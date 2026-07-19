# 🛡️ TriageIQ — AI-Powered Static Analysis Triage

> Static analysis tools find hundreds of issues. Most get ignored because no one has time to parse them. TriageIQ uses AI to tell developers exactly which 3 actually matter — automatically, on every PR.

![Build Status](https://img.shields.io/github/actions/workflow/status/<you>/triageiq/sast.yml?branch=main)
![License](https://img.shields.io/badge/license-MIT-blue)
![Powered by Gemini](https://img.shields.io/badge/AI-Gemini%203.5%20Flash-4285F4)

## Why This Matters
Static analysis tools like Semgrep are powerful but produce high false-positive rates and jargon-heavy output that developers routinely ignore — a well-documented problem called "alert fatigue" in application security. TriageIQ closes that gap: it doesn't replace the scanner, it makes the scanner's output *usable* by ranking findings by real exploitability and explaining the fix in plain language.

## What It Does
- Runs Semgrep SAST scanning on every pull request
- Sends raw findings to Gemini 3.5 Flash for severity re-ranking and plain-English remediation guidance
- Posts a single, prioritized PR comment — critical issues first, noise filtered out
- Fails the build only on confirmed high-severity issues, not every low-signal finding

## Skills Demonstrated
- Static Application Security Testing (SAST) pipeline design
- LLM integration for security triage (prompt engineering, structured JSON output, API error handling)
- CI/CD security gating (GitHub Actions)
- Reducing alert fatigue — a real, named problem in the AppSec industry

## Demo
[Screenshot: before/after — raw Semgrep JSON vs. TriageIQ's prioritized PR comment]

## How It Works
[Flow diagram: PR opened → Semgrep scans → JSON findings → Gemini triage → PR comment + check status]

```
PR opened/updated
      │
      ▼
run_semgrep.py  ──►  scans PR-changed files with Semgrep (security-audit + owasp-top-ten)
      │
      ▼
normalized-findings.json
      │
      ▼
triage_engine.py ──► prompt_builder.py builds prompt w/ code context
      │                          │
      │                          ▼
      │                 gemini_client.py calls Gemini 3.5 Flash
      │                          │
      ▼                          ▼
      └──────────► defensive JSON parsing ──► triage-report.json
                                   │
                                   ▼
                        post_pr_comment.py ──► PR comment (create or edit)
                                   │
                                   ▼
                          check_gate.py ──► fails build only on confirmed Critical
```

## Setup
See [SETUP.md](SETUP.md) for full step-by-step setup instructions, including how to add your `GEMINI_API_KEY` as a GitHub Actions secret.

## Lessons Learned
See [LEARNINGS.md](LEARNINGS.md) for a real issue found during testing (initial ruleset config only caught 1 of 3 planted demo vulnerabilities) and what it revealed about ruleset coverage, rule evasion, and why the AI triage layer matters more as you add more rulesets.

## Repository Structure
```
triageiq/
├── .github/
│   └── workflows/
│       └── sast.yml
├── scripts/
│   ├── run_semgrep.py           # Wraps semgrep CLI call, captures JSON
│   ├── triage_engine.py         # Sends findings to Gemini, parses structured response
│   ├── prompt_builder.py        # Builds the triage prompt
│   ├── post_pr_comment.py       # Formats + posts/edits the PR comment
│   ├── gemini_client.py         # Thin Gemini API wrapper
│   └── check_gate.py            # Selective build-failure gate
├── test_repo_samples/
│   └── vulnerable_app.py        # Intentionally vulnerable code for demo (SQLi, hardcoded secret, eval)
├── requirements.txt
├── README.md
├── SETUP.md
└── LICENSE
```

## Portfolio Note
This project pairs with a SOC Triage Assistant project: both apply LLMs to reduce alert fatigue in security workflows — one for SOC analysts triaging live alerts, one for developers triaging static analysis findings in CI.
