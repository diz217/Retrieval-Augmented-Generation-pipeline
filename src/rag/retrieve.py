import argparse
import json
from pathlib import Path
import os
import numpy as np
from sentence_transformers import SentenceTransformer

VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "faiss")  # "faiss" or "qdrant"
MODEL_NAME = "BAAI/bge-base-en-v1.5"
USE_BGE_PREFIX = False
DEFAULT_RULES = ("syntax_rules.txt", "rtmprep_rules.txt")

INDEX_PATH = Path("../index/faiss.index")
META_PATH = Path("../index/meta.json")

_model = None
_index = None
_meta = None

def _get_meta():
    global _meta
    if _meta is None:
        with META_PATH.open("r", encoding="utf-8") as f:
            _meta = json.load(f)
    return _meta

def _get_index():
    global _index
    if _index is None:
        import faiss
        _index = faiss.read_index(str(INDEX_PATH))
    return _index

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def search_vector_db(query_vector, k):
    if VECTOR_BACKEND == "faiss":
        index = _get_index()
        scores, idxs = index.search(query_vector, k)
        return scores[0].tolist(), idxs[0].tolist()

    elif VECTOR_BACKEND == "qdrant":
        from qdrant_client import QdrantClient

        client = QdrantClient(url="http://localhost:6333")

        hits = client.search(collection_name="execution_knowledge_base",query_vector=query_vector[0].tolist(),limit=k)
        scores = [hit.score for hit in hits]
        idxs = [hit.payload["meta_index"] for hit in hits]
        return scores, idxs

    else:
        raise ValueError(f"Unknown VECTOR_BACKEND: {VECTOR_BACKEND}")


def enforce_rules(meta, rule_filenames):
    forced = []
    wanted = set([n.lower() for n in rule_filenames])
    for obj in meta:
        fn = (obj.get("meta", {}).get("filename") or "").lower()
        if fn in wanted:
            forced.append(obj)
    return forced

def retrieve(q, k=8, force_rules=True, rules=DEFAULT_RULES):
    meta = _get_meta()

    model = _get_model()
    if USE_BGE_PREFIX:
        q = "query: " + q

    q_vec = model.encode([q], convert_to_numpy=True)
    import faiss
    faiss.normalize_L2(q_vec)
    scores, idxs = search_vector_db(q_vec, k)

    retrieved = []
    for score, i in zip(scores, idxs):
        if i < 0 or i >= len(meta):
            continue
        retrieved.append(meta[i])

    forced = []
    if force_rules:
        forced_objs = enforce_rules(meta, rules)
        seen_ids = set(obj.get("id") for obj in retrieved)

        for obj in forced_objs:
            if obj.get("id") not in seen_ids:
                forced.append(obj)

    merged = []
    merged.extend(retrieved)
    if force_rules:
        merged.extend(forced)

    return merged

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", type=str, help="Search query string")
    ap.add_argument("--k", type=int, default=8, help="TopK retrieved chunks from FAISS")
    ap.add_argument("--force-rules",action="store_true",help="Force include syntax_rules.txt + rtmprep_rules.txt (Scheme A)")
    ap.add_argument("--rules",type=str,default="syntax_rules.txt,rtmprep_rules.txt",
                    help="Comma-separated rule filenames to force include")
    args = ap.parse_args()

    merged = retrieve(args.query, args.k, args.force_rules)

    out_path = Path("../knowledge/processed/last_retrieval.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
