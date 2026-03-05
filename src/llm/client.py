# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 01:24:36 2026

@author: Ding Zhang
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from openai import OpenAI
import time


@dataclass
class LLMConfig:
    """
    LLM call settings (keep them centralized for reproducibility).
    """
    model: str = "gpt-4o"      
    temperature: float = 0.1
    max_tokens: int = 1200
    top_p: float = 1.0
    timeout_s: float = 60.0
    retries: int = 2
    retry_backoff_s: float = 1.5


class LLMClient:
    """
    Thin adapter around an LLM provider.
    - Does NOT know about runs/, files, retrieval, etc.
    - Only knows: (system_prompt, user_prompt) -> text.
    """

    def __init__(self, cfg: Optional[LLMConfig] = None):
        self.cfg = cfg or LLMConfig()
        self._OpenAI = OpenAI
        self._client = self._OpenAI() 
        print(f"[LLM] model={cfg.model}")

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        cfg = self.cfg
        last_err: Optional[Exception] = None
        for attempt in range(cfg.retries + 1):
            try:
                resp = self._client.chat.completions.create(model=cfg.model,messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}],
                    temperature=cfg.temperature, top_p=cfg.top_p, max_tokens=cfg.max_tokens,timeout=cfg.timeout_s)
                text = resp.choices[0].message.content or ""
                return text.strip() + "\n"
            except Exception as e:
                last_err = e
                if attempt >= cfg.retries:
                    break
                time.sleep(cfg.retry_backoff_s * (attempt + 1))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

GLOBAL_LLM_CLIENT = LLMClient(LLMConfig())