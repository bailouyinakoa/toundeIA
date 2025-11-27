"""LLM helper wrapping Mistral chat completions with optional Groq fallback."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency guard during upgrade
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None  # type: ignore
from mistralai import Mistral
from mistralai.models.sdkerror import SDKError

from .config import get_settings

DEFAULT_MODE = "standard"

MODE_INSTRUCTIONS = {
    "standard": "Réponds de manière claire et structurée en citant les passages fournis.",
    "beginner": (
        "Explique comme à un débutant en vulgarisant chaque concept, avec un vocabulaire simple et des exemples concrets."
    ),
    "exercise": (
        "Propose un ou deux exercices progressifs basés sur les extraits, puis donne des pistes de correction succinctes."
    ),
    "revision": (
        "Rédige un résumé synthétique sous forme de puces par thème/champion en te basant uniquement sur les extraits."
    ),
    "review": (
        "Présente une fiche de révision structurée (points clés, rappels importants) uniquement à partir des extraits fournis."
    ),
}


def _normalize_mode(mode: str) -> str:
    normalized = (mode or DEFAULT_MODE).strip().lower()
    if normalized not in MODE_INSTRUCTIONS:
        # Alias manuel : "review" était utilisé côté Django mais peut être confondu.
        if normalized == "revision":
            return "revision"
        if normalized == "revise":
            return "revision"
        return DEFAULT_MODE
    return normalized


def format_context(chunks: List[Dict]) -> str:
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        citation = f"Chapitre {chunk.get('chapter')}"
        if chunk.get("page"):
            citation += f", page {chunk['page']}"
        source = chunk.get("source_filename")
        if source:
            citation += f" ({source})"
        lines.append(f"[{idx}] {citation}\n{chunk.get('text', '')}")
    return "\n\n".join(lines)


def format_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "Pas d'historique fourni."
    snippets = []
    for item in history:
        role = item.get("role", "user")
        content = item.get("content", "").strip()
        if not content:
            continue
        label = (
            "Utilisateur"
            if role == "user"
            else ("Assistant" if role == "assistant" else role)
        )
        snippets.append(f"{label}: {content}")
    return "\n".join(snippets[-6:]) or "Historique vide après nettoyage."


def build_prompt(
    question: str,
    chunks: List[Dict],
    mode: str,
    chapter: Optional[str | int] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict]:
    normalized_mode = _normalize_mode(mode)
    instruction = MODE_INSTRUCTIONS.get(
        normalized_mode, MODE_INSTRUCTIONS[DEFAULT_MODE]
    )
    system_prompt = (
        "Tu es un assistant pédagogique spécialisé en algorithmique. "
        "Réponds uniquement à partir des extraits fournis. Si l'information n'est pas dans le contexte, "
        "dis-le clairement. Cite les passages entre crochets [n]."
    )
    context_block = format_context(chunks)
    chapter_line = f"Chapitre ciblé: {chapter}\n" if chapter else ""
    history_block = format_history(history or [])
    user_prompt = (
        f"Question: {question}\n"
        f"Mode: {normalized_mode}\n"
        f"{chapter_line}"
        f"Consigne: {instruction}\n"
        f"Historique récent:\n{history_block}\n\n"
        f"Contexte:\n{context_block}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


class LLMCapacityError(RuntimeError):
    """Raised when the upstream LLM refuses the request due to capacity limits."""


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.mistral_client: Optional[Mistral] = None
        self.groq_client: Optional[Groq] = None
        mistral_key = settings["mistral_api_key"]
        if mistral_key:
            self.mistral_client = Mistral(api_key=mistral_key)
        groq_key = settings.get("groq_api_key")
        if groq_key:
            if Groq is None:  # pragma: no cover
                raise RuntimeError(
                    "Le SDK Groq n'est pas installé. Exécute `pip install groq`."
                )
            self.groq_client = Groq(api_key=groq_key)
        if not self.mistral_client and not self.groq_client:
            raise RuntimeError("Missing LLM provider configuration (Mistral or Groq)")
        self.mistral_model = settings["chat_model"]
        self.groq_model = settings.get("groq_chat_model")
        self.logger = logging.getLogger(__name__)

    def generate(
        self,
        question: str,
        chunks: List[Dict],
        mode: str = "standard",
        chapter: Optional[str | int] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not chunks:
            return (
                "Je n'ai trouvé aucun passage pertinent dans le cours. Reformule la question "
                "ou vérifie que le sujet fait bien partie des chapitres disponibles."
            )
        messages = build_prompt(
            question,
            chunks,
            mode,
            chapter=chapter,
            history=history,
        )
        mistral_error: Optional[Exception] = None
        if self.mistral_client:
            try:
                return self._call_mistral(messages)
            except LLMCapacityError as err:
                mistral_error = err
                if self.groq_client:
                    self.logger.warning(
                        "Mistral capacity issue detected. Falling back to Groq."
                    )
                else:
                    raise
            except RuntimeError:
                # Propagate other unexpected errors without fallback for now.
                raise
        if self.groq_client:
            try:
                return self._call_groq(messages)
            except LLMCapacityError:
                # If Mistral already failed, prefer Groq message; otherwise bubble up.
                raise
        if mistral_error:
            raise mistral_error
        raise RuntimeError("Aucun modèle LLM n'est disponible pour traiter la requête.")

    def _call_mistral(self, messages: List[Dict]) -> str:
        if not self.mistral_client:
            raise RuntimeError("Mistral client is not configured")
        try:
            response = self.mistral_client.chat.complete(
                model=self.mistral_model, messages=messages
            )
        except SDKError as err:
            status = getattr(err, "status_code", None)
            message = getattr(err, "message", "")
            if status == 429 or "capacity" in message.lower():
                raise LLMCapacityError(
                    "Le modèle Mistral est momentanément saturé. Patiente quelques secondes puis réessaie."
                ) from err
            raise RuntimeError("Erreur lors de l'appel au modèle Mistral") from err
        return response.choices[0].message.content.strip()

    def _call_groq(self, messages: List[Dict]) -> str:
        if not self.groq_client:
            raise RuntimeError("Groq client is not configured")
        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
            )
        except Exception as err:
            status = getattr(err, "status_code", None) or getattr(err, "status", None)
            message = getattr(err, "message", str(err))
            if isinstance(message, str) and "capacity" in message.lower():
                raise LLMCapacityError(
                    "Le modèle Groq est momentanément saturé. Patiente quelques secondes puis réessaie."
                ) from err
            if status == 429:
                raise LLMCapacityError(
                    "Le modèle Groq est momentanément saturé. Patiente quelques secondes puis réessaie."
                ) from err
            raise RuntimeError("Erreur lors de l'appel au modèle Groq") from err
        return response.choices[0].message.content.strip()
