from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("dicussion/<uuid:pk>/", views.mes, name="message"),
    path("conversation/nouvelle/", views.new_conversation, name="new_conversation"),
]
