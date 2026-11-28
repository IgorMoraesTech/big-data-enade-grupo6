"""E2E: consulta duas questões transcritas do ENADE por texto interdisciplinar.

Executar APÓS publicar sample/real_questions.jsonl via Kafka.
Não valida, por si só, fidelidade de transcrição, páginas ou gabaritos oficiais.
"""
import json
import time
from pathlib import Path

import httpx


BASE = "http://127.0.0.1:8000"
FIXTURE = Path(__file__).resolve().parents[1] / "sample" / "real_questions.jsonl"


def load_questions():
    return [json.loads(row) for row in FIXTURE.read_text(encoding="utf-8").splitlines()
            if row.strip()]


def wait_for_cross_course_search(client, expected_ids, timeout=100):
    deadline = time.monotonic() + timeout
    seen = set()
    last_response = None
    while time.monotonic() < deadline:
        response = client.get(
            BASE + "/api/questions",
            params={"q": "ética", "page": 1, "page_size": 100},
        )
        response.raise_for_status()
        result = response.json()
        last_response = result
        seen = {item["id"] for item in result["items"]} & expected_ids
        if seen == expected_ids:
            return result
        time.sleep(2)
    raise AssertionError(
        f"Busca 'ética' não recuperou os dois cursos após {timeout}s. "
        f"Identificadores localizados: {sorted(seen)}; "
        f"total informado: {last_response.get('total') if last_response else 'N/A'}"
    )


def main():
    questions = load_questions()
    assert len(questions) == 2, "O recorte esperado possui duas questões"
    expected = {q["id"]: q for q in questions}
    assert {q["course"] for q in questions} == {"Enfermagem", "Fisioterapia"}

    with httpx.Client(timeout=20) as client:
        data = wait_for_cross_course_search(client, set(expected))
        matches = [item for item in data["items"] if item["id"] in expected]

        for item in matches:
            source = expected[item["id"]]
            assert item["course"] == source["course"]
            assert item["year"] == 2023
            assert item["source_pdf"] == source["source_pdf"]
            assert item["source_pages"] == source["source_pages"]
            assert "answer" not in item, "Resposta oficial exposta pela pesquisa pública"

        # A restrição por curso deve funcionar usando registros indexados reais.
        for course, wanted_id in (
            ("Enfermagem", next(q["id"] for q in questions if q["course"] == "Enfermagem")),
            ("Fisioterapia", next(q["id"] for q in questions if q["course"] == "Fisioterapia")),
        ):
            response = client.get(
                BASE + "/api/questions",
                params={"q": "ética", "course": course, "page_size": 100},
            )
            response.raise_for_status()
            ids = {item["id"] for item in response.json()["items"]}
            assert wanted_id in ids, f"Questão real não aparece no filtro {course}"
            assert all(item["course"] == course for item in response.json()["items"])

        print(json.dumps({
            "fixture": "duas questões de transcrição manual atribuídas a fontes INEP; "
                       "sem auditoria independente dos PDFs",
            "search_term": "ética",
            "real_questions_found": len(matches),
            "courses": sorted({item["course"] for item in matches}),
            "public_answer_hidden": True,
            "course_filters": True,
            "kafka_to_elasticsearch": True,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
