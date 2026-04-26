from pathlib import Path
import sys

# Ensure repository root is available for `src` imports when executing this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.revit_backend.loaders.pdf_loader import PDFLoader
from src.revit_backend.vectorstore.faiss_store import FAISSStore

# Load PDF
pdf_path = PROJECT_ROOT / "data" / "all-pages.pdf"
if not pdf_path.exists():
    raise FileNotFoundError(f"PDF not found: {pdf_path}")

loader = PDFLoader(str(pdf_path))
chunks = loader.load_and_split()

print(f"Loaded {len(chunks)} chunks")

# Create vector DB
store = FAISSStore()
vector_db = store.create_store(chunks)

# Test search
query = "minimum bedroom area"

results = vector_db.similarity_search(query, k=3)

for i, doc in enumerate(results):
    print(f"\nResult {i+1}:")
    print(doc.page_content[:300])