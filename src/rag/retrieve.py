# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 11:38:41 2026

@author: Ding Zhang
"""

# rag/retrieve.py
# Scheme A: FAISS topK retrieval + forced inclusion of rules chunks
# - meta.json is a list of chunk objects, each with at least:
#     obj["id"], obj["text"], obj["meta"]["filename"], obj["meta"]["type"]
#

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

import os



INDEX_PATH = Path("index/faiss.index")
META_PATH = Path("index/meta.json")

MODEL_NAME = "BAAI/bge-base-en-v1.5"
USE_BGE_PREFIX = False
DEFAULT_RULES = ("syntax_rules.txt","rtmprep_rules.txt")

_model = None
_index = None
_meta = None
def _get_meta():
    global _meta
    if _meta is None:
        with META_PATH.open("r", encoding="utf-8") as f:
            _meta = json.load(f)
        if not isinstance(_meta, list):
            raise ValueError("meta.json must be a list of chunk objects.")
    return _meta

def _get_index():
    global _index
    if _index is None:
        _index = faiss.read_index(str(INDEX_PATH))
    return _index

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def enforce_rules(meta, rule_filenames=("syntax_rules.txt", "rtmprep_rules.txt")):
    forced = []
    wanted = set([n.lower() for n in rule_filenames])
    for obj in meta:
        fn = (obj.get("meta", {}).get("filename") or "").lower()
        if fn in wanted:
            forced.append(obj)
    return forced


def pretty_obj(obj, score=None):
    cid = obj.get("id", "<no-id>")
    m = obj.get("meta", {})
    fn = m.get("filename", "<no-filename>")
    typ = m.get("type", "<no-type>")
    header = f"[{typ}] {fn}  id={cid}"
    if score is not None:
        header += f"  score={score:.4f}"

    # Print a compact preview (first ~20 lines or 800 chars)
    text = (obj.get("text") or "").strip()
    if len(text) > 800:
        text = text[:800] + "\n... (truncated)"
    return header + "\n" + text

def retrieve(q, k = 8, force_rules=True, rules = DEFAULT_RULES):
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing FAISS index: {INDEX_PATH}")
    if not META_PATH.exists():
        raise FileNotFoundError(f"Missing meta.json: {META_PATH}")
    meta = _get_meta()
    index = _get_index()
    
    # ---- Encode query (must match build_index configuration) ----
    model = _get_model()
    if USE_BGE_PREFIX:
        # BGE common pattern; turn on only if you also do consistent prefixing.
        q = "query: " + q

    q_vec = model.encode([q], convert_to_numpy=True)
    faiss.normalize_L2(q_vec)

    # ---- Search ----
    scores, idxs = index.search(q_vec, k)
    scores = scores[0].tolist()
    idxs = idxs[0].tolist()

    retrieved = []
    for score, i in zip(scores, idxs):
        if i < 0 or i >= len(meta):
            continue
        obj = meta[i]
        retrieved.append((i, score, obj))

    # ---- Scheme A: force include rules ----
    forced = []
    if force_rules:
        forced_objs = enforce_rules(meta, rule_filenames=rules)

        # De-dupe by id (keep retrieved score if present)
        seen_ids = set()
        for _, _, obj in retrieved:
            seen_ids.add(obj.get("id"))
        for obj in forced_objs:
            if obj.get("id") not in seen_ids:
                forced.append(obj)

    # ---- Print output (separate groups so you can judge retrieval quality) ----
    print("\n=== Retrieved (FAISS topK) ===")
    '''
    for i, score, obj in retrieved:
        print(pretty_obj(obj, score=score))
        print("-" * 80)
    '''
    if force_rules:
        print("\n=== Forced rules (Scheme A) ===")
        if not forced:
            print("(No forced rules found. Check filenames in --rules.)")
        '''
        for obj in forced:
            print(pretty_obj(obj, score=None))
            print("-" * 80)
        '''
    merged = []
    merged.extend([obj for _, _, obj in retrieved])
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

    merged = retrieve(q = args.query.strip(),k = args.k,force_rules = args.force_rules,rules = args.rules)
    out_path = Path("../knowledge/processed/last_retrieval.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"\nSaved merged retrieval context -> {out_path}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    INDEX_PATH = Path("../index/faiss.index")
    META_PATH = Path("../index/meta.json")
    main()