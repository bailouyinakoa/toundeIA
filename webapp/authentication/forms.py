from django.contrib.auth.forms import *
from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.models import User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "nom.prenom@exemple.com"}
        ),
    )
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Mot de passe"}
        ),
    )

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            self.user_cache = get_user_model().objects.filter(email=email).first()
            if self.user_cache is None:
                raise forms.ValidationError("Utilisateur non trouvé")
            elif not self.user_cache.check_password(password):
                raise forms.ValidationError("Mot de passe incorrect")
        return self.cleaned_data


class UserForm(UserCreationForm):
    first_name = forms.CharField(
        label="",
        widget=forms.TextInput(
            attrs={"class": "form-control m-3", "placeholder": "Nom"}
        ),
    )
    last_name = forms.CharField(
        label="",
        widget=forms.TextInput(
            attrs={"class": "form-control m-3", "placeholder": "Prenom"}
        ),
    )
    email = forms.CharField(
        label="",
        widget=forms.EmailInput(
            attrs={"class": "form-control m-3", "placeholder": "Email"}
        ),
    )
    password1 = forms.CharField(
        label="",
        widget=forms.PasswordInput(
            attrs={"class": "form-control m-3", "placeholder": "mot de passe"}
        ),
    )
    password2 = forms.CharField(
        label="",
        widget=forms.PasswordInput(
            attrs={"class": "form-control m-3", "placeholder": "confirmer mot de pass"}
        ),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2")
