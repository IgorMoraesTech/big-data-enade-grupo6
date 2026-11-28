"""Mede backlog Kafka, drenagem após parada e indexação Elasticsearch.

Executar SOMENTE no Docker Compose de CI/laboratório, com serviços já
inicializados. Publica registros sintéticos identificáveis e reinicia indexer.
Métrica docs/s é vazão efetiva observada durante recuperação (inclui startup,
esperas de polling e visibilidade do ES), não capacidade máxima sustentável.
"""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ES = "http://127.0.0.1:9200"
INDEX = "enade-questions-v1"
GROUP = "enade-indexer"
TOPIC = "enade-questions"


def compose(*args: str, timeout=150) -> str:
    result = subprocess.run(
        ["docker", "compose", *args],
        text=True, capture_output=True, timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"docker compose {' '.join(args)} falhou: "
            f"{result.stderr[-1800:]} {result.stdout[-1000:]}"
        )
    return result.stdout


def parse_group_lag(output: str, group: str = GROUP, topic: str = TOPIC) -> dict:
    """Interpreta linhas do kafka-consumer-groups --describe (somente números)."""
    partitions = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 6 or fields[0] != group or fields[1] != topic:
            continue
        # GROUP TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG ...
        try:
            partition = int(fields[2])
            committed = int(fields[3])
            end = int(fields[4])
            lag = int(fields[5])
        except ValueError:
            continue
        if committed < 0 or end < 0 or lag < 0:
            raise ValueError(f"Offsets negativos/inexistentes: {line!r}")
        if lag != max(0, end - committed):
            raise ValueError(f"Lag inconsistente: {line!r}")
        partitions[partition] = {
            "committed": committed,
            "end": end,
            "lag": lag,
        }
    if not partitions:
        raise ValueError(f"Nenhum offset comprometido para {group}/{topic}: {output[-1500:]}")
    return {"total": sum(p["lag"] for p in partitions.values()), "partitions": partitions}


def group_lag() -> dict:
    output = compose(
        "exec", "-T", "kafka", "/opt/kafka/bin/kafka-consumer-groups.sh",
        "--bootstrap-server", "localhost:9092", "--describe", "--group", GROUP,
        timeout=45,
    )
    return parse_group_lag(output)


def indexed_count(client: httpx.Client, prefix: str) -> int:
    response = client.post(
        f"{ES}/{INDEX}/_count",
        json={"query": {"prefix": {"id": prefix + "-"}}},
    )
    response.raise_for_status()
    return int(response.json()["count"])


def measure(count: int, prefix: str, timeout: int = 180) -> dict:
    started_at = datetime.now(timezone.utc).isoformat()
    # Este script não roda no CI em paralelo com outros produtores.
    initial = group_lag()
    with httpx.Client(timeout=20) as client:
        assert indexed_count(client, prefix) == 0, "Prefixo já usado no índice"

        compose("stop", "indexer")
        try:
            publish_stdout = compose(
                "run", "--rm", "api", "python", "-m", "scripts.produce_load",
                "--count", str(count), "--prefix", prefix, timeout=120,
            )
            producer_info = next(
                json.loads(line) for line in publish_stdout.splitlines()
                if line.strip().startswith("{") and '"kind": "synthetic_kafka_load"' in line
            )
            queued = group_lag()
            increase = queued["total"] - initial["total"]
            if increase < count:
                raise AssertionError(
                    f"Backlog cresceu {increase}, esperado pelo menos {count}. "
                    f"{initial=}, {queued=}"
                )
            assert indexed_count(client, prefix) == 0, (
                "Indexação avançou enquanto o consumidor estava parado"
            )
        finally:
            # Independente de falhas de produção/verificação, restaurar serviço.
            restarted_at = time.perf_counter()
            compose("start", "indexer")

        deadline = restarted_at + timeout
        samples = []
        success = False
        last_error = None
        while time.perf_counter() < deadline:
            try:
                lag = group_lag()["total"]
                indexed = indexed_count(client, prefix)
                observed = round(time.perf_counter() - restarted_at, 3)
                samples.append({
                    "seconds_since_restart": observed,
                    "consumer_lag": lag,
                    "indexed_documents": indexed,
                })
                if lag == 0 and indexed == count:
                    success = True
                    break
            except (RuntimeError, ValueError, httpx.HTTPError) as exc:
                last_error = str(exc)
            time.sleep(2)

        if not success:
            raise AssertionError(
                f"Fila não drenada no prazo. Última amostra: "
                f"{samples[-1] if samples else 'nenhuma'}, erro={last_error}"
            )

        elapsed = samples[-1]["seconds_since_restart"]
        if elapsed <= 0:
            raise AssertionError("Tempo de recuperação inválido")
        result = {
            "experiment": "synthetic_backlog_drain_and_indexing",
            "started_at_utc": started_at,
            "fixture": "SINTETICA (não são provas ENADE)",
            "count": count,
            "prefix": prefix,
            "initial_consumer_lag": initial["total"],
            "lag_while_stopped": queued["total"],
            "backlog_increase": increase,
            "final_consumer_lag": 0,
            "indexed_documents": count,
            "recovery_seconds_including_container_start": elapsed,
            "observed_indexed_documents_per_second": round(count / elapsed, 3),
            "producer": producer_info,
            "samples": samples,
            "method": (
                "consumer parado, lote publicado e confirmado, offsets de "
                "grupo Kafka consultados, reinício do indexador, drenagem de "
                "lag e contagem de documentos no Elasticsearch"
            ),
            "limitations": (
                "docs/s é taxa de drenagem do lote sintético, inclui restart "
                "do container, polling e atualização do índice; não é taxa "
                "máxima sustentável, nem vazão de extração de PDFs oficiais"
            ),
        }
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=80)
    parser.add_argument("--prefix", default=f"load-{int(time.time())}")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default="evidence/kafka-ingestion-lag.json")
    args = parser.parse_args()
    if not 1 <= args.count <= 5000:
        parser.error("--count precisa estar entre 1 e 5000")
    if not 30 <= args.timeout <= 600:
        parser.error("--timeout precisa estar entre 30 e 600 segundos")
    result = measure(args.count, args.prefix, args.timeout)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
