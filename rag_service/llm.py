"""LLM helper wrapping Mistral chat completions."""

from __future__ import annotations

from typing import Dict, List, Optional

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
        api_key = settings["mistral_api_key"]
        if not api_key:
            raise RuntimeError("Missing MISTRAL_API_KEY in environment")
        self.client = Mistral(api_key=api_key)
        self.model = settings["chat_model"]

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
        try:
            response = self.client.chat.complete(model=self.model, messages=messages)
        except SDKError as err:
            status = getattr(err, "status_code", None)
            message = getattr(err, "message", "")
            if status == 429 or "capacity" in message.lower():
                raise LLMCapacityError(
                    "Le modèle Mistral est momentanément saturé. Patiente quelques secondes puis réessaie."
                ) from err
            raise RuntimeError("Erreur lors de l'appel au modèle Mistral") from err
        return response.choices[0].message.content.strip()
