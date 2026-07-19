"""
check_gate.py
Reads triage-report.json (written by triage_engine.py) and exits 1 only if
there is at least one finding with true_severity == "Critical" AND
is_likely_false_positive == false.

This selective gating -- failing only on confirmed critical issues, not
every low-signal finding -- is a deliberate design choice: it reduces
false-positive fatigue compared to naive scanners that block merges on
every finding regardless of real exploitability.
"""

import json
import os
import sys

TRIAGE_REPORT_PATH = "triage-report.json"


def main():
    if not os.path.isfile(TRIAGE_REPORT_PATH):
        print(f"[check_gate] {TRIAGE_REPORT_PATH} not found; nothing to gate on. Passing.")
        sys.exit(0)

    with open(TRIAGE_REPORT_PATH, "r", encoding="utf-8") as f:
        triage_result = json.load(f)

    findings = triage_result.get("findings", [])
    blocking = [
        f for f in findings
        if f.get("true_severity") == "Critical" and not f.get("is_likely_false_positive", False)
    ]

    if blocking:
        print(f"[check_gate] ❌ {len(blocking)} confirmed Critical finding(s) block this PR:")
        for f in blocking:
            print(f"  - {f.get('file')}:{f.get('line')} ({f.get('rule_id')})")
        sys.exit(1)

    print("[check_gate] ✅ No confirmed Critical findings. Build passes (lower-severity findings, if any, are reported but non-blocking).")
    sys.exit(0)


if __name__ == "__main__":
    main()
