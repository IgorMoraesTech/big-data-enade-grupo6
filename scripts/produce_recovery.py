"""Publica segundo evento de demonstração após parada do consumidor Kafka."""
import json

from confluent_kafka import Producer
from app import config

payload = {
    "id": "recovery-didatico-02",
    "year": 2023,
    "area": "Tecnologia",
    "course": "Curso Fictício",
    "section": "FG",
    "number": 2,
    "question_type": "objective",
    "statement": "Exemplo FICTÍCIO de recuperação de mensagens Kafka.",
    "context": None,
    "alternatives": {"A": "Recuperação"},
    "answer": None,
    "annulled": False,
    "competencies": [],
    "knowledge_objects": [],
    "source_pdf": "EXEMPLO_FICTICIO_NAO_E_PROVA_OFICIAL.pdf",
    "source_pages": [1],
}
producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS, "acks": "all"})
failed = []


def delivery(error, _message):
    if error is not None:
        failed.append(str(error))


producer.produce(config.KAFKA_TOPIC, key=payload["id"],
                 value=json.dumps(payload, ensure_ascii=False).encode(),
                 on_delivery=delivery)
assert producer.flush(20) == 0 and not failed, f"Produção falhou: {failed}"
print("Publicação fictícia de recuperação confirmada.")
