"""Publica JSON ou JSONL estruturado no Kafka.

Uso: python -m scripts.produce caminho.jsonl
"""
import json
import sys
from pathlib import Path

from confluent_kafka import Producer
from app import config
from app.schema import Question


def main(path: str):
    producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS, "acks": "all"})
    errors = []

    def on_delivery(err, _msg):
        if err:
            errors.append(str(err))

    count = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = Question.model_validate_json(line)
        producer.produce(
            config.KAFKA_TOPIC, key=item.id,
            value=json.dumps(item.model_dump(), ensure_ascii=False).encode("utf-8"),
            on_delivery=on_delivery,
        )
        producer.poll(0)
        count += 1
    pending = producer.flush(timeout=30)
    if errors or pending:
        raise RuntimeError(f"Envio Kafka incompleto: erros={errors}, pendentes={pending}")
    print(f"Mensagens confirmadas pelo produtor: {count}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m scripts.produce caminho.jsonl")
    main(sys.argv[1])
