#!/usr/bin/env python
"""Utilitaire Django en ligne de commande pour les tâches d'administration."""

import os
import sys


def main():
    """Exécute les différentes commandes d'administration Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RAGCampus.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifiez qu'il est installé, "
            "accessible via PYTHONPATH et que votre environnement virtuel est activé."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
