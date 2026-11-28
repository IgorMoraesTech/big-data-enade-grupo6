"""Autenticação de usuários via OpenLDAP de laboratório e sessões Redis.

LDAP sem TLS apenas na rede isolada do Compose. Em produção use LDAPS/StartTLS,
segredos externos, CSRF e restrições de rede apropriadas.
"""
import json
import re
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from ldap3 import Connection, Server, SUBTREE
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from app import config
from app.search import get_elastic, get_redis

router = APIRouter(prefix="/api", tags=["Autenticação LDAP e perfis"])
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,48}$")
SESSION_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SESSION_COOKIE = "enade_auth_session"
SESSION_SECONDS = 3600


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=48)
    password: str = Field(min_length=1, max_length=256)


def ldap_login(username: str, password: str) -> str:
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(401, "Credenciais inválidas")
    url = urlparse(config.LDAP_URL)
    if url.scheme not in {"ldap", "ldaps"} or not url.hostname:
        raise HTTPException(503, "Configuração LDAP inválida")
    server = Server(url.hostname, port=url.port or (636 if url.scheme == "ldaps" else 389),
                    use_ssl=url.scheme == "ldaps", connect_timeout=5)
    dn = f"uid={username},{config.LDAP_PEOPLE_DN}"
    try:
        with Connection(server, user=dn, password=password, auto_bind=True,
                        receive_timeout=5) as conn:
            if not conn.search(dn, "(objectClass=inetOrgPerson)",
                               search_scope=SUBTREE, attributes=["employeeType"]):
                raise HTTPException(403, "Usuário sem perfil autorizado")
            attrs = conn.entries[0].entry_attributes_as_dict
            roles = attrs.get("employeeType", [])
            if roles not in (["professor"], ["estudante"]):
                raise HTTPException(403, "Perfil LDAP não permitido")
            return roles[0]
    except HTTPException:
        raise
    except LDAPException as exc:
        # Nunca incluir senhas e DNs internos no texto da resposta.
        if "invalidCredentials" in str(exc) or "invalid credentials" in str(exc).lower():
            raise HTTPException(401, "Credenciais inválidas") from exc
        raise HTTPException(503, "Servidor LDAP indisponível") from exc
    except OSError as exc:
        raise HTTPException(503, "Servidor LDAP indisponível") from exc


def session_key(token: str):
    return "enade:auth:" + token


def current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not SESSION_PATTERN.fullmatch(token):
        raise HTTPException(401, "Login necessário")
    try:
        raw = get_redis().get(session_key(token))
    except RedisError as exc:
        raise HTTPException(503, "Serviço de sessão indisponível") from exc
    if not raw:
        raise HTTPException(401, "Sessão encerrada")
    try:
        data = json.loads(raw)
        if data["role"] not in ("estudante", "professor"):
            raise ValueError("Invalid role")
        return {"username": data["username"], "role": data["role"]}
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(401, "Sessão inválida") from exc


def professor(user: dict = Depends(current_user)):
    if user["role"] != "professor":
        raise HTTPException(403, "Acesso exclusivo do professor")
    return user


@router.post("/auth/login")
def login(credentials: Credentials, request: Request, response: Response):
    role = ldap_login(credentials.username, credentials.password)
    token = secrets.token_hex(32)
    try:
        get_redis().setex(session_key(token), SESSION_SECONDS, json.dumps(
            {"username": credentials.username, "role": role}))
    except RedisError as exc:
        raise HTTPException(503, "Serviço de sessão indisponível") from exc
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https",
                        max_age=SESSION_SECONDS, path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"username": credentials.username, "role": role}


@router.get("/auth/me")
def me(response: Response, user: dict = Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE, "")
    if SESSION_PATTERN.fullmatch(token):
        try:
            get_redis().delete(session_key(token))
        except RedisError as exc:
            raise HTTPException(503, "Serviço de sessão indisponível") from exc
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"logged_out": True}


@router.get("/professor/questions/{question_id}/answer")
def answer(question_id: str, _user: dict = Depends(professor)):
    if len(question_id) > 128:
        raise HTTPException(422, "ID muito longo")
    try:
        result = get_elastic().get(index=config.ELASTICSEARCH_INDEX, id=question_id,
                                   _source_includes=["id", "answer", "annulled"])
    except Exception as exc:
        from elasticsearch import NotFoundError
        if isinstance(exc, NotFoundError):
            raise HTTPException(404, "Questão não encontrada") from exc
        raise HTTPException(503, "Acervo indisponível") from exc
    return result["_source"]


@router.get("/professor/stats/courses")
def private_courses(_user: dict = Depends(professor)):
    try:
        response = get_elastic().search(
            index=config.ELASTICSEARCH_INDEX,
            size=0,
            aggs={"courses": {"terms": {"field": "course", "size": 500}}},
        )
    except Exception as exc:
        raise HTTPException(503, "Estatísticas indisponíveis") from exc
    return {"items": [{"course": v["key"], "count": v["doc_count"]}
                      for v in response["aggregations"]["courses"]["buckets"]]}
