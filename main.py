from fastapi import FastAPI
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os

app = FastAPI()

# -------------------------------
# LOAD EMBEDDING MODEL
# -------------------------------

model = SentenceTransformer("all-MiniLM-L6-v2")

# -------------------------------
# LOAD OR BUILD CODE DATABASE
# -------------------------------

PDF_FILE = "Dubai Building Code_English_2021 Edition_compressed.pdf"
INDEX_FILE = "vector.index"
CHUNKS_FILE = "code_chunks.pkl"

# -------------------------------
# TEST SEARCH FUNCTION
# -------------------------------
def test_search_code():
    import logging
    logging.basicConfig(level=logging.INFO)
    # # Simple test chunks and embeddings
    # test_chunks = [
    #     "Room area must be at least 9 m2.",
    #     "Door width must be at least 800 mm.",
    #     "Stair width must be at least 1000 mm.",
    #     "Windows must be operable.",
    #     "Fire exits required on each floor."
    # ]
    # logging.info(f"Test chunks: {test_chunks}")
    # # Fake embeddings: 5D vectors
    # test_embeddings = np.array([
    #     [1, 0, 0, 0, 0],
    #     [0, 1, 0, 0, 0],
    #     [0, 0, 1, 0, 0],
    #     [0, 0, 0, 1, 0],
    #     [0, 0, 0, 0, 1]
    # ], dtype=np.float32)
    # logging.info(f"Test embeddings: {test_embeddings}")
    # Build FAISS index
    test_index = faiss.IndexFlatL2(5)
    
    index = faiss.read_index(INDEX_FILE)

    with open(CHUNKS_FILE, "rb") as f:
        code_chunks = pickle.load(f)

    
    
    logging.info("FAISS index built and embeddings added.")
    # Simulate query embedding (e.g., for 'minimum door width')
    query = "minimum door width"
    # For test, use [0, 1, 0, 0, 0] as query vector
    query_vector = model.encode([query])

    D, I = index.search(np.array(query_vector), k=3)

    results = []
    print("Search results for query:", query)
    print("Query vector:", query_vector)
    print("Distances:", D)
    print("Indices:", I)
    
    for idx in I[0]:
        print(f"Result index: {idx}, code chunk: {code_chunks[idx]} \n \n")
        results.append(code_chunks[idx])


    
    return results
    # logging.info(f"Query: {query}")
    # logging.info(f"Query vector: {query_vector}")
    # D, I = index.search(query_vector, k=3)
    # logging.info(f"Distances: {D}")
    # logging.info(f"Indices: {I}")
    # results = [code_chunks[idx] for idx in I[0]]
    # logging.info(f"Search results: {results}")
    # print("Test search results:", results)


def extract_pdf_text():

    reader = PdfReader(PDF_FILE)

    text = ""

    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t

    return text


def split_text(text, chunk_size=500):

    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks


def build_vector_database():

    print("Building code database from PDF...")

    text = extract_pdf_text()

    chunks = split_text(text)

    embeddings = model.encode(chunks)

    dimension = len(embeddings[0])

    index = faiss.IndexFlatL2(dimension)

    index.add(np.array(embeddings))

    faiss.write_index(index, INDEX_FILE)

    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump(chunks, f)

    print("Code database created.")


if not os.path.exists(INDEX_FILE) or not os.path.exists(CHUNKS_FILE):
    build_vector_database()


# -------------------------------
# LOAD DATABASE
# -------------------------------

try:
    index = faiss.read_index(INDEX_FILE)

    with open(CHUNKS_FILE, "rb") as f:
        code_chunks = pickle.load(f)

except Exception as e:

    print("Database corrupted. Rebuilding...")

    build_vector_database()

    index = faiss.read_index(INDEX_FILE)

    with open(CHUNKS_FILE, "rb") as f:
        code_chunks = pickle.load(f)
# -------------------------------
# SEARCH BUILDING CODE
# -------------------------------

def search_code(query):

    query_vector = model.encode([query])

    D, I = index.search(np.array(query_vector), k=3)

    results = []

    for idx in I[0]:
        results.append(code_chunks[idx])

    return results



test_search_code()

# -------------------------------
# API ENDPOINT
# -------------------------------

@app.post("/modeldata")
def analyze_model(data: dict):

    rooms = data.get("rooms", [])
    doors = data.get("doors", [])
    stairs = data.get("stairs", [])

    analysis = []
    code = search_code("minimum room area")
    prompt = "from {code}, extract the minimum area requirement for rooms in m2 and return just the number"
    minArea = int(model.call(prompt))

    # ROOM CHECK
    for room in rooms:

        if room["area"] < minArea:


            analysis.append({
                "issue": f"Room {room['name']} area too small ({room['area']} m2)",
                "code_reference": code
            })

    # DOOR CHECK
    for door in doors:

        if door["width"] < 800:

            code = search_code("minimum door width")

            analysis.append({
                "issue": f"Door width {door['width']} mm below minimum",
                "code_reference": code
            })

    # STAIR CHECK
    for stair in stairs:

        if stair["width"] < 1000:

            code = search_code("minimum stair width")

            analysis.append({
                "issue": f"Stair width {stair['width']} mm too narrow",
                "code_reference": code
            })

    if len(analysis) == 0:

        analysis.append({"result": "Model passed basic compliance checks"})

    return {"analysis": analysis}