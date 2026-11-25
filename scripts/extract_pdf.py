"""Extração textual exploratória de provas ENADE.

ATENÇÃO: PDFs variam muito. Este script trata padrões simples de "QUESTÃO N"
e NÃO garante extração multimodal, classificação completa ou cobertura integral.
Revisar cada questão antes de publicar.
Uso: python -m scripts.extract_pdf --pdf caminho.pdf --year 2023
     --course "Sistemas de Informação" --area "Tecnologia" --section CE
     --source-url https://.../prova.pdf --output data/output/questoes.jsonl
"""
import argparse
import json
import re
from pathlib import Path

import fitz

from app.schema import Question, stable_question_id

QUESTION_PATTERN = re.compile(r"(?im)^\s*QUEST[ÃA]O\s+(\d{1,3})\b")
ALTERNATIVE_PATTERN = re.compile(r"(?m)^\s*([A-E])\s*[)\.]\s+(.+?)(?=^\s*[A-E]\s*[)\.]|\Z)", re.S)


def extract(pdf: str, source_url: str, year: int, course: str, area: str, section: str):
    pages = []
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc):
            pages.append((i + 1, page.get_text(sort=True)))
    all_text = "\n".join(text for _num, text in pages)
    matches = list(QUESTION_PATTERN.finditer(all_text))
    results = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(all_text)
        start = match.end()
        block = all_text[start:end].strip()
        if not block:
            continue
        number = int(match.group(1))
        alternatives = {key: text.strip() for key, text in ALTERNATIVE_PATTERN.findall(block)}
        statement = ALTERNATIVE_PATTERN.split(block)[0].strip() if alternatives else block
        # A posição no texto concatenado determina a página inicial da questão.
        prefix_length = 0
        page_start = 1
        page_end = 1
        for page_num, text in pages:
            length = len(text) + 1
            if prefix_length <= match.start() < prefix_length + length:
                page_start = page_num
            if prefix_length <= end - 1 < prefix_length + length:
                page_end = page_num
            prefix_length += length
        results.append(Question(
            id=stable_question_id(source_url, year, course, section, number),
            year=year, area=area, course=course, section=section, number=number,
            question_type="objective" if alternatives else "discursive",
            statement=statement, context=None, alternatives=alternatives,
            answer=None, annulled=False, competencies=[], knowledge_objects=[],
            source_pdf=source_url,
            source_pages=list(range(page_start, max(page_start, page_end) + 1)),
        ))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--course", required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument("--section", required=True, choices=["FG", "CE"])
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    questions = extract(args.pdf, args.source_url, args.year, args.course, args.area, args.section)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(x.model_dump(), ensure_ascii=False) + "\n" for x in questions),
                   encoding="utf-8")
    print(f"Extraídas {len(questions)} questões (REVISÃO MANUAL OBRIGATÓRIA) para {out}")


if __name__ == "__main__":
    main()
