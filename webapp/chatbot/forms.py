from django import forms
from django.contrib.auth.forms import AuthenticationForm,UserCreationForm
from .models import Conversation
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User


class QuestionForm(forms.Form):
    question = forms.CharField(
        label="Votre question",
        widget=forms.Textarea(
            attrs={"class":"form-controls" ,"color":"white" ,"rows":1, "placeholder": "Posez votre question..."}
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
