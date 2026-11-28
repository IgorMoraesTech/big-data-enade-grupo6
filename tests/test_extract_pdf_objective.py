"""Testes do extrator em PDFs SINTÉTICOS; não equivalem às provas INEP."""
import fitz

from scripts.extract_pdf import extract, split_alternatives


def test_recognizes_alternatives_without_punctuation_and_multiline():
    raw = (
        "Qual é a resposta?\n"
        "A primeira alternativa\ncontinuação de A\n"
        "B segunda alternativa\nC terceira alternativa\n"
        "D quarta alternativa\nE quinta alternativa"
    )
    statement, alternatives = split_alternatives(raw)
    assert statement == "Qual é a resposta?"
    assert len(alternatives) == 5
    assert alternatives["A"] == "primeira alternativa\ncontinuação de A"
    assert alternatives["E"] == "quinta alternativa"


def test_classic_punctuation_formats():
    raw = "Pergunta?\nA) um\nB. dois\nC) três\nD. quatro\nE) cinco"
    statement, alternatives = split_alternatives(raw)
    assert statement == "Pergunta?"
    assert alternatives["B"] == "dois"


def test_incomplete_alternatives_not_published():
    statement, alternatives = split_alternatives("A decisão foi tomada.\nA texto\nB outro")
    assert not alternatives
    assert "decisão" in statement


def test_extract_auto_section_and_survey_boundary(tmp_path):
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text(
        (50, 70),
        "QUESTÃO 04\nQual é a resposta?\n"
        "A alternativa a\nB alternativa b\nC alternativa c\n"
        "D alternativa d\nE alternativa e",
    )
    p = doc.new_page()
    p.insert_text(
        (50, 70),
        "QUESTÃO 15\nQual é a segunda resposta?\n"
        "A) uma\nB) duas\nC) três\nD) quatro\nE) cinco",
    )
    p = doc.new_page()
    p.insert_text(
        (50, 70),
        "QUESTIONÁRIO DE PERCEPÇÃO DA PROVA\n"
        "QUESTÃO 01\nMarque sua percepção.\n"
        "A concordo\nB discordo\nC talvez\nD nunca\nE sempre",
    )
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    questions = extract(str(path), "https://example.invalid/official.pdf",
                        2023, "Curso de teste", "Área de teste", "auto")
    assert [(q.number, q.section) for q in questions] == [(4, "FG"), (15, "CE")]
    assert questions[0].source_pages == [1]
    assert questions[1].source_pages == [2]
    assert all(q.question_type == "objective" and q.answer is None for q in questions)
    assert questions[0].alternatives["A"] == "alternativa a"
