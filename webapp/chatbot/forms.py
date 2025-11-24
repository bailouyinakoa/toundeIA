from django import forms

from .models import Conversation


class QuestionForm(forms.Form):
    question = forms.CharField(
        label="Votre question",
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Posez votre question..."}
        ),
        max_length=2000,
    )
    mode = forms.ChoiceField(
        label="Mode",
        choices=Conversation.Mode.choices,
        initial=Conversation.Mode.STANDARD,
    )
    chapter = forms.CharField(
        label="Chapitre (optionnel)",
        required=False,
        max_length=128,
    )

    def clean_question(self):
        data = self.cleaned_data["question"].strip()
        if not data:
            raise forms.ValidationError("La question ne peut pas être vide.")
        return data
