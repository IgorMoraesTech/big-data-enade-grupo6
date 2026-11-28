
import csv
from pathlib import Path

import pytest

from scripts.inventory_enade import (
    FIELDS,
    load_manifest,
    summarize,
    update_local_statuses,
)


def test_manifest_contains_two_real_courses_and_official_documents():
    root = Path(__file__).resolve().parents[1]
    rows = load_manifest(root / "data" / "manifest.csv")

    assert len(rows) == 8
    assert {row["curso"] for row in rows} == {
        "Fisioterapia",
        "Enfermagem",
    }
    assert {row["tipo_documento"] for row in rows} == {
        "prova",
        "gabarito",
        "padrao_resposta",
        "diretriz",
    }
    assert {row["formato"] for row in rows} == {"pdf", "html"}
    assert all(row["url_oficial"].startswith("https://") for row in rows)


def test_summary_distinguishes_link_download_and_processing(tmp_path):
    rows = [
        {
            "ano": "2023",
            "curso": "Enfermagem",
            "area": "Saúde",
            "tipo_documento": "prova",
            "formato": "pdf",
            "url_oficial": "https://download.inep.gov.br/prova.pdf",
            "nome_arquivo": "prova.pdf",
            "status_link": "disponivel",
            "status_local": "baixado",
        }
    ]

    raw = tmp_path / "data" / "raw"
    processed = tmp_path / "data" / "output"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    (raw / "prova.pdf").write_bytes(b"%PDF-1.4")

    result = summarize(rows, tmp_path)

    assert result["identificados"] == 1
    assert result["disponiveis"] == 1
    assert result["baixados"] == 1
    assert result["processados"] == 0

    (processed / "prova.jsonl").write_text("{}\n", encoding="utf-8")

    assert summarize(rows, tmp_path)["processados"] == 1


def test_missing_document_cannot_have_url_or_filename(tmp_path):
    path = tmp_path / "manifest.csv"

    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "ano": "2023",
                "curso": "Enfermagem",
                "area": "Saúde",
                "tipo_documento": "prova",
                "formato": "pdf",
                "url_oficial": "https://example.gov.br/prova.pdf",
                "nome_arquivo": "",
                "status_link": "ausente",
                "status_local": "ausente",
            }
        )

    with pytest.raises(ValueError, match="não pode ter URL/nome"):
        load_manifest(path)


def test_duplicate_course_year_and_document_type_is_rejected(tmp_path):
    root = Path(__file__).resolve().parents[1]
    rows = load_manifest(root / "data" / "manifest.csv")
    path = tmp_path / "manifest.csv"

    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows([rows[0], rows[0]])

    with pytest.raises(ValueError, match="duplicado"):
        load_manifest(path)


def test_local_status_is_independent_from_link_status(tmp_path):
    rows = [
        {
            "ano": "2023",
            "curso": "Enfermagem",
            "area": "Saúde",
            "tipo_documento": "prova",
            "formato": "pdf",
            "url_oficial": "https://example.gov.br/prova.pdf",
            "nome_arquivo": "prova.pdf",
            "status_link": "quebrado",
            "status_local": "nao_baixado",
        }
    ]

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "prova.pdf").write_bytes(b"%PDF-1.4")

    update_local_statuses(rows, raw)

    assert rows[0]["status_link"] == "quebrado"
    assert rows[0]["status_local"] == "baixado"
