"""Testes locais: PDFs sintéticos, sem alegar auditoria do INEP."""
import csv

import fitz

from scripts.prepare_50_sources import SOURCES, generate, scan_pdf


def make_synthetic_pdf(path):
    pdf = fitz.open()
    p1 = pdf.new_page()
    p1.insert_text((60, 100), "QUESTÃO 04\nEnunciado sintético de teste")
    p2 = pdf.new_page()
    p2.insert_text((60, 100), "QUESTÃO 04\nDuplicidade para revisão")
    p2.insert_text((60, 180), "QUESTÃO 15\nOutro enunciado sintético")
    pdf.save(path)
    pdf.close()


def test_scan_preserves_ambiguous_duplicate_question_headings(tmp_path):
    path = tmp_path / "teste.pdf"
    make_synthetic_pdf(path)
    found = scan_pdf(path)
    assert [x["pagina_fisica_candidata"] for x in found[4]] == [1, 2]
    assert [x["pagina_fisica_candidata"] for x in found[15]] == [2]


def test_generates_only_pending_candidates_without_manual_claims(tmp_path):
    pdf_dir = tmp_path / "raw"
    pdf_dir.mkdir()
    for filename, _ in SOURCES.values():
        make_synthetic_pdf(pdf_dir / filename)
    csv_path, report_path = generate(pdf_dir, tmp_path / "evidence")
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 50
    assert all(row["status_revisao"] == "pendente" for row in rows)
    assert all(row["pagina_pdf_confirmada"] == "" for row in rows)
    assert all(row["revisor"] == "" for row in rows)
    row = next(
        row for row in rows if row["curso"] == "Fisioterapia" and row["questao"] == "04"
    )
    assert row["cabecalhos_detectados"] == "2"
    assert row["paginas_candidatas_nao_confirmadas"] == "1;2"
    assert "human_reviews_completed" in report_path.read_text(encoding="utf-8")
