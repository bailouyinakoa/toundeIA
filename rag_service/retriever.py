"""Retriever utilities wrapping FAISS and metadata lookups."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import faiss
import numpy as np
from mistralai import Mistral

from .config import get_settings


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    chapter: int | None
    page: int | None
    source_filename: str | None
    tags: Sequence[str]


class Retriever:
    def __init__(self) -> None:
        settings = get_settings()
        self.index_path = Path(settings["vector_store_path"])
        self.metadata_path = Path(settings["metadata_path"])
        self.top_k = settings["top_k"]
        self.embed_model = settings["embedding_model"]
        api_key = settings["mistral_api_key"]
        if not api_key:
            raise RuntimeError("Missing MISTRAL_API_KEY in environment")
        self.client = Mistral(api_key=api_key)
        self.index = self._load_faiss_index()
        self.metadata = self._load_metadata()

    def _load_faiss_index(self) -> faiss.Index:
        if not self.index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {self.index_path}")
        index = faiss.read_index(str(self.index_path))
        return index

    def _load_metadata(self) -> List[Dict]:
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")
        metadata: List[Dict] = []
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    metadata.append(json.loads(line))
        if len(metadata) != self.index.ntotal:
            raise RuntimeError(
                "Metadata count and FAISS vectors mismatch: "
                f"{len(metadata)} vs {self.index.ntotal}"
            )
        return metadata

    def _embed_query(self, query: str) -> np.ndarray:
        response = self.client.embeddings.create(model=self.embed_model, inputs=[query])
        vector = np.array(response.data[0].embedding, dtype="float32")
        faiss.normalize_L2(vector.reshape(1, -1))
        return vector.reshape(1, -1)

    def search(self, query: str, top_k: int | None = None) -> List[RetrievedChunk]:
        if not query.strip():
            raise ValueError("Query must not be empty")
        k = top_k or self.top_k
        query_vec = self._embed_query(query)
        scores, ids = self.index.search(query_vec, k)
        results = []
        for score, vector_id in zip(scores[0], ids[0]):
            if vector_id == -1:
                continue
            record = self.metadata[vector_id]
            results.append(
                RetrievedChunk(
                    chunk_id=record.get("chunk_id"),
                    text=record.get("text", ""),
                    score=float(score),
                    chapter=record.get("chapter"),
                    page=record.get("page"),
                    source_filename=record.get("source_filename"),
                    tags=record.get("tags", []),
                )
            )
        return results
