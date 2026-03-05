# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 02:41:45 2026

@author: Ding Zhang
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# Data structures
@dataclass
class Issue:
    code: str
    msg: str
    line: Optional[int] = None
    key: Optional[str] = None


@dataclass
class ValidationResult:
    ok: bool
    errors: List[Issue]
    warnings: List[Issue]
    parsed: Dict[str, str]
    submission_key: Optional[str] = None
    master_key: Optional[str] = None
    queue: Optional[str] = None
    jobname_token: Optional[str] = None
    dep_var: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "parsed": self.parsed,
            "submission_key": self.submission_key,
            "master_key": self.master_key,
            "queue": self.queue,
            "jobname_token": self.jobname_token,
            "dep_var": self.dep_var,
        }

# Parsing (syntax)
_KEY_RE = re.compile(r"^[A-Za-z0-9_`]+$")  # allow `masked keys`, dots, hyphen
_COMMENT_RE = re.compile(r"^\s*#")


def parse_kv_lines(text: str) -> Tuple[Dict[str, str], List[Issue], List[Issue]]:
    """
    Parse DSL lines: key = value
    - Skips empty lines
    - Skips comment lines starting with '#'
    - Strips whitespace around key/value
    """
    parsed: Dict[str, str] = {}
    errors: List[Issue] = []

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if _COMMENT_RE.match(line):
            continue

        if "=" not in line:
            errors.append(Issue(code="PARSE_NO_EQUAL", msg="Line missing '='", line=i))
            continue

        key, value = line.split("=", 1)
        key = key.strip().strip('"').strip("'")
        value = value.strip().strip('"').strip("'")

        if not key:
            errors.append(Issue(code="PARSE_EMPTY_KEY", msg="Empty key", line=i))
            continue
        if not _KEY_RE.match(key):
            errors.append(Issue(code="KEY_SUSPICIOUS", msg=f"Suspicious key format: {key}", line=i, key=key))

        # Duplicate key policy: last one wins, but warn
        if key in parsed:
            errors.append(Issue(code="DUPLICATE_KEY", msg=f"Duplicate key overwritten: {key}", line=i, key=key))

        parsed[key] = value

    return parsed, errors

# Semantic heuristics
def _find_master_js(parsed: Dict[str, str]) -> Optional[str]:
    # master job template recognized ONLY if value ends with ".js"
    for k, v in parsed.items():
        if v.lower().endswith(".js"):
            return k
    return None

def _is_submission_value(v: str) -> bool:
    return "uds:" in v.lower()

def _find_submission(parsed: Dict[str, str]) -> Optional[str]:
    # If multiple look like submission, prefer one with queue keyword.
    candidates = []
    for k, v in parsed.items():
        if _is_submission_value(v):
            candidates.append(k)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def score(key: str) -> int:
        v = parsed[key].lower()
        s = 0
        if "sparaq" in v or "slurmq" in v:
            s += 10
        if v.strip().startswith("{"):
            s += 2
        if "-d" in v:
            s += 2
        if "-z" in v:
            s += 1
        return s

    candidates.sort(key=score, reverse=True)
    return candidates[0]

def _extract_queue(submission_value: str) -> Optional[str]:
    v = submission_value.lower()
    if "sparaq" in v:
        return "sparaq"
    if "slurmq" in v:
        return "slurmq"
    return None

def _has_sparaq_n_flag(submission_value: str) -> bool:
    v = submission_value.lower()
    return re.search(r"(^|\s)-n\d+(\s|$)", v) is not None

def _extract_first_token(submission_value: str) -> Optional[str]:
    # first whitespace-separated token
    s = submission_value.strip()
    if not s:
        return None
    return s.split()[0]

def _extract_dep_var(submission_value: str) -> Optional[str]:
    m = re.search(r"\s-d\{([A-Za-z0-9_,]+)\}", submission_value)
    if m:
        return m.group(1)
    else:
        m = re.search(r"\s-d[A-Za-z0-9_./]*\{([A-Za-z0-9_]+)\}.js",submission_value)
        if m: return m.group(1)
    return None

