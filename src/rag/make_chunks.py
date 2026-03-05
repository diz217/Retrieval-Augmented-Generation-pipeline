# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 16:18:14 2026

@author: Ding Zhang
"""

import json
import hashlib
from pathlib import Path
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

RAW_DIR = Path("../knowledge/raw")
OUT_PATH = Path("../knowledge/processed/chunks.jsonl")

def file_sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    files = sorted([p for p in RAW_DIR.rglob("*") if p.is_file() and 'log' not in p.name.lower() and p.suffix.lower() in {".txt", ".md"}])
    n = 0
    with OUT_PATH.open("w", encoding="utf-8") as f_out:
        for p in files:
            text = p.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue

            # simple type tagging
            fname = p.name.lower()
            if "rules" in fname:
                doc_type = "rules"
            else:
                doc_type = "examples"
            chunk = {"id": f"{doc_type}:{p.name}:{file_sha1(text)}","text": text,
                     "meta": {"type": doc_type,"filename": p.name,"relpath": str(p.as_posix())}}
            f_out.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            n += 1

    print(f"Wrote {n} chunks -> {OUT_PATH}")

if __name__ == "__main__":
    main()