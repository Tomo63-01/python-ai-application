---
name: streamlit-llm-security-check
description: Runs a security review of a Streamlit application that calls an LLM/AI API (Gemini, OpenAI, Anthropic, etc.), producing a dated Markdown security report under reports/. Covers both general web-app risks (hardcoded secrets, .env/.gitignore hygiene, dependency CVEs, unsafe error handling, TLS/timeout misconfiguration) and risks specific to LLM apps (prompt injection, unsafe HTML rendering of model output, third-party data exposure from what gets sent to the API). Use this whenever the user asks for a security check, security review, vulnerability scan, "is this app safe", 脆弱性チェック, セキュリティチェック, or セキュリティレビュー on a Streamlit or LLM-backed Python app — even if they only name one narrow concern (e.g. "check my API key isn't leaking") rather than asking for a full review, since the same pass covers the rest cheaply.
---

# Streamlit + LLM API Security Check

## Why this exists

Streamlit apps that call an LLM API sit at the intersection of two risk
categories that neither a generic web-security checklist nor a generic
"prompt injection" writeup covers on its own: they're often small,
single-file, quickly-deployed tools (so basics like `.gitignore` hygiene
get skipped), and they route arbitrary user text through a paid third-party
API and back into the UI (so prompt injection and unsafe rendering are live
concerns even in a "just a writing tool" app). This skill runs both angles
in one pass.

## Workflow

### 1. Find the app root

Usually the current project directory. If it's ambiguous (a monorepo with
multiple Streamlit apps, for instance), ask the user which one to target.

### 2. Run the deterministic scanner

```
python .claude/skills/streamlit-llm-security-check/scripts/scan.py <app_root>
```

This does the grunt work that's tedious and error-prone to redo by hand
every time: finds hardcoded-secret-looking assignments, dangerous calls
(`eval`, `exec`, `os.system`, `shell=True`, `verify=False`, unsafe
`yaml.load`), every `unsafe_allow_html=True` site, places that show a raw
exception to the user, whether `.env` exists and is actually covered by
`.gitignore` (and, if it's a git repo, whether it's already tracked —
which `.gitignore` alone can't undo), which files call an LLM API (so you
know where to focus the manual read), and a `pip-audit` dependency scan if
`pip-audit` is installed (pass `--skip-pip-audit` to skip it deliberately;
otherwise a missing tool is reported as "not installed," not silently
treated as "no issues found" — that distinction matters for the report).

Treat everything it prints as a **worklist of candidates**, not a list of
confirmed findings — a regex has no idea whether an `eval()` call is fed by
a hardcoded string or a Streamlit text box. The next step is where you
supply that judgment.

### 3. Read the actual data flow

This is the part the script can't do. Open the files it flagged under
`llm_call_sites` and trace, for each user-facing input field:

- Does it flow into the LLM prompt with any separation between "developer
  instructions" and "untrusted user content," or is it just concatenated
  in? This determines the prompt-injection severity.
- Does the LLM's *output* ever get rendered with `unsafe_allow_html=True`,
  written to a file, executed, or piped into another privileged action?
- What exactly gets sent to the third-party API — just the immediate input,
  or something broader (an entire uploaded document, email thread, etc.)?
- Is the app meant to run locally for one person, or be deployed somewhere
  reachable by others? This single fact changes the severity of missing
  auth, verbose error messages, and shared API-key exposure — don't assess
  those in a vacuum.

Read `references/checklist.md` for the full reasoning behind each risk
category (why it matters for *this kind* of app, and what a good fix looks
like) — pull up the relevant section once you have a candidate finding in
hand, rather than reading it all upfront.

### 4. Write the report

Save to `reports/security-YYYYMMDD.md` (create the `reports/` directory if
it doesn't exist; use today's actual date). Keep past reports in place —
don't overwrite — so the user can see the history of scans over time.

Use this structure:

```markdown
# Security Report — <app name> — YYYY-MM-DD

## Summary
Critical: N · High: N · Medium: N · Low: N

One or two sentences on overall posture — e.g. "no critical issues; the
main gap is prompt-injection hardening around the email-summary feature."

## Findings

### [CRITICAL|HIGH|MEDIUM|LOW] <short title>
- **File:** path:line
- **Issue:** what's actually wrong, in plain terms
- **Risk:** the concrete scenario where this bites someone — not just
  "this is bad practice"
- **Fix:** a specific, actionable change

(repeat per finding, most severe first)

## Dependency scan
Result of pip-audit, or a note that it wasn't installed and should be run
manually (`pip install pip-audit && pip-audit -r requirements.txt`).

## Verified OK
Short bullet list of things you specifically checked and found fine — this
tells the reader what was covered, not just what was wrong.
```

Assign severity based on realistic impact for *this app's actual
deployment context*, not the pattern in isolation — `references/checklist.md`
explains this per-category (e.g. missing auth is a non-issue for a local
single-user tool but a real Medium/High once shared). When in doubt about
deployment context, ask the user rather than guessing.

### 5. Tell the user what you found

After writing the report, summarize the top 2-3 findings in the
conversation directly (severity + one-line fix) rather than just pointing
at the file — most users want the headline before they go open a Markdown
file.
