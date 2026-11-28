"""Testes unitários do carrinho sem infraestrutura externa."""
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app import cart


class RedisFake:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        assert ttl == cart.TTL
        self.data[key] = value


def make_client(monkeypatch):
    db = RedisFake()
    monkeypatch.setattr(cart, "get_redis", lambda: db)

    def question(qid):
        if qid != "q1":
            raise HTTPException(404, "Não encontrada")
        return {"id": "q1", "statement": "Ética", "course": "SI", "year": 2023,
                "number": 1, "alternatives": {"A": "Sim"}, "source_pages": [1],
                "source_pdf": "https://example.org/enade.pdf"}

    monkeypatch.setattr(cart, "get_question", question)
    app = FastAPI()
    app.include_router(cart.router)
    return TestClient(app)


def test_add_remove_export_and_pdf(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/api/cart").json()["count"] == 0
    response = client.post("/api/questions/q1/cart")
    assert response.status_code == 201
    assert response.json()["count"] == 1
    assert client.post("/api/questions/q1/cart").json()["count"] == 1
    json_response = client.get("/api/cart/export.json")
    assert json_response.status_code == 200
    assert json_response.headers["content-disposition"] == 'attachment; filename="questoes-enade.json"'
    assert json_response.headers["cache-control"] == "no-store"
    questions = json_response.json()["questions"]
    assert len(questions) == 1
    assert "answer" not in questions[0]
    pdf = client.get("/api/cart/export.pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")
    assert client.delete("/api/questions/q1/cart").json()["count"] == 0


def test_not_found(monkeypatch):
    client = make_client(monkeypatch)
    assert client.post("/api/questions/nope/cart").status_code == 404
    assert client.get("/api/cart").json()["count"] == 0


def test_cookie_is_random(monkeypatch):
    client = make_client(monkeypatch)
    client.cookies.set(cart.COOKIE, "invalid", domain="testserver.local", path="/")
    client.get("/api/cart")
    assert len(client.cookies[cart.COOKIE]) == 64


def test_empty_pdf():
    assert cart.render_pdf([]).startswith(b"%PDF-")
