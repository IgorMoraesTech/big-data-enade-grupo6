"""Cria o índice e o mapping explícito antes de indexar dados."""
from elasticsearch import Elasticsearch
from app import config

MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "filter": {
                "enade_synonyms": {
                    "type": "synonym_graph",
                    "synonyms": ["ética, moral", "sustentabilidade, desenvolvimento sustentável"],
                },
            },
            "analyzer": {
                "enade_pt": {
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "enade_synonyms",
                               "brazilian_stop", "brazilian_stem"],
                },
            },
        },
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "id": {"type": "keyword"},
            "year": {"type": "integer"},
            "area": {"type": "keyword"},
            "course": {"type": "keyword"},
            "section": {"type": "keyword"},
            "number": {"type": "integer"},
            "question_type": {"type": "keyword"},
            "statement": {"type": "text", "analyzer": "enade_pt"},
            "context": {"type": "text", "analyzer": "enade_pt"},
            "alternatives": {"type": "object", "dynamic": True},
            "answer": {"type": "keyword"},
            "annulled": {"type": "boolean"},
            "competencies": {"type": "keyword"},
            "knowledge_objects": {"type": "keyword"},
            "source_pdf": {"type": "keyword"},
            "source_pages": {"type": "integer"},
        },
    },
}


def main():
    es = Elasticsearch(config.ELASTICSEARCH_URL)
    if not es.indices.exists(index=config.ELASTICSEARCH_INDEX):
        es.indices.create(index=config.ELASTICSEARCH_INDEX, body=MAPPING)
        print("Índice criado:", config.ELASTICSEARCH_INDEX)
    else:
        print("Índice existente:", config.ELASTICSEARCH_INDEX)


if __name__ == "__main__":
    main()
