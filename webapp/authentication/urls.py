from django.urls import path
from django.contrib.auth.views import LoginView
from . import views

app_name = "authentication"

urlpatterns = [
    path("login/", views.Login.as_view(), name="login"),
    path("inscription/", views.inscription, name="inscription"),
    path("logout/", views.logout_view, name="logout"),
]
