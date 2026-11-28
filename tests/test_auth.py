"""Testes de RBAC/403 sem LDAP nem Redis reais."""
import json

from fastapi.testclient import TestClient
from app import auth
from app.main import app


class RedisFake:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)


def test_student_403_teacher_and_login(monkeypatch):
    db = RedisFake()
    monkeypatch.setattr(auth, "get_redis", lambda: db)
    monkeypatch.setattr(auth, "ldap_login", lambda u, p: "estudante" if u == "estudante" else "professor")
    with TestClient(app) as client:
        assert client.get("/api/professor/questions/example/answer").status_code == 401
        r = client.post("/api/auth/login", json={"username": "estudante", "password": "senha"})
        assert r.status_code == 200
        assert r.json()["role"] == "estudante"
        assert client.get("/api/auth/me").json()["role"] == "estudante"
        assert client.get("/api/professor/questions/example/answer").status_code == 403
        assert client.get("/api/professor/stats/courses").status_code == 403
        assert client.post("/api/auth/logout").json()["logged_out"] is True
        assert client.get("/api/auth/me").status_code == 401


def test_professor_access_answer(monkeypatch):
    db = RedisFake()
    monkeypatch.setattr(auth, "get_redis", lambda: db)
    monkeypatch.setattr(auth, "ldap_login", lambda u, p: "professor")

    class ElasticFake:
        def get(self, **kw):
            return {"_source": {"id": "abc", "answer": "B", "annulled": False}}
        def search(self, **kw):
            return {"aggregations": {"courses": {"buckets": [{"key": "SI", "doc_count": 3}]}}}

    monkeypatch.setattr(auth, "get_elastic", lambda: ElasticFake())
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "professor",
                                                        "password": "senha"}).status_code == 200
        result = client.get("/api/professor/questions/abc/answer")
        assert result.status_code == 200
        assert result.json()["answer"] == "B"
        assert client.get("/api/professor/stats/courses").json()["items"][0]["count"] == 3


def test_ldap_username_validation():
    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException) as exc:
        auth.ldap_login("admin)(uid=*", "senha")
    assert exc.value.status_code == 401
