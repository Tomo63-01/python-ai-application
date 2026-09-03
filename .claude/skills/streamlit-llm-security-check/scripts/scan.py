#!/usr/bin/env python3
"""Deterministic static scanner for Streamlit + LLM-API applications.

Finds the kind of thing a human reviewer would grep for by hand: hardcoded
secrets, dangerous calls, unsafe HTML rendering, and whether .env is actually
protected from being committed. Prints a single JSON object to stdout.

This script only reports *candidates* — it has no idea whether a given
match is actually exploitable in context (e.g. an `eval()` call sitting
behind a hardcoded, developer-only input is very different from one fed by
a Streamlit text box). Read the surrounding code before writing findings
into the report; use this output as a worklist, not a verdict.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Scanned source files may contain non-ASCII text (Japanese UI strings, em
# dashes in comments, etc.). Windows consoles often default stdout to a
# legacy codepage (cp932) that can't encode them, so force UTF-8 here.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".streamlit",
    # Claude Code tooling directories, not application code.
    ".claude", ".agents",
}

# Secret-looking assignments. Deliberately excludes os.getenv/os.environ
# reads (those are the *correct* pattern) and obvious placeholders.
SECRET_PATTERN = re.compile(
    r"""(?i)\b(api[_-]?key|secret|token|password|access[_-]?key)\b\s*[:=]\s*
        (?P<q>["'])(?P<val>[^"'\n]{12,})(?P=q)""",
    re.VERBOSE,
)
PLACEHOLDER_RE = re.compile(
    r"(?i)^(your|my|example|placeholder|xxx|test|dummy|<|\.\.\.|change[_-]?me|none|null)"
)

DANGEROUS_CALL_PATTERNS = {
    "eval(": r"\beval\s*\(",
    "exec(": r"\bexec\s*\(",
    "os.system(": r"\bos\.system\s*\(",
    "subprocess with shell=True": r"subprocess\.\w+\([^)]*shell\s*=\s*True",
    "pickle.loads(": r"\bpickle\.loads?\s*\(",
    "requests with verify=False": r"verify\s*=\s*False",
    "yaml.load( without SafeLoader)": r"yaml\.load\s*\((?!.*SafeLoader)",
}

UNSAFE_HTML_PATTERN = re.compile(r"unsafe_allow_html\s*=\s*True")

BROAD_EXCEPTION_TO_UI_PATTERNS = {
    "raw exception shown via st.error/st.write/st.exception": (
        r"st\.(error|write|exception|markdown|text)\s*\(\s*(str\(exc"
        r"|str\(e\)|traceback\.|repr\(exc)"
    ),
}


def iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def scan_secrets(root: Path):
    findings = []
    for path in iter_py_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            m = SECRET_PATTERN.search(line)
            if m and not PLACEHOLDER_RE.match(m.group("val").strip()):
                findings.append({
                    "file": str(path.relative_to(root)),
                    "line": i,
                    "snippet": line.strip()[:200],
                })
    return findings


def scan_dangerous_calls(root: Path):
    findings = []
    for path in iter_py_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in DANGEROUS_CALL_PATTERNS.items():
            for i, line in enumerate(text.splitlines(), start=1):
                if re.search(pattern, line):
                    findings.append({
                        "type": label,
                        "file": str(path.relative_to(root)),
                        "line": i,
                        "snippet": line.strip()[:200],
                    })
    return findings


def scan_unsafe_html(root: Path):
    findings = []
    for path in iter_py_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if UNSAFE_HTML_PATTERN.search(line):
                findings.append({
                    "file": str(path.relative_to(root)),
                    "line": i,
                    "snippet": line.strip()[:200],
                })
    return findings


def scan_broad_exception_exposure(root: Path):
    findings = []
    for path in iter_py_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in BROAD_EXCEPTION_TO_UI_PATTERNS.items():
            for i, line in enumerate(text.splitlines(), start=1):
                if re.search(pattern, line):
                    findings.append({
                        "type": label,
                        "file": str(path.relative_to(root)),
                        "line": i,
                        "snippet": line.strip()[:200],
                    })
    return findings


def check_env_protection(root: Path):
    result = {
        "env_file_present": False,
        "gitignore_present": False,
        "env_ignored_by_gitignore": None,
        "env_tracked_by_git": None,
        "note": "",
    }
    env_path = root / ".env"
    result["env_file_present"] = env_path.exists()

    gitignore_path = root / ".gitignore"
    result["gitignore_present"] = gitignore_path.exists()
    if gitignore_path.exists():
        gi_text = gitignore_path.read_text(encoding="utf-8", errors="ignore")
        patterns = [ln.strip() for ln in gi_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        result["env_ignored_by_gitignore"] = any(p in (".env", "*.env", ".env*") for p in patterns)

    if (root / ".git").exists():
        try:
            out = subprocess.run(
                ["git", "-C", str(root), "ls-files", ".env"],
                capture_output=True, text=True, timeout=10,
            )
            result["env_tracked_by_git"] = bool(out.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            result["note"] = "git not available to verify tracked status"
    else:
        result["note"] = "no .git directory found — not a git repo, so nothing can leak via git history here"

    return result


def find_dependency_files(root: Path):
    names = ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "environment.yml"]
    found = {}
    for name in names:
        p = root / name
        if p.exists():
            found[name] = p.read_text(encoding="utf-8", errors="ignore")
    return found


def try_pip_audit(root: Path):
    req = root / "requirements.txt"
    if not req.exists():
        return {"ran": False, "reason": "no requirements.txt found"}
    try:
        out = subprocess.run(
            ["pip-audit", "-r", str(req), "-f", "json"],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode in (0, 1) and out.stdout.strip():
            try:
                return {"ran": True, "result": json.loads(out.stdout)}
            except json.JSONDecodeError:
                return {"ran": True, "raw_output": out.stdout[:5000]}
        return {"ran": False, "reason": f"pip-audit exited {out.returncode}: {out.stderr[:500]}"}
    except FileNotFoundError:
        return {"ran": False, "reason": "pip-audit is not installed (pip install pip-audit to enable this check)"}
    except subprocess.SubprocessError as exc:
        return {"ran": False, "reason": f"pip-audit failed: {exc}"}


def find_llm_call_sites(root: Path):
    """Surface the files most likely to build prompts or call an LLM API,
    so the model reviewing this output knows where to look for prompt-injection
    and data-exfiltration risk without having to grep the whole tree itself."""
    keyword_pattern = re.compile(
        r"(?i)(generateContent|chat\.completions|openai|anthropic|gemini|"
        r"generativelanguage|\.messages\.create|completions\.create)"
    )
    hits = []
    for path in iter_py_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if keyword_pattern.search(text):
            hits.append(str(path.relative_to(root)))
    return hits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Project root to scan")
    parser.add_argument("--skip-pip-audit", action="store_true", help="Skip the pip-audit dependency check")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    report = {
        "root": str(root),
        "hardcoded_secrets": scan_secrets(root),
        "dangerous_calls": scan_dangerous_calls(root),
        "unsafe_allow_html_usage": scan_unsafe_html(root),
        "broad_exception_exposure": scan_broad_exception_exposure(root),
        "env_protection": check_env_protection(root),
        "dependency_files": list(find_dependency_files(root).keys()),
        "llm_call_sites": find_llm_call_sites(root),
        "pip_audit": {"ran": False, "reason": "skipped"} if args.skip_pip_audit else try_pip_audit(root),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
