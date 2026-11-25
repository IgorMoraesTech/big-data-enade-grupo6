"""Kafka → Elasticsearch, DLQ e commits manuais de offsets.

O commit acontece após indexação ou confirmação de mensagem na DLQ.
Esta implementação deve ser submetida a testes de falha reais antes de alegar
ausência de perdas em todos os cenários.
"""
import json
import logging
import signal
import time

from confluent_kafka import Consumer, Producer, KafkaException
from elasticsearch import Elasticsearch
from pydantic import ValidationError

from app import config
from app.schema import Question

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)
running = True


def stop(_sig, _frame):
    global running
    running = False


def index_one(es: Elasticsearch, raw: bytes):
    question = Question.model_validate_json(raw)
    es.index(index=config.ELASTICSEARCH_INDEX, id=question.id, document=question.model_dump())
    return question.id


def send_dead_letter(producer: Producer, raw: bytes, reason: str):
    delivery_errors = []

    def on_delivery(err, _msg):
        if err is not None:
            delivery_errors.append(str(err))

    payload = json.dumps({"error": reason, "raw": raw.decode("utf-8", errors="replace")})
    producer.produce(config.KAFKA_DLQ_TOPIC, value=payload.encode("utf-8"), on_delivery=on_delivery)
    remaining = producer.flush(timeout=15)
    if remaining or delivery_errors:
        raise RuntimeError(f"Publicação DLQ falhou: {delivery_errors}, pendentes={remaining}")


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    consumer = Consumer({
        "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": config.KAFKA_GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS, "acks": "all"})
    es = Elasticsearch(config.ELASTICSEARCH_URL, request_timeout=30)
    consumer.subscribe([config.KAFKA_TOPIC])
    try:
        while running:
            msg = consumer.poll(1)
            if msg is None:
                continue
            if msg.error():
                log.error("Kafka: %s", msg.error())
                continue
            try:
                doc_id = index_one(es, msg.value())
                log.info("Indexado: %s", doc_id)
            except (ValidationError, ValueError, UnicodeDecodeError) as exc:
                try:
                    send_dead_letter(producer, msg.value(), str(exc))
                    log.warning("Mensagem inválida enviada à DLQ")
                except Exception as dlq_exc:
                    log.error("DLQ indisponível: %s", dlq_exc)
                    time.sleep(2)
                    continue
            except Exception as exc:
                # Não confirmar offsets se ES não respondeu com sucesso.
                log.error("Falha indexando; tentará novamente: %s", exc)
                time.sleep(2)
                continue
            try:
                consumer.commit(message=msg, asynchronous=False)
            except KafkaException as exc:
                log.error("Falha commit (idempotência permite reprocessar): %s", exc)
    finally:
        consumer.close()
        producer.flush(10)


if __name__ == "__main__":
    main()
