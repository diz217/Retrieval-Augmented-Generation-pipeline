# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 00:55:22 2026

@author: Ding Zhang
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional,Literal

Mode = Literal["generate","repair"]
@dataclass(frozen=True)
class PromptPaths:
    system_generate_path: Path = Path("llm/prompts/system_generate.txt")
    system_repair_path: Path = Path("llm/prompts/system_repair.txt")


@dataclass(frozen=True)
class PromptBuildOptions:
    query_header: str = "### QUERY"
    context_header: str = "### CONTEXT"
    require_nonempty_context: bool = True
    normalize_newlines: bool = True


def _normalize_newlines(text: str) -> str:
    # Make prompt stable across OS (Windows vs Linux) and editors.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def load_system_prompt(paths: PromptPaths, opts: PromptBuildOptions,mode:Mode) -> str:
    if mode=="generate":
        p = paths.system_generate_path
    elif mode=="repair":
        p = paths.system_repair_path
    else:
        raise ValueError(f"Unknown mode in prompting: {mode}")
    
    if not p.exists():
        raise FileNotFoundError(f"Missing system prompt {mode}: {p}")

    system_text = p.read_text(encoding="utf-8")
    if opts.normalize_newlines:
        system_text = _normalize_newlines(system_text)
    # Ensure it ends with one newline (LLM formatting stability)
    system_text = system_text.strip() + "\n"
    return system_text


def build_user_prompt(query: str, context_text: str, opts: Optional[PromptBuildOptions] = None) -> str:
    """
    Build the user prompt from:
      - query: the natural language request / spec
      - context_text: retrieved context text (ideally includes RULES + EXAMPLES sections)
    """
    opts = opts or PromptBuildOptions()

    if opts.normalize_newlines:
        query = _normalize_newlines(query)
        context_text = _normalize_newlines(context_text)

    query = query.strip()
    context_text = context_text.strip()

    if not query:
        raise ValueError("QUERY is empty. Did you write request.txt?")

    if opts.require_nonempty_context and not context_text:
        raise ValueError("CONTEXT is empty. Did retrieve/render_context run?")

    user_prompt = (
        f"{opts.query_header}\n"
        f"{query}\n\n"
        f"{opts.context_header}\n"
        f"{context_text}\n"
    )
    return user_prompt


def build_prompts(query: str, context_text: str, mode: Mode = 'generate', paths: Optional[PromptPaths] = None, opts: Optional[PromptBuildOptions] = None) -> Tuple[str, str]:
    paths = paths or PromptPaths()
    opts = opts or PromptBuildOptions()

    system_prompt = load_system_prompt(paths, opts, mode)
    user_prompt = build_user_prompt(query, context_text, opts)
    return system_prompt, user_prompt