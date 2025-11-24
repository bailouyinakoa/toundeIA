"""
Configuration ASGI du projet RAGCampus.

Expose la variable ``application`` utilisée par Channels/ASGI pour traiter les requêtes.
Consultez la documentation Django pour les conseils de déploiement ASGI :
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RAGCampus.settings")

application = get_asgi_application()
