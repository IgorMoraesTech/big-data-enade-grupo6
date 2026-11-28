import json
from pathlib import Path

from app.schema import Question


def test_real_questions_match_schema_and_have_official_sources():
    path = Path(__file__).resolve().parents[1] / "sample" / "real_questions.jsonl"
    rows = [Question.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert {row.course for row in rows} == {"Fisioterapia", "Enfermagem"}
    assert all(row.source_pdf.startswith("https://download.inep.gov.br/") for row in rows)
    assert all(row.source_pages and row.answer in row.alternatives for row in rows)
    assert len({row.id for row in rows}) == len(rows)
