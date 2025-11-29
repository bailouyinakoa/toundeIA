"""
Configuration WSGI du projet RAGCampus.

Expose la variable ``application`` utilisée par les serveurs WSGI classiques.
Guide de déploiement détaillé : https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.RAGCampus.settings')

application = get_wsgi_application()
