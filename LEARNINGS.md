# Engineering Note: Ruleset Coverage

**Issue:** Initial testing caught only 1 of 3 intentionally-planted vulnerabilities in the demo file.

**Root cause:** The starting rulesets (`p/security-audit`, `p/owasp-top-ten`) are weighted toward framework-specific patterns (Django/Flask request objects). The demo code uses plain `sqlite3`, which fell outside their scope. This is normal SAST behavior, not a pipeline bug — no single ruleset has full coverage.

**Fix:** Added `p/python` (general Python rules) and `p/secrets` (credential detection). Result: 2/3 caught, confirmed in CI. SQL injection detection remains a known gap, not yet root-caused.

**Why it matters:** Ruleset selection is an ongoing tuning decision, not a one-time setup — every team running SAST deals with this tradeoff. Broader coverage also means more noise, which is exactly the gap TriageIQ's AI triage layer is designed to close.