"""High-level RAG service orchestrating retrieval and generation."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
import re
from typing import Dict, List, Optional, Union

from .config import get_settings
from .llm import LLMClient, LLMCapacityError
from .retriever import EmbeddingCapacityError, RetrievedChunk, Retriever

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    answer: str
    citations: List[Dict]
    chunks: List[Dict]
    latency_ms: float
    retrieval_ms: float
    generation_ms: float


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

    def _normalize_chapter(
        self, chapter: Optional[Union[str, int]], question: str
    ) -> Optional[int]:
        if chapter:
            if isinstance(chapter, int):
                return chapter
            if isinstance(chapter, str):
                digits = re.findall(r"\d+", chapter)
                if digits:
                    return int(digits[0])
        match = re.search(r"chapitre\s+(\d+)", question, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _prepare_history(self, history: Optional[List[Dict]]) -> List[Dict[str, str]]:
        if not history:
            return []
        sanitized: List[Dict[str, str]] = []
        for item in history[-6:]:
            role = str(item.get("role", "user")).strip().lower()
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            sanitized.append({"role": role, "content": content})
        return sanitized

    def answer(
        self,
        question: str,
        mode: str = "standard",
        chapter: Optional[Union[str, int]] = None,
        history: Optional[List[Dict]] = None,
    ) -> RAGResponse:
        if not question.strip():
            raise ValueError("Question must not be empty")
        chapter_hint = self._normalize_chapter(chapter, question)
        history_payload = self._prepare_history(history)
        total_start = time.perf_counter()
        retrieval_start = time.perf_counter()
        try:
            retrieved = self.retriever.search(
                question,
                chapter=chapter_hint,
                history=history_payload,
            )
        except EmbeddingCapacityError:
            logger.warning(
                "Embedding capacity limit reached | mode=%s chapter=%s",
                mode,
                chapter_hint,
            )
            raise
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
        context_payload = [
            {
                "text": chunk.text,
                "chapter": chunk.chapter,
                "page": chunk.page,
                "source_filename": chunk.source_filename,
            }
            for chunk in retrieved
        ]
        llm_start = time.perf_counter()
        try:
            answer = self.llm.generate(
                question,
                context_payload,
                mode=mode,
                chapter=chapter_hint,
                history=history_payload,
            )
        except LLMCapacityError:
            logger.warning(
                "LLM capacity limit reached | mode=%s chapter=%s chunks=%d",
                mode,
                chapter_hint,
                len(retrieved),
            )
            raise
        generation_ms = (time.perf_counter() - llm_start) * 1000
        latency_ms = (time.perf_counter() - total_start) * 1000
        citations = self._format_citations(retrieved)

        logger.info(
            "RAG answer generated | mode=%s chapter=%s chunks=%d retrieval_ms=%.2f generation_ms=%.2f total_ms=%.2f",
            mode,
            chapter_hint,
            len(retrieved),
            retrieval_ms,
            generation_ms,
            latency_ms,
        )

        return RAGResponse(
            answer=answer,
            citations=citations,
            chunks=self._chunks_to_dict(retrieved),
            latency_ms=latency_ms,
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
        )
