"""Build embeddings and FAISS index from processed JSONL chunks."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, Iterable, Iterator, List

import faiss
import numpy as np
import yaml
from mistralai import Mistral
from mistralai.models.sdkerror import SDKError
from tqdm import tqdm


def load_config(config_path: Path) -> Dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_env_from_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def read_jsonl(file_path: Path) -> Iterator[Dict]:
    if not file_path.exists():
        raise FileNotFoundError(f"Processed file missing: {file_path}")
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def gather_chunks(processed_dir: Path, documents: List[Dict]) -> List[Dict]:
    records: List[Dict] = []
    for doc in documents:
        doc_file = processed_dir / f"{doc['id']}.jsonl"
        records.extend(read_jsonl(doc_file))
    if not records:
        raise RuntimeError("No chunks found. Did you run pdf_extractor.py first?")
    return records


def batch_iter(iterable: List[str], size: int) -> Iterator[List[str]]:
    for idx in range(0, len(iterable), size):
        yield iterable[idx : idx + size]


def embed_chunks(chunks: List[Dict], config: Dict) -> np.ndarray:
    provider_cfg = config.get("embeddings", {})
    model_name = provider_cfg.get("model", "mistral-embed")
    batch_size = provider_cfg.get("batch_size", 16)
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY env var is required for embeddings")

    client = Mistral(api_key=api_key)
    texts = [record["text"] for record in chunks]
    embeddings: List[List[float]] = []
    for batch in tqdm(
        batch_iter(texts, batch_size),
        desc="Embedding",
        total=(len(texts) + batch_size - 1) // batch_size,
    ):
        attempts = 3
        response = None
        for attempt in range(1, attempts + 1):
            try:
                response = client.embeddings.create(model=model_name, inputs=batch)
                break
            except SDKError as err:
                status = getattr(err, "status_code", None)
                message = getattr(err, "message", "")
                capacity_hit = status == 429 or "capacity" in message.lower()
                if not capacity_hit or attempt == attempts:
                    raise RuntimeError(
                        "Échec lors de la génération des embeddings (dernier batch)."
                    ) from err
                delay = 1.0 * attempt
                print(
                    f"[warn] Capacité embeddings atteinte (tentative {attempt}/{attempts}). Nouvelle tentative dans {delay:.1f}s",
                    flush=True,
                )
                time.sleep(delay)
        if response is None:
            raise RuntimeError(
                "Aucune réponse reçue du service d'embeddings après plusieurs tentatives."
            )
        embeddings.extend([item.embedding for item in response.data])
    return np.array(embeddings, dtype="float32")


def build_faiss_index(vectors: np.ndarray, config: Dict) -> faiss.Index:
    metric = config.get("vector_store", {}).get("distance_metric", "cosine")
    dim = vectors.shape[1]
    if metric == "cosine":
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(dim)
    elif metric == "l2":
        index = faiss.IndexFlatL2(dim)
    else:
        raise ValueError(f"Unsupported distance metric: {metric}")
    index.add(vectors)
    return index


def write_metadata(chunks: List[Dict], metadata_path: Path) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8") as handle:
        for idx, chunk in enumerate(chunks):
            record = {
                "vector_id": idx,
                "chunk_id": chunk.get("chunk_id"),
                "doc_id": chunk.get("doc_id"),
                "chapter": chunk.get("chapter"),
                "page": chunk.get("page"),
                "source_filename": chunk.get("source_filename"),
                "text": chunk.get("text"),
                "tokens": chunk.get("tokens"),
                "tags": chunk.get("tags", []),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run(doc_ids: Iterable[str] | None = None) -> None:
    root = Path(__file__).resolve().parents[2]
    load_env_from_file(root / ".env")
    config_path = root / "config" / "docs.yaml"
    config = load_config(config_path)
    documents = config.get("documents", [])
    if doc_ids:
        wanted = set(doc_ids)
        documents = [doc for doc in documents if doc["id"] in wanted]
    processed_dir = root / "data" / "processed"

    print("Collecting chunks...")
    chunks = gather_chunks(processed_dir, documents)
    print(f"Loaded {len(chunks)} chunks from {len(documents)} documents")

    vectors = embed_chunks(chunks, config)
    print("Embeddings computed, building FAISS index...")
    index = build_faiss_index(vectors, config)

    vector_store_cfg = config.get("vector_store", {})
    index_path = root / vector_store_cfg.get(
        "index_path", "data/metadata/vector_store.faiss"
    )
    metadata_path = root / vector_store_cfg.get(
        "metadata_store", "data/metadata/chunks.jsonl"
    )

    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    write_metadata(chunks, metadata_path)
    print(f"Index stored at {index_path}")
    print(f"Metadata stored at {metadata_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build FAISS index from processed chunks"
    )
    parser.add_argument(
        "--doc-id",
        nargs="*",
        help="Optional document ids to limit the index",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.doc_id)
