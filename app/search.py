"""Consultas Elastic; fonte única da lógica de busca."""
import json
from typing import Any

from elasticsearch import Elasticsearch
from redis import Redis

from app import config


def get_elastic() -> Elasticsearch:
    return Elasticsearch(config.ELASTICSEARCH_URL, request_timeout=10)


def get_redis() -> Redis:
    return Redis.from_url(config.REDIS_URL, decode_responses=True, socket_timeout=2)


PUBLIC_FIELDS = [
    "id", "year", "area", "course", "section", "number",
    "question_type", "statement", "context", "alternatives",
    "annulled", "competencies", "knowledge_objects", "source_pdf", "source_pages"
]


def search_body(q: str | None, year: int | None, course: str | None,
                area: str | None, section: str | None, question_type: str | None,
                competency: str | None, page: int, page_size: int) -> dict[str, Any]:
    filters: list[dict[str, Any]] = []
    if year is not None:
        filters.append({"term": {"year": year}})
    for key, value in (
        ("course", course), ("area", area), ("section", section),
        ("question_type", question_type), ("competencies", competency),
    ):
        if value:
            filters.append({"term": {key: value}})
    query: dict[str, Any] = {"bool": {
        "must": [{"multi_match": {
            "query": q, "fields": ["statement^3", "context^2", "alternatives.*"],
            "type": "best_fields",
        }}] if q else [{"match_all": {}}],
        "filter": filters,
    }}
    return {
        "query": query,
        "from": (page - 1) * page_size,
        "size": page_size,
        "_source": PUBLIC_FIELDS,
        "sort": ["_score", {"id": "asc"}] if q else [{"year": "desc"}, {"id": "asc"}],
        "highlight": {"pre_tags": ["<mark>"], "post_tags": ["</mark>"],
                      "fields": {"statement": {}, "context": {}}} if q else {},
        "track_total_hits": True,
    }


def query_questions(es: Elasticsearch, body: dict[str, Any], page: int, page_size: int) -> dict[str, Any]:
    resp = es.search(index=config.ELASTICSEARCH_INDEX, body=body)
    return {
        "total": resp["hits"]["total"]["value"],
        "page": page,
        "page_size": page_size,
        "items": [{**hit["_source"], "highlights": hit.get("highlight", {})}
                  for hit in resp["hits"]["hits"]],
    }


def cache_key(body: dict[str, Any]) -> str:
    import hashlib
    serialized = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return "enade:search:v1:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()
