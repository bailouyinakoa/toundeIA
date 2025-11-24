"""CLI tool to convert course PDFs into normalized JSONL chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

import yaml
from pypdf import PdfReader


def load_config(config_path: Path) -> Dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def fetch_documents(
    config: Dict, target_ids: Iterable[str] | None = None
) -> List[Dict]:
    documents = config.get("documents", [])
    if target_ids:
        wanted = set(target_ids)
        documents = [doc for doc in documents if doc["id"] in wanted]
        missing = wanted - {doc["id"] for doc in documents}
        if missing:
            raise ValueError(f"Unknown document ids: {', '.join(sorted(missing))}")
    return documents


def extract_pdf_text(pdf_path: Path) -> List[str]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        clean = text.replace("\r", "\n").replace("\xa0", " ")
        pages.append((page_number, clean.strip()))
        if page_number % 10 == 0:
            print(f"   - extrait {page_number} pages sur {len(reader.pages)}")
    return pages


def chunk_text(text: str, chunk_size: int, overlap: int):
    """Yield successive chunks without storing them all in memory."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    start = 0
    step = chunk_size - overlap
    length = len(text)
    while start < length:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            yield chunk
        if end >= length:
            break
        start += step


def build_output_records(doc: Dict, pages: List[str], config: Dict):
    chunk_cfg = config.get("chunking", {})
    chunk_size = chunk_cfg.get("chunk_size", 500)
    chunk_overlap = chunk_cfg.get("chunk_overlap", 80)
    chunk_idx = 0
    for page_number, page_text in pages:
        for chunk in chunk_text(page_text, chunk_size, chunk_overlap):
            chunk_idx += 1
            yield {
                "chunk_id": f"{doc['id']}::{chunk_idx}",
                "doc_id": doc["id"],
                "chapter": doc.get("chapter"),
                "section": None,
                "source_filename": doc["filename"],
                "page": page_number,
                "text": chunk,
                "tokens": len(chunk.split()),
                "tags": doc.get("topics", []),
            }


def write_jsonl(records, output_path: Path) -> int:
    """Stream records to disk and return how many were written."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
            if count % 500 == 0:
                print(f"   - {count} chunks écrits...")
    return count


def run(doc_ids: Iterable[str] | None = None) -> None:
    root = Path(__file__).resolve().parents[2]
    config_path = root / "config" / "docs.yaml"
    config = load_config(config_path)
    documents = fetch_documents(config, doc_ids)

    processed_dir = root / "data" / "processed"
    try:
        for doc in documents:
            pdf_path = root / doc["filename"]
            print(f"Processing {doc['id']} ({pdf_path})...")
            pages = extract_pdf_text(pdf_path)
            records = build_output_records(doc, pages, config)
            output_file = processed_dir / f"{doc['id']}.jsonl"
            chunk_count = write_jsonl(records, output_file)
            print(f"[ok] {doc['id']}: {chunk_count} chunks -> {output_file}")
    except KeyboardInterrupt:
        print(
            "[warn] Extraction interrompue par l'utilisateur. Le dernier fichier peut être incomplet."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract PDFs defined in config/docs.yaml"
    )
    parser.add_argument(
        "--doc-id",
        nargs="*",
        help="Optional document ids to process (default: all)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.doc_id)
