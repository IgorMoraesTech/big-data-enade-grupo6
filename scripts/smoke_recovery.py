"""Verifica invariantes do pipeline Kafka -> Elasticsearch usando Docker Compose real.

Executado apenas em ambiente temporário de CI com a amostra fictícia.
"""
import json
import subprocess
import time

import httpx

BASE = "http://127.0.0.1:8000"
ES = "http://127.0.0.1:9200"
DOC_ID = "sample-didatico-01"
INDEX = "enade-questions-v1"
SAMPLE = "sample/example_question.json"


def compose(*args: str, timeout=120) -> str:
    completed = subprocess.run(
        ["docker", "compose", *args],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"docker compose {' '.join(args)} falhou: {completed.stderr[-2000:]}"
        )
    return completed.stdout


def eventually(check, description, timeout=65):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (httpx.HTTPError, KeyError, ValueError, AssertionError) as exc:
            last = str(exc)
        time.sleep(2)
    raise AssertionError(f"Tempo limite para {description}. Último resultado: {last}")


def get_doc(client: httpx.Client):
    response = client.get(f"{ES}/{INDEX}/_doc/{DOC_ID}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def doc_count(client: httpx.Client):
    response = client.get(f"{ES}/{INDEX}/_count")
    response.raise_for_status()
    return response.json()["count"]


def publish_sample():
    compose("run", "--rm", "api", "python", "-m", "scripts.produce", SAMPLE)


def publish_invalid():
    compose("run", "--rm", "api", "python", "-m", "scripts.produce_invalid")


def dlq_has_invalid():
    # O consumidor Kafka do broker retorna status não-zero por timeout;
    # a saída precisa conter o evento inválido, independentemente do exit.
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "kafka",
         "/opt/kafka/bin/kafka-console-consumer.sh",
         "--bootstrap-server", "localhost:9092",
         "--topic", "enade-questions-dlq", "--from-beginning",
         "--timeout-ms", "6000"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    return '"raw": "not-a-json-document"' in out.stdout


def main():
    data = {
        "fixture": "FICTICIA; não equivale a questões oficiais",
        "tests": {},
    }
    with httpx.Client(timeout=20) as client:
        # O smoke anterior já publicou a amostra e confirmou a indexação.
        doc = eventually(lambda: get_doc(client), "primeira indexação")
        assert doc["_id"] == DOC_ID
        initial_count = doc_count(client)

        # Reentregar a mesma mensagem deve sobrescrever o mesmo _id.
        publish_sample()
        eventually(lambda: get_doc(client), "reentrega")
        # O evento deve ser consumido antes de verificar o contador.
        time.sleep(5)
        after_count = doc_count(client)
        assert after_count == initial_count, (
            f"Idempotência falhou: count={initial_count} -> {after_count}"
        )
        data["tests"]["idempotent_indexing"] = {
            "passed": True, "before": initial_count, "after": after_count,
        }

        # Falha artificial do consumidor: o produtor continua publicando,
        # e mensagens persistidas no Kafka são reprocessadas após o restart.
        compose("stop", "indexer")
        compose("run", "--rm", "api", "python", "-m", "scripts.produce_recovery")
        # O segundo evento tem identificador distinto e é válido.
        before = client.get(f"{ES}/{INDEX}/_doc/recovery-didatico-02")
        assert before.status_code == 404, "Consumidor parado indexou indevidamente"
        compose("start", "indexer")
        def recovered():
            response = client.get(f"{ES}/{INDEX}/_doc/recovery-didatico-02")
            return response.json() if response.status_code == 200 else None
        recovered_doc = eventually(recovered, "retomada após reinício")
        assert recovered_doc["_id"] == "recovery-didatico-02"
        data["tests"]["consumer_restart_recovery"] = {"passed": True}

        # Evento inválido deve ir para a DLQ, sem derrubar o processo.
        publish_invalid()
        eventually(dlq_has_invalid, "registro na DLQ", timeout=60)
        data["tests"]["dlq_invalid_payload"] = {"passed": True}

        # O consumidor prossegue após a mensagem inválida.
        publish_sample()
        eventually(lambda: get_doc(client), "continuidade após DLQ")
        data["tests"]["consumer_after_dlq"] = {"passed": True}

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