def _token_refers_to_var(token: str) -> Optional[str]:
    m = re.fullmatch(r"\{([A-Za-z0-9_]+)\}", token.strip())
    if m:
        return m.group(1)
    return None

# Validator v1
def validate_candidate(text: str) -> ValidationResult:
    parsed, errors = parse_kv_lines(text)
    warnings: List[Issue] = []
    master_key = _find_master_js(parsed)
    submission_key = _find_submission(parsed)

    queue = None
    jobname_token = None
    dep_var = None

    if master_key is None:
        errors.append(Issue(code="MISSING_MASTER_JS", msg="Missing master job template: no value ends with '.js'"))
    if submission_key is None:
        errors.append(Issue(code="MISSING_SUBMISSION", msg="Missing submission command: no line looks like a submission command (uds: + sparaq/slurmq)"))
    else:
        sub_val = parsed[submission_key]
        queue = _extract_queue(sub_val)
        if queue is None:
            errors.append(Issue(code="QUEUE_UNKNOWN", msg="Submission command does not contain 'sparaq' or 'slurmq'"))
        if '-r' not in sub_val:
            errors.append(Issue(code="MISSING PRIORITY IN SUBMISSION", msg="Missing -r",line=sub_val))
        if '-z' not in sub_val:
            errors.append(Issue(code="MISSING STAGE NAME IN SUBMISSION", msg="Missing -z",line=sub_val))
        # jobname token = first token of submission command
        jobname_token = _extract_first_token(sub_val)
        if not jobname_token:
            errors.append(Issue(code="EMPTY_OUTPUT_SUBMISSION", msg="Missing output name in SUBMISSION", key=submission_key))
        else:
            varref = _token_refers_to_var(jobname_token)
            if varref is None:
                errors.append(Issue(code="WRONG_OUTPUT_NAME",msg=f"output name {jobname_token} contains illegal characters, ascii only",key=submission_key))
            elif varref not in parsed:
                errors.append(Issue(code="JOBNAME_VAR_UNDEFINED",msg=f"Submission first token references undefined variable: {jobname_token}",key=submission_key))
        # dependency must reference some var
        dep_var = _extract_dep_var(sub_val)
        if dep_var is None:
            warnings.append(Issue(code="MISSING_DEPENDENCY",msg="Submission command missing dependency reference '-d{...}'",key=submission_key))
        else:
            dep_list = dep_var.strip().split(',')
            for dep in dep_list:
                if dep.strip() not in parsed:
                    errors.append(Issue(code="DEP_VAR_UNDEFINED",msg=f"Dependency variable referenced in -d{{...}} is undefined: {dep}",key=submission_key))
        # queue constraint: sparaq requires -n
        if queue == "sparaq" and not _has_sparaq_n_flag(sub_val):
            errors.append(Issue(code="SPARAQ_MISSING_N",msg="Queue 'sparaq' requires '-n<integer>' in submission command",key=submission_key))

    ok = (len(errors) == 0)
    return ValidationResult(
        ok=ok,
        errors=errors,
        warnings=warnings,
        parsed=parsed,
        submission_key=submission_key,
        master_key=master_key,
        queue=queue,
        jobname_token=jobname_token,
        dep_var=dep_var)

def validate_file(candidate_path: Path) -> ValidationResult:
    text = Path(candidate_path).read_text(encoding="utf-8")
    return validate_candidate(text)

def write_validation_json(result: ValidationResult, out_path: Path) -> None:
    Path(out_path).write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

# Convenience CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) not in (2, 3):
        print("Usage: python -m llm.validator <candidate.txt> [validation.json]")
        raise SystemExit(2)

    cand = Path(sys.argv[1])
    res = validate_file(cand)

    if len(sys.argv) == 3:
        out = Path(sys.argv[2])
        write_validation_json(res, out)
        print(f"Wrote validation report to {out}")
    else:
        print(json.dumps(res.to_dict(), indent=2))