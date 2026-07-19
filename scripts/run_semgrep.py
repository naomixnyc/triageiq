"""
run_semgrep.py
Wraps the semgrep CLI call. Scans only files changed in the current PR
(via `git diff --name-only origin/main...HEAD`) rather than the whole repo,
so scans stay fast, cheap, and relevant to the PR under review.

Writes raw Semgrep JSON output to semgrep-report.json in the repo root.
"""

import json
import os
import subprocess
import sys

SEMGREP_CONFIGS = ["p/security-audit", "p/owasp-top-ten"]
OUTPUT_PATH = "semgrep-report.json"


def get_changed_files(base_ref: str = "origin/main") -> list:
    """
    Returns a list of files changed between `base_ref` and HEAD.
    Falls back to scanning the whole repo (empty list signals "no filter")
    if git diff fails, e.g. when run locally outside a PR context.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        # Only keep files that still exist (ignore deleted files) and are
        # plausible source files.
        files = [f for f in files if os.path.isfile(f)]
        return files
    except subprocess.CalledProcessError as exc:
        print(f"[run_semgrep] git diff failed ({exc}); falling back to full repo scan.", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("[run_semgrep] git not found; falling back to full repo scan.", file=sys.stderr)
        return []


def run_semgrep(target_files: list, output_path: str = OUTPUT_PATH) -> dict:
    """
    Runs semgrep against `target_files` (or the whole repo if the list is
    empty) using the configured public rulesets, writes JSON output to
    `output_path`, and returns the parsed JSON dict.
    """
    cmd = ["semgrep"]
    for cfg in SEMGREP_CONFIGS:
        cmd.extend(["--config", cfg])
    cmd.extend(["--json", "--output", output_path])

    if target_files:
        cmd.extend(target_files)
    else:
        cmd.append(".")

    print(f"[run_semgrep] running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    # Semgrep exits non-zero when findings are present -- that's expected
    # and not itself an error. Only treat it as fatal if no output file
    # was produced at all.
    if not os.path.isfile(output_path):
        print("[run_semgrep] semgrep did not produce an output file.", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        sys.exit(1)

    with open(output_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_findings(raw_semgrep_json: dict) -> list:
    """
    Converts raw Semgrep JSON `results` entries into the simplified finding
    dicts expected by prompt_builder.py / triage_engine.py.
    """
    normalized = []
    for result in raw_semgrep_json.get("results", []):
        normalized.append(
            {
                "file": result.get("path", ""),
                "line": result.get("start", {}).get("line", 0),
                "rule_id": result.get("check_id", "unknown"),
                "message": result.get("extra", {}).get("message", ""),
                "severity": result.get("extra", {}).get("severity", "unknown"),
            }
        )
    return normalized


def main():
    changed_files = get_changed_files()
    if changed_files:
        print(f"[run_semgrep] scanning {len(changed_files)} changed file(s): {changed_files}")
    else:
        print("[run_semgrep] no changed-file list available; scanning full repo.")

    raw = run_semgrep(changed_files)
    findings = normalize_findings(raw)

    with open("normalized-findings.json", "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)

    print(f"[run_semgrep] {len(findings)} finding(s) written to normalized-findings.json")


if __name__ == "__main__":
    main()
