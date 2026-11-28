"""Extrator heurístico de questões OBJETIVAS ENADE: resultados não auditados.

Usar --section auto para classificar FG (01-09) e CE (10-38).
Exige alternativas A-E completas; não infere respostas, imagens ou qualidade.
"""
import argparse
import bisect
import json
import re
from pathlib import Path

import fitz
from app.schema import Question, stable_question_id

QUESTION_PATTERN = re.compile(r"(?im)^[ \t]*QUEST[ÃA]O[ \t]+0?(\d{1,3})\b")
SURVEY_PATTERN = re.compile(
    r"(?im)^[ \t]*QUESTION[ÁA]RIO[ \t]+(?:DE[ \t]+PERCEP[ÇC][ÃA]O|DO[ \t]+ESTUDANTE)\b"
)
ALTERNATIVE_LINE = re.compile(r"^[ \t]*([A-E])(?:[).]|[ \t]+)(.*)$")
LETTER_ONLY_LINE = re.compile(r"^[ \t]*([A-E])[ \t]*$")


def split_alternatives(block: str) -> tuple[str, dict[str, str]]:
    """Identifica A-E nas formas 'A)', 'A.' ou 'A texto'.

    Se não houver sequência completa, não classificar como objetiva extraída.
    """
    lines = block.splitlines()
    markers = []
    for index, line in enumerate(lines):
        match = ALTERNATIVE_LINE.match(line)
        if match:
            markers.append((index, match.group(1), match.group(2).strip()))
        else:
            match = LETTER_ONLY_LINE.match(line)
            if match:
                markers.append((index, match.group(1), ""))
    for start in range(len(markers)):
        sequence = markers[start:start + 5]
        if len(sequence) < 5 or [entry[1] for entry in sequence] != list("ABCDE"):
            continue
        answers = {}
        for i, (line_index, letter, first) in enumerate(sequence):
            next_line = sequence[i + 1][0] if i < 4 else len(lines)
            answer = "\n".join(([first] if first else []) + lines[line_index + 1:next_line]).strip()
            if not answer:
                break
            answers[letter] = answer
        statement = "\n".join(lines[:sequence[0][0]]).strip()
        if len(answers) == 5 and statement:
            return statement, answers
    return block.strip(), {}


def extract(pdf: str, source_url: str, year: int, course: str,
            area: str, section: str = "auto"):
    if section not in ("auto", "FG", "CE"):
        raise ValueError("Seção deve ser auto, FG ou CE")
    pages = []
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc):
            pages.append((i + 1, page.get_text(sort=True)))
    if not pages:
        return []
    offsets = []
    length = 0
    for _page, text in pages:
        offsets.append(length)
        length += len(text) + 1
    text = "\n".join(page_text for _num, page_text in pages)
    survey = SURVEY_PATTERN.search(text)
    if survey:
        text = text[:survey.start()]
    matches = [m for m in QUESTION_PATTERN.finditer(text) if 1 <= int(m.group(1)) <= 38]
    results = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end].strip()
        if not block:
            continue
        number = int(match.group(1))
        question_section = ("FG" if number <= 9 else "CE") if section == "auto" else section
        statement, alternatives = split_alternatives(block)
        if len(alternatives) != 5:
            continue  # Não inventar classificação discursiva para bloco incompleto.
        start_page = pages[bisect.bisect_right(offsets, match.start()) - 1][0]
        end_page = pages[bisect.bisect_right(offsets, max(match.end(), end - 1)) - 1][0]
        results.append(Question(
            id=stable_question_id(source_url, year, course, question_section, number),
            year=year, area=area, course=course, section=question_section, number=number,
            question_type="objective", statement=statement, context=None,
            alternatives=alternatives, answer=None, annulled=False,
            competencies=[], knowledge_objects=[], source_pdf=source_url,
            source_pages=list(range(start_page, end_page + 1)),
        ))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--course", required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument("--section", default="auto", choices=["auto", "FG", "CE"])
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    questions = extract(args.pdf, args.source_url, args.year, args.course, args.area, args.section)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(q.model_dump(), ensure_ascii=False) + "\n"
                           for q in questions), encoding="utf-8")
    print(f"Extraídos {len(questions)} candidatos objetivos; revisão manual obrigatória: {out}")


if __name__ == "__main__":
    main()
