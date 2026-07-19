"""
triage_engine.py
Orchestrates the AI triage step:
  1. Load normalized Semgrep findings (from run_semgrep.py)
  2. Build the triage prompt (prompt_builder.py)
  3. Call Gemini (gemini_client.py)
  4. Defensively parse the response into structured JSON
  5. Post/update the PR comment (post_pr_comment.py)

Also writes triage-report.json to disk so check_gate.py can read the
final, AI-re-ranked severities without re-calling the API.
"""

import json
import os
import re
import sys

from gemini_client import GeminiAPIError, GeminiClient
from post_pr_comment import post_or_update_comment
from prompt_builder import build_triage_prompt

FINDINGS_INPUT_PATH = "normalized-findings.json"
TRIAGE_OUTPUT_PATH = "triage-report.json"

# Defaults applied to any finding missing keys in the parsed Gemini
# response, so a malformed/partial response never crashes the pipeline.
FINDING_DEFAULTS = {
    "file": "unknown",
    "line": 0,
    "rule_id": "unknown",
    "true_severity": "Low",
    "exploitability": "Unknown",
    "plain_english_explanation": "No explanation provided by the AI triage step.",
    "suggested_fix": "No fix suggestion provided by the AI triage step.",
    "is_likely_false_positive": False,
}

CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    """Removes leading/trailing ```json ... ``` fences Gemini sometimes adds
    even when explicitly told to return raw JSON."""
    return CODE_FENCE_RE.sub("", text).strip()


def _parse_response(raw_text: str) -> dict:
    """
    Defensive parser for the Gemini triage response.

    Order of attempts:
      1. Strip code fences, then json.loads() directly.
      2. If that fails, regex-extract the first {...} blob and try again.
      3. If that also fails, return a safe fallback structure so the
         pipeline degrades gracefully instead of crashing.
    """
    cleaned = _strip_code_fences(raw_text)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = JSON_OBJECT_RE.search(cleaned)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = None
        else:
            parsed = None

    if not isinstance(parsed, dict):
        print("[triage_engine] WARNING: could not parse Gemini response as JSON; using fallback.", file=sys.stderr)
        return {
            "findings": [],
            "summary": (
                "AI triage response could not be parsed. Raw Semgrep findings are "
                "available in the Actions log; please review manually."
            ),
        }

    # Apply defaults for any missing keys on each finding.
    raw_findings = parsed.get("findings", [])
    if not isinstance(raw_findings, list):
        raw_findings = []

    normalized_findings = []
    for f in raw_findings:
        if not isinstance(f, dict):
            continue
        merged = dict(FINDING_DEFAULTS)
        merged.update(f)
        normalized_findings.append(merged)

    return {
        "findings": normalized_findings,
        "summary": parsed.get("summary", "No summary provided."),
    }


def load_findings(path: str = FINDINGS_INPUT_PATH) -> list:
    if not os.path.isfile(path):
        print(f"[triage_engine] {path} not found; assuming zero findings.", file=sys.stderr)
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    findings = load_findings()

    if not findings:
        print("[triage_engine] No Semgrep findings to triage. Skipping Gemini call.")
        triage_result = {"findings": [], "summary": "No findings reported by Semgrep for this PR."}
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        prompt = build_triage_prompt(findings, repo_root=".")

        try:
            client = GeminiClient(api_key)
            raw_response = client.triage(prompt)
            triage_result = _parse_response(raw_response)
        except GeminiAPIError as exc:
            print(f"[triage_engine] Gemini triage failed: {exc.technical_detail}", file=sys.stderr)
            # Graceful degradation: fall back to raw Semgrep findings with
            # a clear note, instead of crashing the whole pipeline.
            triage_result = {
                "findings": [
                    {**FINDING_DEFAULTS, "file": f["file"], "line": f["line"], "rule_id": f["rule_id"],
                     "true_severity": f.get("severity", "Low").title() if isinstance(f.get("severity"), str) else "Low",
                     "exploitability": "Unknown (AI triage unavailable)",
                     "plain_english_explanation": f.get("message", "No description available."),
                     "suggested_fix": "AI triage was unavailable; review this finding manually.",
                     "is_likely_false_positive": False}
                    for f in findings
                ],
                "summary": f"⚠️ AI triage step failed: {exc.user_message}",
                "ai_triage_failed": True,
            }

    with open(TRIAGE_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(triage_result, f, indent=2)

    print(f"[triage_engine] triage report written to {TRIAGE_OUTPUT_PATH}")

    # Post/update the PR comment (only actually posts if running in a
    # GitHub Actions PR context with the right env vars set).
    post_or_update_comment(triage_result)


if __name__ == "__main__":
    main()
