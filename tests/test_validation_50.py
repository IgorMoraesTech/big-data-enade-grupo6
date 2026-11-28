"""O relatório não pode atribuir taxas à amostra não revisada."""
from copy import deepcopy
import pytest
from scripts.validation_50 import CHECK_FIELDS, QUESTION_NUMBERS, assess, make_rows, read_csv, write_csv


def completed_rows():
    rows = make_rows()
    for row in rows:
        row.update({
            "pagina_pdf_confirmada": "6",
            "caminho_jsonl_extraido": "data/output/teste.jsonl",
            "revisor": "REVISOR_FICTICIO_DE_TESTE",
            "data_revisao": "2026-11-28",
            "status_revisao": "verificado",
        })
        for field in CHECK_FIELDS:
            row[field] = "certo"
    return rows


def test_sample_has_50_unique_questions_across_two_courses():
    rows = make_rows()
    assert len(QUESTION_NUMBERS) == 25
    assert len(rows) == 50
    assert len({(r["curso"], r["questao"]) for r in rows}) == 50
    assert {r["curso"] for r in rows} == {"Enfermagem", "Fisioterapia"}
    assert all(r["secao_esperada"] == ("FG" if int(r["questao"]) <= 9 else "CE") for r in rows)
    assert all(r["status_revisao"] == "pendente" for r in rows)


def test_blocks_unreviewed_sample():
    with pytest.raises(ValueError, match="pendências"):
        assess(make_rows())


def test_blocks_duplicate_questions():
    rows = completed_rows()
    rows[1] = deepcopy(rows[0])
    with pytest.raises(ValueError, match="distintas"):
        assess(rows)


def test_blocks_uncategorized_mistake():
    rows = completed_rows()
    rows[0]["enunciado_ok"] = "errado"
    with pytest.raises(ValueError, match="categoria"):
        assess(rows)


def test_report_math_on_fictitious_test_data_only():
    rows = completed_rows()
    rows[0]["enunciado_ok"] = "errado"
    rows[0]["categoria_erro"] = "segmentacao"
    result = assess(rows)
    assert result["acertos_por_campo"]["enunciado_ok"]["corretos"] == 49
    assert result["acertos_por_campo"]["enunciado_ok"]["taxa"] == .98
    assert result["registros_totalmente_corretos"] == 49


def test_csv_roundtrip(tmp_path):
    path = tmp_path / "sample.csv"
    write_csv(path, make_rows())
    assert read_csv(path) == make_rows()
