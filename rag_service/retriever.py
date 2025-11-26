"""Retriever utilities wrapping FAISS and metadata lookups."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Optional

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
        self.chapter_to_ids = self._build_chapter_index(self.metadata)

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

    def _build_chapter_index(self, metadata: List[Dict]) -> Dict[int, List[int]]:
        mapping: Dict[int, List[int]] = defaultdict(list)
        for idx, record in enumerate(metadata):
            chapter = record.get("chapter")
            try:
                chapter_int = int(chapter)
            except (TypeError, ValueError):
                continue
            mapping[chapter_int].append(idx)
        return mapping

    def _record_to_chunk(self, record: Dict, score: float) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=record.get("chunk_id"),
            text=record.get("text", ""),
            score=float(score),
            chapter=record.get("chapter"),
            page=record.get("page"),
            source_filename=record.get("source_filename"),
            tags=record.get("tags", []),
        )

    def _embed_query(self, query: str) -> np.ndarray:
        response = self.client.embeddings.create(model=self.embed_model, inputs=[query])
        vector = np.array(response.data[0].embedding, dtype="float32")
        faiss.normalize_L2(vector.reshape(1, -1))
        return vector.reshape(1, -1)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        chapter: int | None = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[RetrievedChunk]:
        if not query.strip():
            raise ValueError("Query must not be empty")
        _ = history  # Currently unused but reserved for future personalization.
        k = top_k or self.top_k
        query_vec = self._embed_query(query)
        scores, ids = self.index.search(query_vec, k)
        results: List[RetrievedChunk] = []
        seen_ids: Set[int] = set()
        for score, vector_id in zip(scores[0], ids[0]):
            if vector_id == -1:
                continue
            seen_ids.add(int(vector_id))
            record = self.metadata[vector_id]
            results.append(self._record_to_chunk(record, score))

        if chapter is not None:
            self._extend_with_chapter(results, seen_ids, k, chapter)

        return results[:k]

    def _extend_with_chapter(
        self,
        results: List[RetrievedChunk],
        seen_ids: Set[int],
        limit: int,
        chapter: int,
    ) -> None:
        candidate_ids = self.chapter_to_ids.get(chapter, [])
        for vector_id in candidate_ids:
            if len(results) >= limit:
                break
            if vector_id in seen_ids:
                continue
            seen_ids.add(vector_id)
            record = self.metadata[vector_id]
            # Score arbitraire faible puisqu'il provient d'un élargissement manuel.
            results.append(self._record_to_chunk(record, score=0.0))
