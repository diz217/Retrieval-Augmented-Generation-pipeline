# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 14:42:33 2026

@author: Ding Zhang
"""

from __future__ import annotations
import json
from typing import Dict, Any

def build_repair_user_prompt(query: str, context_text: str, candidate: str, report: Dict[str, Any]) -> str:
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])

    return ("### QUERY\n"
        f"{query.strip()}\n\n"
        "### CONTEXT\n"
        f"{context_text.strip()}\n\n"
        "### CANDIDATE (to fix)\n"
        f"{candidate.strip()}\n\n"
        "### VALIDATION REPORT\n"
        f"{json.dumps({'errors': errors, 'warnings': warnings}, ensure_ascii=False, indent=2)}\n")
