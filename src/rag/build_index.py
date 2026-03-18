import json
from pathlib import Path
import os
from sentence_transformers import SentenceTransformer

VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "faiss")  # "faiss" or "qdrant"
MODE = os.getenv("INDEX_MODE", "rebuild")  # "rebuild" or "upsert"

MODEL_NAME = "BAAI/bge-base-en-v1.5"

CHUNKS_PATH = Path("../knowledge/processed/chunks.jsonl")
INDEX_DIR = Path("../index")
INDEX_DIR.mkdir(exist_ok=True)

INDEX_PATH = INDEX_DIR / "faiss.index"
META_PATH = INDEX_DIR / "meta.json"

def load_chunks():
    texts = []
    meta = []

    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            obj = json.loads(line)
            obj["meta_index"] = i

            texts.append(obj["text"])
            meta.append(obj)

    return texts, meta

def build_faiss(embeddings):
    import faiss

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))

def upsert_qdrant(texts, meta, embeddings):
    from qdrant_client import QdrantClient

    client = QdrantClient(url="http://localhost:6333")

    points = []
    for obj, text, vector in zip(meta, texts, embeddings):
        points.append({"id": obj["id"],"vector": vector.tolist(),"payload": {
                "text": text,
                "meta": obj.get("meta", {}),
                "meta_index": obj["meta_index"],
                "active": True}})

    client.upsert(collection_name="execution_knowledge_base",points=points)

def main():
    print(f"MODE = {MODE}, BACKEND = {VECTOR_BACKEND}")
    texts, meta = load_chunks()
    print(f"Loaded {len(texts)} chunks")

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    print("Embedding...")
    embeddings = model.encode(texts,convert_to_numpy=True,show_progress_bar=True)

    import faiss
    faiss.normalize_L2(embeddings)

    if VECTOR_BACKEND == "faiss":
        print("Building FAISS index...")
        build_faiss(embeddings)

        with META_PATH.open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        print("FAISS build done.")

    elif VECTOR_BACKEND == "qdrant":
        print("Upserting into Qdrant...")
        upsert_qdrant(texts, meta, embeddings)
        print("Qdrant upsert done.")

    else:
        raise ValueError(f"Unknown VECTOR_BACKEND: {VECTOR_BACKEND}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
