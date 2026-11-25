"""Contrato estrito dos documentos indexados."""
import hashlib

from pydantic import BaseModel, Field, ConfigDict


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=8)
    year: int = Field(ge=2004, le=2100)
    area: str = Field(min_length=1)
    course: str = Field(min_length=1)
    section: str = Field(pattern=r"^(FG|CE)$")
    number: int = Field(ge=1)
    question_type: str = Field(pattern=r"^(objective|discursive)$")
    statement: str = Field(min_length=1)
    context: str | None = None
    alternatives: dict[str, str] = Field(default_factory=dict)
    answer: str | None = None
    annulled: bool = False
    competencies: list[str] = Field(default_factory=list)
    knowledge_objects: list[str] = Field(default_factory=list)
    source_pdf: str = Field(min_length=1)
    source_pages: list[int] = Field(min_length=1)


def stable_question_id(source_pdf: str, year: int, course: str, section: str, number: int) -> str:
    raw = f"{source_pdf}|{year}|{course}|{section}|{number}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
