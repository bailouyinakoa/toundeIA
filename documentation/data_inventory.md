# Course Asset Inventory

Suivi des supports du cours d'algorithmique disponibles pour le pipeline RAG.

| File | Type | Chapter | Location | Extraction | Notes |
| --- | --- | --- | --- | --- | --- |
| chap1_Intro_algorithmique_et_SDD.pdf | pdf | 1 | data/raw/pdf | done | Cours d'introduction et structures de données |
| chap2_variables_instructions_de_base_Algo_et_SDD_Octobre2022.pdf | pdf | 2 | data/raw/pdf | done | Variables et instructions de base |
| chap3_Structures_de_controle_Algo_et_SDD_Decembre2022.pdf | pdf | 3 | data/raw/pdf | done | Structures de contrôle |
| chap4_Structures_de_donnees_de_base_algo_et_SDD_Octobre2022.pdf | pdf | 4 | data/raw/pdf | done | Structures de données |
| chap5_Procedures_et_fonctions_algo_et_SDD_allege_Dec2022.pdf | pdf | 5 | data/raw/pdf | done | Procédures et fonctions |

## Répertoires en place
- `data/raw/` : sources brutes (PDF, PPTX, DOCX, images)
- `data/processed/` : texte nettoyé + chunks
- `data/metadata/` : index FAISS et manifestes
- `config/docs.yaml` : registre des documents + paramètres d'ingestion

## Prochaines étapes
1. Ajouter les autres supports (slides, TD/TP) et compléter cette table.
2. Lancer `python scripts/ingestion/pdf_extractor.py` (ou `--doc-id chap1_intro ...`) pour produire les JSONL dans `data/processed/` puis passer `extraction` à `done`.
3. Générer les embeddings/FAISS depuis `data/processed/*.jsonl` via `python scripts/ingestion/build_index.py` (clé `MISTRAL_API_KEY` requise) pour alimenter `data/metadata/`.
