from django.contrib import admin
from .models import *
# Déclarez ici les modèles du chatbot pour l'interface d'administration.
admin.site.register([Conversation,Message,DocumentSource])