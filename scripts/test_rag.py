from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_service import RAGService

question = "Qu'est-ce qu'une pile ?"
mode = "standard"

service = RAGService()
response = service.answer(question, mode=mode)

print("Question:", question)
print("Mode:", mode)
print("Réponse:\n", response.answer)
print("Citations:")
for citation in response.citations:
    print(" -", citation)
print("Chunks retournés:", len(response.chunks))
print("Latence (ms):", round(response.latency_ms, 2))
