from __future__ import annotations

from typing import Dict, List

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import QuestionForm
from .models import Conversation, DocumentSource, Message
from .services import RAGServiceError, get_rag_client


def _get_conversation(request: HttpRequest, mode: str, chapter: str) -> Conversation:
    conversation_id = request.session.get("conversation_id")
    conversation: Conversation | None = None
    if conversation_id:
        conversation = Conversation.objects.filter(id=conversation_id).first()

    if (
        conversation is None
        or conversation.mode != mode
        or conversation.chapter != chapter
    ):
        conversation = Conversation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            mode=mode,
            chapter=chapter,
        )
        request.session["conversation_id"] = str(conversation.id)

    return conversation


def _serialize_history(conversation: Conversation) -> List[Dict[str, str]]:
    return list(conversation.messages.order_by("created_at").values("role", "content"))


def chat_view(request: HttpRequest) -> HttpResponse:
    form = QuestionForm(request.POST or None)
    conversation: Conversation | None = None

    if request.method == "POST" and form.is_valid():
        mode = form.cleaned_data["mode"]
        chapter = form.cleaned_data["chapter"]
        question = form.cleaned_data["question"]
        conversation = _get_conversation(request, mode, chapter)
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

    context = {
        "form": form,
        "conversation": conversation,
        "chat_messages": chat_messages,
    }
    return render(request, "chatbot/chat.html", context)
