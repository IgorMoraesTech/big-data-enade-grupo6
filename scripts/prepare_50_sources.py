"""Prepara as provas oficiais do ENADE 2023 e localiza candidatos à revisão.

Este módulo NÃO executa auditoria humana e NÃO atribui taxa de acerto.
Uso:
  python -m scripts.prepare_50_sources --download
  python -m scripts.prepare_50_sources
Os PDFs locais ficam em data/raw/ (fora do versionamento Git).
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

import fitz

from scripts.validation_50 import make_rows

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "evidence"
QUESTION_HEADING = re.compile(r"(?im)^\s*QUEST[ÃA]O\s*0?(\d{1,2})\b")
MAX_DOWNLOAD = 35 * 1024 * 1024
SOURCES = {
    "Enfermagem": (
        "2023_PV_enfermagem.pdf",
        "https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_enfermagem.pdf",
    ),
    "Fisioterapia": (
        "2023_PV_fisioterapia.pdf",
        "https://download.inep.gov.br/enade/provas_e_gabaritos/2023_PV_fisioterapia.pdf",
    ),
}


def download_pdf(url: str, target: Path) -> dict:
    """Valida a assinatura PDF antes de substituir qualquer arquivo local."""
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    try:
        request = Request(url, headers={"User-Agent": "ENADE-Academic-Validation/1.0"})
        digest = hashlib.sha256()
        total = 0
        with urlopen(request, timeout=45) as response, part.open("wb") as out:
            for chunk in iter(lambda: response.read(1024 * 256), b""):
                total += len(chunk)
                if total > MAX_DOWNLOAD:
                    raise ValueError("PDF excede o limite de 35 MiB")
                digest.update(chunk)
                out.write(chunk)
        with part.open("rb") as stream:
            if not stream.read(5) == b"%PDF-":
                raise ValueError("Fonte não forneceu PDF (assinatura inválida)")
        with fitz.open(part) as doc:
            if len(doc) == 0:
                raise ValueError("PDF sem páginas")
            pages = len(doc)
        part.replace(target)
        return {"sha256": digest.hexdigest(), "bytes": total, "pages": pages}
    finally:
        if part.exists():
            part.unlink()


def scan_pdf(path: Path) -> dict:
    """Encontra títulos de questões por página; não afirma que sejam corretos."""
    candidates = {}
    with fitz.open(path) as pdf:
        for page_i, page in enumerate(pdf):
            text = page.get_text(sort=True)
            for match in QUESTION_HEADING.finditer(text):
                number = int(match.group(1))
                if 1 <= number <= 38:
                    candidates.setdefault(number, []).append({
                        "pagina_fisica_candidata": page_i + 1,
                        "trecho_extraido": text[match.end():match.end() + 160].replace("\n", " ").strip(),
                    })
    return candidates


def generate(pdf_dir: Path, output_dir: Path, download: bool = False):
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = make_rows()
    summary = {
        "status": "candidatos_automaticos_nao_auditados",
        "requested_questions": len(rows),
        "human_reviews_completed": 0,
        "sources": {},
    }
    for course, (filename, url) in SOURCES.items():
        path = pdf_dir / filename
        if download:
            info = download_pdf(url, path)
        else:
            if not path.is_file():
                raise FileNotFoundError(
                    f"PDF oficial ausente: {path}. Rode com --download ou salve o PDF nesse local."
                )
            with fitz.open(path) as pdf:
                info = {"bytes": path.stat().st_size, "pages": len(pdf)}
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(256 * 1024), b""):
                    digest.update(chunk)
            info["sha256"] = digest.hexdigest()
        headings = scan_pdf(path)
        summary["sources"][course] = {
            "source_pdf": url,
            "filename": filename,
            "integrity": info,
            "question_heading_numbers_observed": len(headings),
        }
        for row in rows:
            if row["curso"] != course:
                continue
            candidates = headings.get(int(row["questao"]), [])
            row["cabecalhos_detectados"] = str(len(candidates))
            row["paginas_candidatas_nao_confirmadas"] = ";".join(
                str(c["pagina_fisica_candidata"]) for c in candidates
            )
            row["trechos_candidatos"] = " | ".join(
                c["trecho_extraido"][:100] for c in candidates[:3]
            )
            row["status_revisao"] = "pendente"
            # Deliberadamente NÃO preenche pagina_pdf_confirmada nem campos de acerto.
    output = output_dir / "validation_50_candidates.csv"
    fieldnames = list(rows[0])  # colunas originais + colunas dos candidatos
    for extra in ("cabecalhos_detectados", "paginas_candidatas_nao_confirmadas", "trechos_candidatos"):
        if extra not in fieldnames:
            fieldnames.append(extra)
    with output.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    report_path = output_dir / "validation_50_source_report.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, report_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Baixar os PDFs diretamente do INEP")
    parser.add_argument("--pdf-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    csv_path, report_path = generate(args.pdf_dir, args.output_dir, args.download)
    print(f"Candidatos NÃO REVISADOS: {csv_path}")
    print(f"Fontes, hashes e metadados: {report_path}")


if __name__ == "__main__":
    main()
