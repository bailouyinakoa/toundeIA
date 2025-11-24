"""LLM helper wrapping Mistral chat completions."""

from __future__ import annotations

from typing import Dict, List

from mistralai import Mistral

from .config import get_settings

MODE_INSTRUCTIONS = {
    "standard": "Réponds de manière claire et structurée en citant les passages fournis.",
    "beginner": "Explique comme à un débutant en simplifiant les notions complexes et en donnant des analogies.",
    "exercise": "Propose un ou deux exercices basés sur les passages et donne des pistes de correction.",
    "revision": "Fais un résumé à puces par chapitre en te basant sur les extraits fournis.",
}


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


def build_prompt(question: str, chunks: List[Dict], mode: str) -> List[Dict]:
    instruction = MODE_INSTRUCTIONS.get(
        mode,
        MODE_INSTRUCTIONS["standard"],
    )
    system_prompt = (
        "Tu es un assistant pédagogique spécialisé en algorithmique. "
        "Réponds uniquement à partir des extraits fournis. Si l'information n'est pas dans le contexte, "
        "dis-le clairement. Cite les passages entre crochets [n]."
    )
    context_block = format_context(chunks)
    user_prompt = (
        f"Question: {question}\n"
        f"Mode: {mode}\n"
        f"Consigne: {instruction}\n"
        f"Contexte:\n{context_block}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings["mistral_api_key"]
        if not api_key:
            raise RuntimeError("Missing MISTRAL_API_KEY in environment")
        self.client = Mistral(api_key=api_key)
        self.model = settings["chat_model"]

    def generate(
        self, question: str, chunks: List[Dict], mode: str = "standard"
    ) -> str:
        if not chunks:
            return (
                "Je n'ai trouvé aucun passage pertinent dans le cours. Reformule la question "
                "ou vérifie que le sujet fait bien partie des chapitres disponibles."
            )
        messages = build_prompt(question, chunks, mode)
        response = self.client.chat.complete(model=self.model, messages=messages)
        return response.choices[0].message.content.strip()
