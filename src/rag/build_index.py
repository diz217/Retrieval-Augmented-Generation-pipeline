# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 11:38:41 2026

@author: Ding Zhang
"""
import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

CHUNKS_PATH = Path("../knowledge/processed/chunks.jsonl")
INDEX_DIR = Path("../index")
INDEX_DIR.mkdir(exist_ok=True)

INDEX_PATH = INDEX_DIR / "faiss.index"
META_PATH = INDEX_DIR / "meta.json"

MODEL_NAME = "BAAI/bge-base-en-v1.5"


def main():
    print("Loading chunks...")
    texts = []
    meta = []

    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            texts.append(obj["text"])
            meta.append(obj)

    print(f"Loaded {len(texts)} chunks")

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    print("Embedding chunks...")
    embeddings = model.encode(texts,convert_to_numpy=True,show_progress_bar=True)
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]

    print("Building FAISS index...")
    
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    print("Saving index...")
    faiss.write_index(index, str(INDEX_PATH))

    with META_PATH.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("Done.")
    print(f"Index saved to: {INDEX_PATH}")
    print(f"Meta saved to: {META_PATH}")


if __name__ == "__main__":
    main()