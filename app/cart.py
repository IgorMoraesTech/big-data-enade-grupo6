"""Carrinho anônimo no Redis e exportação pública sem respostas/gabaritos.

NÃO substitui autenticação LDAP nem autorização professor/aluno.
"""
import io
import json
import re
import secrets
from html import escape

from elasticsearch import NotFoundError
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from redis.exceptions import RedisError
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from app import config
from app.search import PUBLIC_FIELDS, get_elastic, get_redis

router = APIRouter(prefix="/api", tags=["Carrinho e exportações"])
COOKIE = "enade_cart_session"
TTL = 86400
MAX_ITEMS = 30
TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")


def session(request: Request, response: Response) -> str:
    token = request.cookies.get(COOKIE, "")
    if TOKEN_RE.fullmatch(token):
        return token
    token = secrets.token_hex(32)
    response.set_cookie(COOKIE, token, max_age=TTL, httponly=True,
                        samesite="lax", secure=request.url.scheme == "https")
    return token


def get_ids(token: str) -> list[str]:
    try:
        data = get_redis().get("enade:cart:" + token)
        values = json.loads(data) if data else []
        if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
            raise ValueError("Dados de sessão inválidos")
        return values[:MAX_ITEMS]
    except (RedisError, ValueError, TypeError) as exc:
        raise HTTPException(503, "Carrinho indisponível") from exc


def save_ids(token: str, ids: list[str]):
    try:
        get_redis().setex("enade:cart:" + token, TTL, json.dumps(ids))
    except RedisError as exc:
        raise HTTPException(503, "Não foi possível salvar o carrinho") from exc


def get_question(qid: str):
    try:
        result = get_elastic().get(index=config.ELASTICSEARCH_INDEX, id=qid,
                                   _source_includes=PUBLIC_FIELDS)
        doc = result["_source"]
        return {k: doc[k] for k in PUBLIC_FIELDS if k in doc}
    except NotFoundError as exc:
        raise HTTPException(404, "Questão não encontrada") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Acervo indisponível") from exc


def get_items(ids: list[str]):
    items = []
    for qid in ids:
        try:
            items.append(get_question(qid))
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
    return items


@router.get("/cart")
def cart(request: Request, response: Response):
    ids = get_ids(session(request, response))
    return {"count": len(ids), "items": get_items(ids)}


@router.post("/questions/{question_id}/cart", status_code=201)
def add(question_id: str, request: Request, response: Response):
    if len(question_id) > 128:
        raise HTTPException(422, "ID muito longo")
    token = session(request, response)
    get_question(question_id)  # Não armazenar IDs inexistentes
    ids = get_ids(token)
    if question_id not in ids:
        if len(ids) >= MAX_ITEMS:
            raise HTTPException(409, "Máximo de 30 questões")
        ids.append(question_id)
    save_ids(token, ids)
    return {"count": len(ids), "ids": ids}


@router.delete("/questions/{question_id}/cart")
def remove(question_id: str, request: Request, response: Response):
    token = session(request, response)
    ids = [qid for qid in get_ids(token) if qid != question_id]
    save_ids(token, ids)
    return {"count": len(ids), "ids": ids}


@router.get("/cart/export.json")
def json_export(request: Request, response: Response):
    return {"questions": get_items(get_ids(session(request, response)))}


def render_pdf(items: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm,
                            rightMargin=2*cm, title="Seleção de questões ENADE")
    styles = getSampleStyleSheet()
    blocks = [Paragraph("Seleção de questões ENADE", styles["Title"]), Spacer(1, 14)]
    if not items:
        blocks.append(Paragraph("Nenhuma questão selecionada.", styles["BodyText"]))
    for item in items:
        header = "Questão {} — {} ({})".format(item.get("number", "?"),
                                                item.get("course", ""), item.get("year", ""))
        blocks.append(Paragraph(escape(header), styles["Heading2"]))
        blocks.append(Paragraph(escape(item.get("statement", "")).replace("\n", "<br/>"),
                                styles["BodyText"]))
        for key, value in sorted(item.get("alternatives", {}).items()):
            blocks.append(Paragraph("{}: {}".format(escape(str(key)), escape(str(value))),
                                    styles["BodyText"]))
        origin = "{} — página(s): {}".format(item.get("source_pdf", ""),
                                              ", ".join(map(str, item.get("source_pages", []))))
        blocks.append(Paragraph("Fonte: " + escape(origin), styles["BodyText"]))
        blocks.append(Spacer(1, 14))
    doc.build(blocks)
    return buf.getvalue()


@router.get("/cart/export.pdf")
def pdf_export(request: Request, response: Response):
    ids = get_ids(session(request, response))
    pdf = render_pdf(get_items(ids))
    headers = {"Content-Disposition": 'attachment; filename="questoes-enade.pdf"'}
    # StreamingResponse não herda automaticamente cookies configurados em Response.
    if "set-cookie" in response.headers:
        headers["Set-Cookie"] = response.headers["set-cookie"]
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers=headers)
