"""API FastAPI, com busca pública sem gabarito enquanto LDAP não estiver pronto."""
import json
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from redis.exceptions import RedisError

from app import config
from app.cart import router as cart_router
from app.search import cache_key, get_elastic, get_redis, query_questions, search_body

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
app = FastAPI(title="ENADE | Busca de Questões", version="0.1.0",
              description="Protótipo acadêmico. Autenticação LDAP e Kerberos pendentes.")
app.include_router(cart_router)


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse("frontend/index.html")


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/ready")
def ready():
    try:
        es = get_elastic()
        redis = get_redis()
        if not es.ping() or not redis.ping():
            raise RuntimeError("Serviço indisponível")
    except Exception as exc:
        log.warning("Dependência indisponível: %s", exc)
        raise HTTPException(status_code=503, detail="Serviços indisponíveis") from exc
    return {"status": "ready"}


@app.get("/api/questions")
def list_questions(
    q: str | None = Query(default=None, max_length=300),
    year: int | None = Query(default=None, ge=2004, le=2100),
    course: str | None = None,
    area: str | None = None,
    section: str | None = Query(default=None, pattern="^(FG|CE)$"),
    question_type: str | None = Query(default=None, pattern="^(objective|discursive)$"),
    competency: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    body = search_body(q, year, course, area, section, question_type, competency, page, page_size)
    key = cache_key(body)
    # Uma nova indexação incrementa a versão global do acervo. A versão
    # faz parte da chave, invalidando imediatamente os caches anteriores.
    # Redis indisponível não impede a consulta direta ao Elasticsearch.
    try:
        redis = get_redis()
        version = redis.get("enade:index:version") or "0"
        key = key + ":v" + version
        cached = redis.get(key)
        if cached:
            return {**json.loads(cached), "cache_hit": True}
    except RedisError as exc:
        log.warning("Redis indisponível: %s", exc)
    try:
        result = query_questions(get_elastic(), body, page, page_size)
    except Exception as exc:
        log.error("Falha Elasticsearch: %s", exc)
        raise HTTPException(status_code=503, detail="Busca temporariamente indisponível") from exc
    try:
        get_redis().setex(key, config.REDIS_CACHE_TTL, json.dumps(result, ensure_ascii=False))
    except RedisError as exc:
        log.warning("Falha ao salvar cache: %s", exc)
    return {**result, "cache_hit": False}


@app.get("/api/stats/courses")
def courses():
    try:
        response = get_elastic().search(
            index=config.ELASTICSEARCH_INDEX,
            size=0,
            aggs={"courses": {"terms": {"field": "course", "size": 500}}},
        )
        return {"items": [{"course": x["key"], "count": x["doc_count"]}
                          for x in response["aggregations"]["courses"]["buckets"]]}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Estatísticas indisponíveis") from exc


@app.get("/api/stats/competencies")
def competencies():
    try:
        response = get_elastic().search(
            index=config.ELASTICSEARCH_INDEX,
            size=0,
            aggs={"competencies": {"terms": {"field": "competencies", "size": 500},
                   "aggs": {"years": {"histogram": {"field": "year", "interval": 1}}}}},
        )
        return {"items": response["aggregations"]["competencies"]["buckets"]}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Estatísticas indisponíveis") from exc
