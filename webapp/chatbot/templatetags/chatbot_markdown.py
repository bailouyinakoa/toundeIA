"""Filtres utilitaires pour rendre le texte Markdown des réponses."""

from django import template
from django.utils.safestring import mark_safe

import markdown as md

register = template.Library()


@register.filter(name="render_markdown")
def render_markdown(value: str | None) -> str:
    """Convertit un extrait Markdown en HTML sécurisé pour les réponses."""
    if not value:
        return ""
    html = md.markdown(
        value,
        extensions=["extra", "sane_lists", "toc"],
        output_format="html5",
    )
    return mark_safe(html)
