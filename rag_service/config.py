"""Configuration helpers for the RAG service."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
METADATA_DIR = ROOT_DIR / "data" / "metadata"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CONFIG_FILE = ROOT_DIR / "config" / "docs.yaml"


load_dotenv(ENV_PATH)


@lru_cache()
def get_settings() -> Dict[str, Any]:
    return {
        "mistral_api_key": os.getenv("MISTRAL_API_KEY"),
        "groq_api_key": os.getenv("GROQ_API_KEY"),
        "embedding_model": "mistral-embed",
        "chat_model": os.getenv("MISTRAL_CHAT_MODEL", "mistral-large-latest"),
        "groq_chat_model": os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile"),
        "vector_store_path": METADATA_DIR / "vector_store.faiss",
        "metadata_path": METADATA_DIR / "chunks.jsonl",
        "top_k": int(os.getenv("RAG_TOP_K", "5")),
        "max_context_tokens": int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "2000")),
    }
