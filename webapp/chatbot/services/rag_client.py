from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings

logger = logging.getLogger(__name__)


class RAGServiceError(Exception):
    """Erreur levée quand le service RAG sous-jacent tombe en panne."""


@dataclass
class SourceChunk:
    title: str
    path: str
    score: float
    chunk_id: str | None = None
    extra: Dict[str, Any] | None = None


ROOT_DIR = Path(getattr(settings, "ROOT_DIR", Path(__file__).resolve().parents[3]))
if str(ROOT_DIR) not in sys.path:
    #le dossier racine pour permettre l'import du package rag_service local.
    sys.path.append(str(ROOT_DIR))


class RAGClient:
    """Client léger qui délègue aux fonctions du package python rag_service."""

    def __init__(self) -> None:
        try:
            from rag_service import RAGService  # type: ignore
        except Exception as exc:  # pragma: no cover - module facultatif en dev
            logger.warning("rag_service import failed: %s", exc)
            self._service = None
        else:
            try:
                self._service = RAGService()
            except Exception as exc:  # pragma: no cover - journalisation défensive
                logger.exception("Impossible d'initialiser RAGService")
                self._service = None

    def _format_sources(self, response) -> List[Dict[str, Any]]:
        chunks = response.chunks if hasattr(response, "chunks") else []
        citations = response.citations if hasattr(response, "citations") else []
        sources = []
        for idx, chunk in enumerate(chunks):
            citation = citations[idx] if idx < len(citations) else {}
            sources.append(
                {
                    "title": citation.get("label", f"Source {idx + 1}"),
                    "path": chunk.get("source_filename", ""),
                    "chunk_id": chunk.get("chunk_id"),
                    "score": citation.get("score", 0.0),
                    "extra": {
                        "chapter": chunk.get("chapter"),
                        "page": chunk.get("page"),
                        "tags": chunk.get("tags", []),
                        "citation": citation,
                        "text": chunk.get("text"),
                    },
                }
            )
        return sources

    def answer(
        self, question: str, mode: str, history: List[Dict[str, str]] | None = None
    ) -> Dict[str, Any]:
        if not self._service:
            logger.info(
                "Réponse RAG de secours utilisée pour la question : %s", question
            )
            return {
                "answer": "Le service RAG n'est pas encore connecté. Voici une réponse générique.",
                "sources": [],
                "metadata": {"mode": mode, "history_size": len(history or [])},
            }

        try:
            rag_response = self._service.answer(
                question=question.strip(), mode=mode, history=history or []
            )
        except Exception as exc:  # pragma: no cover - journalisation défensive
            logger.exception("Erreur lors de l'appel au backend RAG")
            raise RAGServiceError(
                "Impossible d'obtenir une réponse pour le moment"
            ) from exc

        return {
            "answer": rag_response.answer,
            "sources": self._format_sources(rag_response),
            "metadata": {
                "mode": mode,
                "history_size": len(history or []),
                "citations": getattr(rag_response, "citations", []),
                "latency_ms": getattr(rag_response, "latency_ms", 0.0),
            },
        }


_client: RAGClient | None = None


def get_rag_client() -> RAGClient:
    global _client
    if _client is None:
        _client = RAGClient()
    return _client
