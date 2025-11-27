from __future__ import annotations

from typing import Dict, List
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.views.decorators.http import require_POST
from .forms import *
from .models import Conversation, DocumentSource, Message
from .services import RAGServiceError, get_rag_client


def _get_conversation(
    request: HttpRequest, mode: str, chapter: str, title: str
) -> Conversation:
    conversation_id = request.session.get("conversation_id")
    conversation: Conversation | None = None
    if conversation_id:
        conversation = Conversation.objects.filter(id=conversation_id).first()

    normalized_title = _shorten_title(title)

    if (
        conversation is None
        or conversation.mode != mode
        or conversation.chapter != chapter
    ):
        conversation = Conversation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            mode=mode,
            me=request.user if request.user.is_authenticated else None,
            title=normalized_title,
            chapter=chapter,
        )
        request.session["conversation_id"] = str(conversation.id)

    return conversation


def _serialize_history(conversation: Conversation) -> List[Dict[str, str]]:
    return list(conversation.messages.order_by("created_at").values("role", "content"))


def _shorten_title(raw: str, max_len: int = 80) -> str:
    text = (raw or "").strip()
    if not text:
        return "Nouvelle question"
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 3].rstrip() + "..."


def _get_user_conversations(user):
    if not user.is_authenticated:
        return []
    latest_messages = Prefetch(
        "messages",
        queryset=Message.objects.order_by("-created_at"),
        to_attr="recent_messages",
    )
    return (
        Conversation.objects.filter(user=user)
        .prefetch_related(latest_messages)
        .only("id", "title", "mode", "chapter", "updated_at")
    )


def chat_view(request: HttpRequest) -> HttpResponse:
    form = QuestionForm(request.POST or None)
    conversation: Conversation | None = None
    if request.method == "POST" and form.is_valid():
        mode = form.cleaned_data["mode"]
        chapter = form.cleaned_data["chapter"]
        question = form.cleaned_data["question"]
        conversation = _get_conversation(request, mode, chapter, title=question)
        history_payload = _serialize_history(conversation)

        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=question,
        )

        client = get_rag_client()
        try:
            result = client.answer(
                question=question, mode=mode, history=history_payload
            )
        except RAGServiceError as exc:
            user_message.delete()
            messages.error(request, str(exc))
            return redirect(reverse("chatbot:chat"))

        answer = result.get("answer", "")
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=answer,
            metadata=result.get("metadata", {}),
        )

        for source in result.get("sources", []):
            DocumentSource.objects.create(
                message=assistant_message,
                title=source.get("title", "Document"),
                path=source.get("path", ""),
                chunk_id=source.get("chunk_id", ""),
                score=source.get("score", 0.0),
                extra=source,
            )

        form = QuestionForm(initial={"mode": mode, "chapter": chapter})
        messages.success(request, "Réponse générée avec succès.")

    if conversation is None:
        convo_id = request.session.get("conversation_id")
        if convo_id:
            conversation = Conversation.objects.filter(id=convo_id).first()

    chat_messages = (
        conversation.messages.select_related(None).prefetch_related("sources")
        if conversation
        else []
    )
    conv = Conversation.objects.all()
    mes_conv = _get_user_conversations(request.user)
    context = {
        "form": form,
        "conversation": conversation,
        "mes_conv": mes_conv,
        "chat_messages": chat_messages,
        "conv": conv,
    }
    return render(request, "chatbot/index.html", context)


def mes(request, pk):
    discussion = get_object_or_404(Conversation, pk=pk)
    request.session["conversation_id"] = str(discussion.id)
    request.session.modified = True
    initial = {"mode": discussion.mode, "chapter": discussion.chapter}
    form = QuestionForm(initial=initial)
    message = Message.objects.filter(conversation=discussion)
    mes_conv = _get_user_conversations(request.user)
    context = {
        "conversation": discussion,
        "mes_conv": mes_conv,
        "chat_messages": message,
        "form": form,
    }
    return render(request, "chatbot/index.html", context)


@require_POST
def new_conversation(request: HttpRequest) -> HttpResponse:
    """Clear the active conversation so the next prompt starts fresh."""
    request.session.pop("conversation_id", None)
    request.session.modified = True
    messages.info(request, "Nouvelle conversation prête.")
    return redirect(reverse("chatbot:chat"))
