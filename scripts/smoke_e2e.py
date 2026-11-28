"""Smoke test externo: valida o pipeline após publicar a amostra no Kafka.

NÃO demonstra questões oficiais; serve para validar integração técnica em CI.
"""
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"


def await_ready(client, timeout=180):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            response = client.get(BASE + "/ready")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(3)
    raise AssertionError("API /ready não ficou disponível")


def await_question(client, timeout=90):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        response = client.get(BASE + "/api/questions", params={"q": "tecnologia"})
        response.raise_for_status()
        matches = [x for x in response.json()["items"] if x.get("id") == "sample-didatico-01"]
        if matches:
            return matches[0]
        time.sleep(2)
    raise AssertionError("Mensagem Kafka não chegou ao índice Elasticsearch")


def main():
    with httpx.Client(timeout=20) as client:
        await_ready(client)
        q = await_question(client)
        assert "answer" not in q, "Gabarito exposto pela busca pública"
        assert q["id"] == "sample-didatico-01"
        response = client.post(BASE + "/api/questions/sample-didatico-01/cart")
        assert response.status_code == 201, response.text
        response = client.get(BASE + "/api/cart")
        assert response.status_code == 200 and response.json()["count"] == 1
        pdf = client.get(BASE + "/api/cart/export.pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
        export = client.get(BASE + "/api/cart/export.json")
        assert export.status_code == 200
        assert "answer" not in export.json()["questions"][0]
        assert client.get(BASE).status_code == 200
        assert client.get(BASE + "/openapi.json").status_code == 200
        assert client.delete(BASE + "/api/questions/sample-didatico-01/cart").status_code == 200
        print(json.dumps({"ready": True, "kafka_to_elasticsearch": True,
                          "search": True, "public_answer_hidden": True,
                          "redis_cart": True, "pdf_export": True,
                          "json_export": True, "frontend": True, "openapi": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        raise
