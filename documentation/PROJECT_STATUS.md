# RAG Campus – État d'avancement

## 1. Vue d'ensemble
- Objectif : assistant pédagogique Django basé sur le cours d'algorithmique, propulsé par un pipeline RAG (Mistral + FAISS).
- Données traitées : 5 chapitres PDF (intro → procédures) situés dans `data/raw/pdf/`.
- Périmètre couvert : ingestion → embeddings/FAISS → service RAG Python → **plateforme Django avec interface chat et rendu Markdown**.

## 2. Ingestion & preprocessing
| Étape | Outil/Fichier | Commande | Statut |
| --- | --- | --- | --- |
| Inventaire documents | `documentation/data_inventory.md`, `config/docs.yaml` | n/a | ✅ à jour (chap1–5)
| Extraction PDF → JSONL | `scripts/ingestion/pdf_extractor.py` | `python scripts/ingestion/pdf_extractor.py [--doc-id ...]` | ✅ (JSONL dans `data/processed/`)
| Nettoyage/Chunking | même script (chunk_size=500, overlap=80) | inclus | ✅

Sorties clés :
- `data/processed/chap*_*.jsonl` (43–88 chunks/doc).
- Paramètres configurables dans `config/docs.yaml` > `chunking`.

## 3. Embeddings & index vectoriel
| Étape | Fichier | Commande | Notes |
| --- | --- | --- | --- |
| Génération embeddings | `scripts/ingestion/build_index.py` | `python scripts/ingestion/build_index.py` | nécessite `MISTRAL_API_KEY`
| Storage vectoriel | `data/metadata/vector_store.faiss` | auto | Index FAISS cosine (normalisé)
| Métadonnées chunks | `data/metadata/chunks.jsonl` | auto | contient `vector_id`, textes, chapitres, pages

Dépendances : `mistralai`, `faiss-cpu`, `numpy`, `tqdm`, `python-dotenv`. Installer via `pip install -r requirements.txt`.

## 4. Service RAG (package `rag_service/`)
Structure :
- `config.py` : charge `.env`, chemins, modèles (`mistral-embed`, `mistral-large-latest`).
- `retriever.py` : charge FAISS + metadata, expose `Retriever.search()` → `RetrievedChunk`.
- `llm.py` : construit les prompts (modes `standard`, `beginner`, `exercise`, `revision`) et appelle `Mistral.chat`.
- `service.py` : classe `RAGService.answer(question, mode)` renvoie `RAGResponse {answer, citations, chunks, latency_ms}`.
- `scripts/test_rag.py` : smoke-test CLI.

Points importants :
- `.env` doit contenir `MISTRAL_API_KEY` et optionnellement `MISTRAL_CHAT_MODEL`.
- Le service gère les cas "hors contexte" (retourne un message explicite si aucun chunk pertinent).
- Les citations incluent chapitre, page, fichier source et score FAISS.

## 5. Tests et validation
- `scripts/test_rag.py` :
  ```powershell
  C:/project/RAG_For_Learning/venv/Scripts/python.exe scripts/test_rag.py
  ```
  Vérifie l'orchestration complète (embeddings requête + réponse Mistral). Exemple obtenu : réponse "hors contexte" cohérente pour "Qu'est-ce qu'une pile ?" avec citations.
- Les scripts d'ingestion affichent des logs de progression (pages/chunks) pour faciliter le suivi.

## 6. Étapes suivantes recommandées
1. **Durcir l'API Django** : ajouter endpoint JSON + authentification basique (étudiants), et gérer les conversations multiples.
2. **Tests automatisés** : couvrir `RAGClient` (mock service), vues `chatbot` et rendu Markdown avec `pytest`/`Django TestCase`.
3. **Observabilité** : journaliser latence, score moyen FAISS et mode utilisé (middleware ou logging structuré).
4. **Nettoyage frontend** : déplacer le CSS inline vers `webapp/static/`, ajouter raccourcis clavier (Ctrl+Enter) côté JS.
5. **Data augmentation** : ajouter slides/TD dans `data/raw/` + relancer ingestion/index.

## 8. Plateforme Django (`webapp/`)
- Projet `webapp/RAGCampus` + app `chatbot` isolée du reste des scripts.
- Modèles : `Conversation`, `Message`, `DocumentSource` pour persister l'historique et citer les chunks.
- Service : `chatbot/services/rag_client.py` importe désormais `rag_service.RAGService` (chemin résolu automatiquement) et sérialise les réponses (answer + sources + métadonnées).
- UI : template unique `chatbot/templates/chatbot/chat.html` avec design responsive (bulle, cartes sources, hero panel) et rendu Markdown via `chatbot.templatetags.chatbot_markdown` (lib `Markdown==3.7`).
- Formulaire : champ question + sélecteurs mode/chapitre avec aides contextuelles.
- Commandes utiles :
  ```powershell
  cd webapp
  ..\venv\Scripts\python.exe manage.py migrate
  ..\venv\Scripts\python.exe manage.py runserver
  ```
  (penser à renseigner `.env` : `DJANGO_SECRET_KEY`, `MISTRAL_API_KEY`, `FAISS_INDEX_PATH`).

## 7. Rappels utiles
- Toutes les commandes Python doivent être lancées dans le venv :
  ```powershell
  .\venv\Scripts\activate
  python -m pip install -r requirements.txt
  ```
- Variables clés : `MISTRAL_API_KEY`, `RAG_TOP_K`, `RAG_MAX_CONTEXT_TOKENS` (optionnels, voir `rag_service/config.py`).
- Structure dossier actuelle :
  - `data/raw/`, `data/processed/`, `data/metadata/`
  - `scripts/ingestion/` (extraction + index)
  - `rag_service/` (API RAG)
  - `documentation/` (inventaire + ce document)

Ce document doit être mis à jour à chaque ajout de corpus, ajustement de paramètres, ou intégration Django afin de conserver une trace claire de l'état du projet.
