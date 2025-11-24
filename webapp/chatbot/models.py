import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    class Mode(models.TextChoices):
        STANDARD = "standard", "Réponse standard"
        BEGINNER = "beginner", "Explication débutant"
        EXERCISE = "exercise", "Exercices générés"
        REVIEW = "review", "Révision par chapitre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    mode = models.CharField(
        max_length=32,
        choices=Mode.choices,
        default=Mode.STANDARD,
    )
    chapter = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Conversation {self.id} ({self.mode})"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Utilisateur"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "Système"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.role} message in {self.conversation_id}"


class DocumentSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    title = models.CharField(max_length=255)
    path = models.CharField(max_length=512)
    chunk_id = models.CharField(max_length=128, blank=True)
    score = models.FloatField(default=0.0)
    extra = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ["-score"]
        indexes = [models.Index(fields=["message", "score"])]

    def __str__(self) -> str:
        return f"Source {self.title} ({self.score:.2f})"
