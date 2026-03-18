# validator.py (desensitized version, examplar validation not for production)
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "parsed": self.parsed}

_KEY_RE = re.compile(r"^[A-Za-z0-9_`]+$")
_COMMENT_RE = re.compile(r"^\s*#")

def parse_kv_lines(text: str) -> Tuple[Dict[str, str], List[Issue]]:
    parsed: Dict[str, str] = {}
    errors: List[Issue] = []

    lines = text.splitlines()

    for i, raw in enumerate(lines, start=1):
        line = raw.strip()

        if not line or _COMMENT_RE.match(line):
            continue

        if "=" not in line:
            errors.append(Issue("PARSE_NO_EQUAL", "Missing '='", i))
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            errors.append(Issue("EMPTY_KEY", "Empty key", i))
            continue

        if not _KEY_RE.match(key):
            errors.append(Issue("INVALID_KEY", f"Invalid key format: {key}", i))

        if key in parsed:
            errors.append(Issue("DUPLICATE_KEY", f"Duplicate key: {key}", i))

        parsed[key] = value

    return parsed, errors

def validate_candidate(text: str) -> ValidationResult:
    parsed, errors = parse_kv_lines(text)
    warnings: List[Issue] = []

    # ---- Rule 1: must contain at least one executable reference ----
    has_executable = any(v.endswith((".js", ".py", ".sh")) for v in parsed.values())

    if not has_executable:
        errors.append(Issue("NO_EXECUTABLE", "No executable reference found (.js/.py/.sh)"))

    # ---- Rule 2: must contain at least one command-like entry ----
    has_command = any(len(v.split()) > 1 for v in parsed.values())

    if not has_command:
        errors.append(Issue("NO_COMMAND", "No command-like entry found"))

    # ---- Rule 3: detect variable references ----
    var_pattern = re.compile(r"\{([A-Za-z0-9_]+)\}")

    for k, v in parsed.items():
        refs = var_pattern.findall(v)
        for ref in refs:
            if ref not in parsed:
                errors.append(Issue("UNDEFINED_VARIABLE", f"{ref} referenced but not defined", key=k))
    ok = len(errors) == 0
    return ValidationResult(ok=ok,errors=errors,warnings=warnings,parsed=parsed)

def validate_file(candidate_path: Path) -> ValidationResult:
    text = candidate_path.read_text(encoding="utf-8")
    return validate_candidate(text)
    
def write_validation_json(result: ValidationResult, out_path: Path) -> None:
    out_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

if __name__ == "__main__":
    import sys

    if len(sys.argv) not in (2, 3):
        print("Usage: python validator.py <input> [output.json]")
        raise SystemExit(2)

    res = validate_file(Path(sys.argv[1]))

    if len(sys.argv) == 3:
        write_validation_json(res, Path(sys.argv[2]))
    else:
        print(json.dumps(res.to_dict(), indent=2))
