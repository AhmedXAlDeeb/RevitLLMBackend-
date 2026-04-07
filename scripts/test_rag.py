from src.revit_backend.loaders.pdf_loader import PDFLoader
from src.revit_backend.vectorstore.faiss_store import FAISSStore

# Load PDF
loader = PDFLoader("data/2015_International_Building_Code-238-323.pdf")
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