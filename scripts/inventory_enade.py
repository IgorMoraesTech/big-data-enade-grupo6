
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifest.csv"

FIELDS = (
    "ano",
    "curso",
    "area",
    "tipo_documento",
    "formato",
    "url_oficial",
    "nome_arquivo",
    "status_link",
    "status_local",
)

VALID_LINK_STATUS = {"disponivel", "ausente", "quebrado", "nao_verificado"}
VALID_LOCAL_STATUS = {"baixado", "nao_baixado", "invalido", "ausente"}
DOCUMENT_FORMATS = {
    "prova": "pdf",
    "gabarito": "pdf",
    "padrao_resposta": "pdf",
    "diretriz": "html",
}


def load_manifest(path: Path = MANIFEST) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"Colunas inválidas: esperado {', '.join(FIELDS)}")
        rows = list(reader)

    seen: set[tuple[str, str, str]] = set()

    for line, row in enumerate(rows, start=2):
        if row["status_link"] not in VALID_LINK_STATUS:
            raise ValueError(f"Status de link inválido na linha {line}")
        if row["status_local"] not in VALID_LOCAL_STATUS:
            raise ValueError(f"Status local inválido na linha {line}")

        expected_format = DOCUMENT_FORMATS.get(row["tipo_documento"])
        if expected_format is None or row["formato"] != expected_format:
            raise ValueError(f"Formato inválido na linha {line}")

        if not row["ano"].isdigit() or not row["curso"].strip() or not row["area"].strip():
            raise ValueError(f"Metadados obrigatórios ausentes na linha {line}")

        key = (row["ano"], row["curso"], row["tipo_documento"])
        if key in seen:
            raise ValueError(f"Documento duplicado no manifesto na linha {line}: {key}")
        seen.add(key)

        if row["status_link"] == "ausente" or row["status_local"] == "ausente":
            if (
                row["status_link"] != "ausente"
                or row["status_local"] != "ausente"
                or row["url_oficial"]
                or row["nome_arquivo"]
            ):
                raise ValueError(
                    f"Documento ausente não pode ter URL/nome de arquivo (linha {line})"
                )
            continue

        parsed = urlparse(row["url_oficial"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"URL HTTPS inválida na linha {line}")

        if not row["nome_arquivo"].strip():
            raise ValueError(f"Nome de arquivo obrigatório na linha {line}")

        suffix = Path(row["nome_arquivo"]).suffix.lower().lstrip(".")
        if suffix != row["formato"]:
            raise ValueError(f"Extensão incompatível com o formato na linha {line}")

    return rows


def check_url(client: httpx.Client, url: str) -> str:
    try:
        response = client.head(url, follow_redirects=True)

        if response.status_code in {405, 501}:
            response = client.get(
                url,
                headers={"Range": "bytes=0-0"},
                follow_redirects=True,
            )

        if 200 <= response.status_code < 400:
            return "disponivel"
        if response.status_code in {404, 410}:
            return "quebrado"
        return "nao_verificado"
    except httpx.HTTPError:
        return "nao_verificado"


def update_link_statuses(
    rows: list[dict[str, str]],
    timeout: float = 20.0,
) -> None:
    with httpx.Client(
        timeout=timeout,
        headers={"User-Agent": "ENADE-acervo-inventory/1.0"},
    ) as client:
        for row in rows:
            if row["status_link"] == "ausente":
                continue
            row["status_link"] = check_url(client, row["url_oficial"])


def update_local_statuses(
    rows: list[dict[str, str]],
    directory: Path,
) -> None:
    for row in rows:
        if row["status_local"] == "ausente":
            continue

        file_path = directory / row["nome_arquivo"]
        row["status_local"] = (
            "baixado" if file_path.is_file() else "nao_baixado"
        )


def count_files(rows: list[dict[str, str]], directory: Path) -> int:
    return sum(
        1
        for row in rows
        if row["nome_arquivo"]
        and (directory / row["nome_arquivo"]).is_file()
    )


def count_processed(rows: list[dict[str, str]], directory: Path) -> int:
    return sum(
        1
        for row in rows
        if row["tipo_documento"] == "prova"
        and row["nome_arquivo"]
        and (directory / f"{Path(row['nome_arquivo']).stem}.jsonl").is_file()
    )


def summarize(
    rows: list[dict[str, str]],
    root: Path = ROOT,
) -> dict[str, int]:
    link_counts = Counter(row["status_link"] for row in rows)
    local_counts = Counter(row["status_local"] for row in rows)

    return {
        "identificados": len(rows),
        "disponiveis": link_counts["disponivel"],
        "ausentes": link_counts["ausente"],
        "quebrados": link_counts["quebrado"],
        "nao_verificados": link_counts["nao_verificado"],
        "baixados": count_files(rows, root / "data" / "raw"),
        "nao_baixados": local_counts["nao_baixado"],
        "invalidos": local_counts["invalido"],
        "processados": count_processed(rows, root / "data" / "output"),
    }


def write_manifest(
    rows: list[dict[str, str]],
    path: Path = MANIFEST,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida e resume o manifesto oficial do ENADE."
    )
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Verifica a disponibilidade das URLs oficiais.",
    )
    parser.add_argument(
        "--check-local",
        action="store_true",
        help="Atualiza a situação dos arquivos em data/raw.",
    )
    args = parser.parse_args()

    rows = load_manifest(args.manifest)
    root = args.manifest.resolve().parent.parent

    if args.check_links:
        update_link_statuses(rows)

    if args.check_local:
        update_local_statuses(rows, root / "data" / "raw")

    if args.check_links or args.check_local:
        write_manifest(rows, args.manifest)

    for key, value in summarize(rows, root).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
