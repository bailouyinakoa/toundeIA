# Toundé AI – Chatbot pédagogique (DeepLearn)

Toundé AI est une plateforme d'apprentissage basée sur un pipeline Retrieval-Augmented Generation (FAISS + Mistral) et une interface Django. Les documents de cours d'algorithmique sont ingérés, chunkés, vectorisés puis interrogés en mode conversationnel (débutant, exercices, révision).

## Architecture
- **scripts/ingestion/** : extraction PDF → JSONL, chunking et construction de l'index FAISS.
- **data/** : `raw/` (sources), `processed/` (chunks), `metadata/` (index, infos).
- **rag_service/** : service Python autonome (retriever, LLM, orchestration).
- **webapp/** : projet Django (`RAGCampus`) + app `chatbot` (modèles, vues, templates, services).
- **documentation/** : inventaire des données, état du projet (`PROJECT_STATUS.md`).

## Prérequis
- Python 3.13 (venv recommandé).
- Clé API Mistral (`MISTRAL_API_KEY`).
- (Optionnel) Clé API Groq (`GROQ_API_KEY`) pour activer un secours si Mistral est saturé.
- FAISS CPU (`faiss-cpu`) déjà listé dans `requirements.txt`.

## Installation
```powershell
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
```

Créez votre fichier `.env` à partir de `.env.example` et complétez les valeurs sensibles.

## Pipeline données (ingestion)
1. Placer les PDF dans `data/raw/pdf/`.
2. Exécuter l'extracteur :
   ```powershell
   python scripts/ingestion/pdf_extractor.py
   ```
3. Construire l'index vectoriel :
   ```powershell
   python scripts/ingestion/build_index.py
   ```
   L'index FAISS est écrit dans `data/metadata/vector_store.faiss`.

## Service RAG autonome
Test rapide :
```powershell
python scripts/test_rag.py --question "Qu'est-ce qu'un algorithme ?"
```
 Retourne la réponse Mistral (avec secours Groq si activé) + citations.

## Application Django
```powershell
cd webapp
../venv/Scripts/python.exe manage.py migrate
../venv/Scripts/python.exe manage.py runserver
```
Fonctionnalités :
- Interface chat responsive (hero panel, bulles, cartes sources).
- Sélecteur de mode (standard, débutant, exercices, révision) et filtrage par chapitre.
- Persistance des conversations (`Conversation`, `Message`, `DocumentSource`).
- Rendu Markdown pour les réponses (lib `Markdown`).

## Tests
Actuellement :
```powershell
../venv/Scripts/python.exe manage.py check
```
À venir : tests unitaires pour `rag_service`, `chatbot` et ingestion.

## Publication GitHub
1. `git init`
2. `git add .`
3. `git commit -m "Initial commit"`
4. Créez un repo GitHub puis :
   ```powershell
   git remote add origin https://github.com/<user>/RAG_For_Learning.git
   git push -u origin main
   ```

Pour l'état détaillé, consultez `documentation/PROJECT_STATUS.md`.
