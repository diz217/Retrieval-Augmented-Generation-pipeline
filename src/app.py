# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 22:55:16 2026

@author: Ding Zhang
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from rag.retrieve import retrieve
from llm.prompts import build_prompts
from llm.client import GLOBAL_LLM_CLIENT
from llm.validator import validate_candidate
from llm.repair import build_repair_user_prompt
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Paths / Runs
RUNS_DIR = Path("runs")
RUNS_DIR.mkdir(exist_ok=True)

DEFAULT_K = 8
DEFAULT_FORCE_RULES = True

# You can later move these into a config file.
RULE_FILENAMES = ("syntax_rules.txt", "rtmprep_rules.txt")


@dataclass
class RunArtifacts:
    run_dir: Path
    request_path: Path
    retrieved_path: Path
    context_path: Path
    prompt_path: Path
    candidate_path: Path
    validation_path: Path
    final_config_path: Path


def new_run() -> RunArtifacts:
    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    return RunArtifacts(
        run_dir=run_dir,
        request_path=run_dir / "request.txt",
        retrieved_path=run_dir / "retrieved.json",
        context_path=run_dir / "context.txt",
        prompt_path=run_dir/"prompt.txt",
        candidate_path=run_dir / "candidate_0.txt",
        validation_path=run_dir / "validation_0.json",
        final_config_path=run_dir / "final_config.txt")

# Retrieval (import your module)
def retrieve_context(user_request: str, k: int = DEFAULT_K, force_rules: bool = DEFAULT_FORCE_RULES, rules: tuple = RULE_FILENAMES) -> List[Dict[str, Any]]:
    """
    Returns a list of chunk objects: [{"id":..., "text":..., "meta": {...}}, ...]
    """
    chunks = retrieve(user_request, k=k, force_rules=force_rules,rules=rules)
    if not isinstance(chunks, list):
        raise TypeError("retrieve() must return a list of chunk dicts.")
    return chunks

# Context rendering (rules first, examples later)
def render_context(chunks: List[Dict[str, Any]]) -> str:
    rules = []
    examples = []
    others = []

    for obj in chunks:
        meta = obj.get("meta", {}) or {}
        typ = meta.get("type", "")
        fn = meta.get("filename", "")

        block = []
        block.append(f"=== {typ.upper() or 'UNK'} | {fn} | id={obj.get('id','<no-id>')} ===")
        block.append((obj.get("text") or "").rstrip())
        block_text = "\n".join(block).strip() + "\n"

        if typ == "rules":
            rules.append(block_text)
        elif typ == "examples":
            examples.append(block_text)
        else:
            others.append(block_text) 
    # Rules at the top: they are hard constraints
    # Examples next: they show style/family patterns
    return "\n".join(rules + others + examples).strip() + "\n"

def llm_repair_stub(user_request: str, context: str, validation_report: Dict[str, Any], candidate: str) -> str:
    """
    Placeholder for repair loop.
    """
    return candidate  # no-op for now

# Orchestration
def run_once(user_request: str, k: int = DEFAULT_K, force_rules: bool = True, max_repairs: int = 1) -> Path:
    art = new_run()
    # 0) Save request
    art.request_path.write_text(user_request.strip() + "\n", encoding="utf-8")

    # 1) Retrieval
    chunks = retrieve_context(user_request, k=k, force_rules=force_rules)
    art.retrieved_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) Build context
    context = render_context(chunks)
    art.context_path.write_text(context, encoding="utf-8")

    # 3) Build prompts
    system_prompt, user_prompt = build_prompts(user_request, context)
    system_repair,_ = build_prompts(user_request, context,mode = 'repair')
    art.prompt_path.write_text(user_prompt, encoding="utf-8")
    
    # 4) Generate candidate
    candidate = GLOBAL_LLM_CLIENT.generate_text(system_prompt, user_prompt)
    art.candidate_path.write_text(candidate, encoding="utf-8")

    # 5) Validate 
    report = validate_candidate(candidate)
    art.validation_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    
    # 6) Repair loop
    ok = report.ok    
    repairs = 0
    while (not ok) and repairs < max_repairs:
        repairs += 1
        repair_prompt = build_repair_user_prompt(user_request, context, candidate,report.to_dict())
        (art.run_dir/f"prompt_repair_{repairs}.txt").write_text(repair_prompt, encoding='utf-8')
        
        candidate = GLOBAL_LLM_CLIENT.generate_text(system_repair, repair_prompt)
        (art.run_dir/f"candiate_{repairs}.txt").write_text(candidate, encoding='utf-8')
        
        report = validate_candidate(candidate)
        art.validation_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    if not ok:
        raise RuntimeError(f"Validation failed after {repairs} repair attempts. See: {art.run_dir}")

    # 5) Finalize
    art.final_config_path.write_text(candidate, encoding="utf-8")
    return art.run_dir


if __name__ == "__main__":
    req = input("Describe the config you want:\n> ").strip()
    out_dir = run_once(req, k=DEFAULT_K, force_rules=True, max_repairs=1)
    print(f"\nOK. Artifacts saved to: {out_dir}")