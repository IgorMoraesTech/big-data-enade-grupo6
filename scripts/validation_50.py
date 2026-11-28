"""Plano auditável de revisão: 25 questões objetivas por curso ENADE 2023.

A geração NÃO avalia a extração nem atribui taxas de acerto.
Só publica métricas após 50 conferências humanas devidamente registradas.
"""
import argparse
import csv
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

COURSES = {
    "Enfermagem": "https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_enfermagem.pdf",
    "Fisioterapia": "https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_fisioterapia.pdf",
}
QUESTION_NUMBERS = (1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16, 18, 19, 21, 23, 24, 26, 27, 29, 30, 32, 33, 35, 36, 38)
CHECK_FIELDS = ("numero_ok", "secao_ok", "tipo_ok", "enunciado_ok", "alternativas_ok", "paginas_ok")
FIELDS = [
    "ano", "curso", "questao", "secao_esperada", "tipo_esperado",
    "url_pdf_oficial", "pagina_pdf_confirmada", "caminho_jsonl_extraido",
    *CHECK_FIELDS, "categoria_erro", "observacoes",
    "revisor", "data_revisao", "status_revisao",
]


def make_rows():
    rows = []
    for course, url in COURSES.items():
        for number in QUESTION_NUMBERS:
            rows.append({
                "ano": "2023", "curso": course, "questao": str(number).zfill(2),
                "secao_esperada": "FG" if number <= 9 else "CE",
                "tipo_esperado": "objective", "url_pdf_oficial": url,
                "pagina_pdf_confirmada": "", "caminho_jsonl_extraido": "",
                **{field: "" for field in CHECK_FIELDS},
                "categoria_erro": "", "observacoes": "", "revisor": "",
                "data_revisao": "", "status_revisao": "pendente",
            })
    assert len(rows) == 50
    return rows


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as src:
        reader = csv.DictReader(src)
        if reader.fieldnames != FIELDS:
            raise ValueError("Cabeçalho do CSV diferente do modelo versionado")
        return list(reader)


def assess(rows):
    expected = {(r["curso"], r["questao"]): r for r in make_rows()}
    keys = [(r["curso"], r["questao"]) for r in rows]
    if len(rows) != 50 or set(keys) != set(expected) or len(set(keys)) != 50:
        raise ValueError("A avaliação exige 50 questões distintas (25 por curso)")
    errors = []
    for row in rows:
        question = f'{row["curso"]} questão {row["questao"]}'
        baseline = expected[(row["curso"], row["questao"])]
        for field in ("ano", "secao_esperada", "tipo_esperado", "url_pdf_oficial"):
            if row[field] != baseline[field]:
                errors.append(f"{question}: {field} difere do plano")
        if row["status_revisao"] != "verificado":
            errors.append(f"{question}: não verificada")
        if not row["revisor"].strip():
            errors.append(f"{question}: revisor ausente")
        try:
            date.fromisoformat(row["data_revisao"])
        except ValueError:
            errors.append(f"{question}: data_revisao inválida")
        if not re.fullmatch(r"\d+(?:\s*;\s*\d+)*", row["pagina_pdf_confirmada"].strip()):
            errors.append(f"{question}: páginas não confirmadas")
        if not row["caminho_jsonl_extraido"].strip():
            errors.append(f"{question}: arquivo JSONL não registrado")
        for field in CHECK_FIELDS:
            if row[field] not in ("certo", "errado"):
                errors.append(f"{question}: preencher {field} com certo/errado")
        if any(row[field] == "errado" for field in CHECK_FIELDS) and not row["categoria_erro"].strip():
            errors.append(f"{question}: categoria de erro ausente")
    if errors:
        raise ValueError(f"Avaliação incompleta: {len(errors)} pendências. " + "; ".join(errors[:8]))
    correct = {field: sum(row[field] == "certo" for row in rows) for field in CHECK_FIELDS}
    all_correct = sum(all(row[field] == "certo" for field in CHECK_FIELDS) for row in rows)
    return {
        "status": "50_revisoes_registradas",
        "method": "Comparação manual declarada por revisor para cada campo",
        "total": 50, "por_curso": dict(Counter(r["curso"] for r in rows)),
        "acertos_por_campo": {
            k: {"corretos": v, "total": 50, "taxa": round(v / 50, 4)}
            for k, v in correct.items()
        },
        "registros_totalmente_corretos": all_correct,
        "taxa_registro_integral": round(all_correct / 50, 4),
        "limitacoes": "Depende da auditoria humana real; não avalia questões discursivas, imagens ou gabaritos",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", type=Path, default=Path("evidence/validation_50_template.csv"))
    report = sub.add_parser("report")
    report.add_argument("--input", type=Path, required=True)
    report.add_argument("--output", type=Path, default=Path("evidence/validation_50_results.json"))
    args = parser.parse_args(argv)
    if args.command == "prepare":
        write_csv(args.output, make_rows())
        print(f"Geradas 50 linhas PENDENTES: {args.output}")
    else:
        result = assess(read_csv(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
