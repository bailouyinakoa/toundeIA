"""High-level RAG service orchestrating retrieval and generation."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from .config import get_settings
from .llm import LLMClient
from .retriever import RetrievedChunk, Retriever


@dataclass
class RAGResponse:
    answer: str
    citations: List[Dict]
    chunks: List[Dict]
    latency_ms: float


class RAGService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings["mistral_api_key"]:
            raise RuntimeError("MISTRAL_API_KEY is required")
        self.retriever = Retriever()
        self.llm = LLMClient()

    def _format_citations(self, chunks: List[RetrievedChunk]) -> List[Dict]:
        citations = []
        for idx, chunk in enumerate(chunks, start=1):
            citations.append(
                {
                    "label": f"[{idx}] Chapitre {chunk.chapter or '?'}",
                    "page": chunk.page,
                    "source": chunk.source_filename,
                    "tags": list(chunk.tags),
                    "score": chunk.score,
                }
            )
        return citations

    def _chunks_to_dict(self, chunks: List[RetrievedChunk]) -> List[Dict]:
        return [asdict(chunk) for chunk in chunks]

    def answer(
        self,
        question: str,
        mode: str = "standard",
        history: Optional[List[Dict]] = None,
    ) -> RAGResponse:
        if not question.strip():
            raise ValueError("Question must not be empty")
        start = time.perf_counter()
        retrieved = self.retriever.search(question)
        context_payload = [
            {
                "text": chunk.text,
                "chapter": chunk.chapter,
                "page": chunk.page,
                "source_filename": chunk.source_filename,
            }
            for chunk in retrieved
        ]
        answer = self.llm.generate(question, context_payload, mode=mode)
        latency_ms = (time.perf_counter() - start) * 1000
        citations = self._format_citations(retrieved)
        return RAGResponse(
            answer=answer,
            citations=citations,
            chunks=self._chunks_to_dict(retrieved),
            latency_ms=latency_ms,
        )
