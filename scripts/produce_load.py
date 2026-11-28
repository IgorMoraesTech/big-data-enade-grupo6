"""Publica registros sintéticos únicos para medir drenagem de uma fila Kafka.

Uso (em container api): python -m scripts.produce_load --count 80 --prefix ci-2026
A saída é JSON e NÃO representa extração nem amostra oficial do ENADE.
"""
import argparse
import json
import time

from confluent_kafka import Producer

from app import config
from app.schema import Question


def publish(count: int, prefix: str) -> dict:
    failures: list[str] = []
    delivered = 0

    def callback(err, _message):
        nonlocal delivered
        if err is not None:
            failures.append(str(err))
        else:
            delivered += 1

    producer = Producer({
        "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
        "acks": "all",
    })
    started = time.perf_counter()
    for i in range(count):
        doc = Question(
            id=f"{prefix}-{i:05d}",
            year=2023,
            area="Dados sintéticos",
            course="Carga de laboratório",
            section="FG",
            number=i + 1,
            question_type="objective",
            statement=f"Questão sintética {i} para medir offsets e indexação Kafka",
            context="EXEMPLO FICTÍCIO; não corresponde a prova oficial.",
            alternatives={"A": "Dado sintético", "B": "Dado fictício"},
            answer=None,
            annulled=False,
            competencies=[],
            knowledge_objects=[],
            source_pdf="SINTETICO_NAO_OFICIAL.pdf",
            source_pages=[1],
        )
        producer.produce(
            config.KAFKA_TOPIC,
            key=doc.id.encode("utf-8"),
            value=json.dumps(doc.model_dump(), ensure_ascii=False).encode("utf-8"),
            on_delivery=callback,
        )
        producer.poll(0)

    pending = producer.flush(60)
    elapsed = time.perf_counter() - started
    if failures or pending or delivered != count:
        raise RuntimeError(
            f"Publicação incompleta: {delivered=}, {count=}, {pending=}, {failures=}"
        )
    result = {
        "kind": "synthetic_kafka_load",
        "count": count,
        "prefix": prefix,
        "producer_seconds": round(elapsed, 3),
        "producer_confirmed_messages_per_second": round(count / elapsed, 3),
        "disclaimer": "vazão do produtor; NÃO é throughput de indexação",
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=80)
    parser.add_argument("--prefix", type=str, required=True)
    args = parser.parse_args()
    if not 1 <= args.count <= 5000:
        parser.error("--count precisa estar entre 1 e 5000")
    if not args.prefix or len(args.prefix) > 50 or not all(
        c.isascii() and (c.isalnum() or c in "_-") for c in args.prefix
    ):
        parser.error("--prefix precisa ter até 50 caracteres ASCII alfanuméricos, _ ou -")
    publish(args.count, args.prefix)


if __name__ == "__main__":
    main()
