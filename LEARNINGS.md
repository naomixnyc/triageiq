# LEARNINGS.md — Notes from setting up TriageIQ

This file documents a real issue found while testing this project, why it
happened, and what changed as a result. Keeping it so future-me (or anyone
else reading this repo) understands the "why" behind the current ruleset
config instead of just seeing four `--config` flags with no context.

---

## The issue

On the first real test PR, `test_repo_samples/vulnerable_app.py` (which has
3 intentionally planted vulnerabilities: SQL injection, a hardcoded secret,
and an unsafe `eval()` call) only triggered **1 finding**, not 3.

## Why — in plain terms

Semgrep doesn't "understand" code the way a human security reviewer does.
It matches **specific code shapes** defined by rules, kind of like a very
smart find-and-replace. A rule for SQL injection might specifically look
for Django's `request.GET.get(...)` flowing into a query — that's a very
different shape than a plain `sqlite3` cursor with an f-string, even
though both are the same underlying vulnerability.

**Vocabulary, for reference:**
- **Ruleset / rule pack** — a bundle of individual detection rules, hosted
  publicly at Semgrep's registry (`semgrep.dev/r`). `p/security-audit` and
  `p/owasp-top-ten` are two specific named bundles within that registry.
- These bundles are written/maintained by Semgrep and open-source
  contributors — not by us, and not custom to this project.

**What we originally picked** (`p/security-audit`, `p/owasp-top-ten`) turned
out to lean heavily on **framework-specific** patterns (Django/Flask request
objects flowing into a query). Our demo file uses plain `sqlite3` with no
web framework, so it fell outside the shape those two packs check for. The
`eval()` misuse *was* caught, because that pattern is generic enough to be
included in `security-audit`.

This is not a bug in the pipeline, and not a flaw in Semgrep — it's the
expected behavior of any pattern-based scanner: **coverage is only as good
as the rulesets you choose**, and no single pack catches everything.

## What changed

Added two more rulesets in `scripts/run_semgrep.py`:
- `p/python` — general Python security rules, including the
  framework-agnostic "formatted SQL query" pattern that matches plain
  f-string/`.format()`/`%`-style queries regardless of framework.
- `p/secrets` — dedicated hardcoded-credential/API-key detection.

Also adjusted the demo file's fake secret from `sk-live-...` to
`sk_live_...` (underscore) to match the real format that Stripe-key
detection rules key off of — the hyphen version didn't match any known
secret pattern.

## Bigger-picture takeaways (worth remembering)

1. **"It didn't get flagged" ≠ "it's not a real vulnerability."** All 3
   demo vulnerabilities were genuinely exploitable code the whole time —
   detection is a separate question from whether something is actually bad.
2. **Ruleset selection is an ongoing, real job**, not a one-time setup.
   Real security teams layer multiple packs (and often write custom rules)
   because no single pack has full coverage. This exact gap is the
   "alert fatigue vs. blind spots" tradeoff that motivated this whole
   project in the first place — worth mentioning in interviews.
3. **Public rules are a double-edged sword.** Because Semgrep's community
   rules are open source, anyone — including attackers — can study exactly
   what pattern a rule looks for and write code that's still vulnerable but
   shaped to slip past it (this is called **rule evasion**). Real
   organizations mitigate this with private/custom rules, multiple
   overlapping tools, and human code review — automated scanning is one
   layer, not the whole defense.
4. **More rulesets = more coverage, but also more noise** (more
   false positives). That's precisely where TriageIQ's AI triage layer
   earns its keep — it gets more valuable, not less, as you add more
   rulesets, because someone/something still needs to filter the noise.

## Verification note

This project's dev sandbox has network restrictions that block
`semgrep.dev`, so the added rulesets could only be verified locally using
hand-written rules that mimic the real ones' shape (confirmed the demo
file's code now matches those shapes). Final confirmation happens in
GitHub Actions, which has full internet access to the real registry.
