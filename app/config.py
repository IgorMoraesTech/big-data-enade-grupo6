"""Configuração por variáveis de ambiente; nunca armazenar segredos no Git."""
import os

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "enade-questions-v1")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "60"))
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "enade-questions")
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", "enade-questions-dlq")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "enade-indexer")

# Laboratório LDAP; use LDAPS e segredos fora do Compose em produção.
LDAP_URL = os.getenv("LDAP_URL", "ldap://ldap:389")
LDAP_PEOPLE_DN = os.getenv("LDAP_PEOPLE_DN", "ou=people,dc=enade,dc=local")
