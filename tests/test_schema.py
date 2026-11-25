import pytest
from pydantic import ValidationError

from app.schema import Question, stable_question_id


def sample():
    return dict(id="sample-123", year=2023, area="Formação Geral",
                course="Curso Fictício", section="FG", number=1,
                question_type="objective", statement="Questão fictícia",
                source_pdf="ficticio.pdf", source_pages=[1])


def test_stable_id_is_deterministic_and_changes_with_question():
    a = stable_question_id("x.pdf", 2023, "SI", "CE", 1)
    assert len(a) == 64
    assert a == stable_question_id("x.pdf", 2023, "SI", "CE", 1)
    assert a != stable_question_id("x.pdf", 2023, "SI", "CE", 2)


def test_invalid_section_rejected():
    data = sample()
    data["section"] = "INVALID"
    with pytest.raises(ValidationError):
        Question.model_validate(data)


def test_unknown_answers_remain_unknown():
    question = Question.model_validate(sample())
    assert question.answer is None
    assert question.competencies == []
