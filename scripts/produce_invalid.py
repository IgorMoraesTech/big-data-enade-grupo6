"""Produz payload inválido diretamente, para provar DLQ do consumidor."""
from confluent_kafka import Producer
from app import config

errors = []


def delivery(error, _msg):
    if error is not None:
        errors.append(str(error))


producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS, "acks": "all"})
producer.produce(config.KAFKA_TOPIC, value=b"not-a-json-document", on_delivery=delivery)
assert producer.flush(20) == 0 and not errors, f"Produção inválida falhou: {errors}"
print("Payload inválido publicado para teste de DLQ.")
