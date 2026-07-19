"""
prompt_builder.py
Builds the prompt sent to Gemini for security finding triage, including
surrounding code context so the model can assess real-world exploitability
rather than just repeating Semgrep's own severity label.
"""

import os

CONTEXT_LINES = 5  # ±5 lines around each finding


def _extract_code_context(file_path: str, line_number: int, context_lines: int = CONTEXT_LINES) -> str:
    """
    Reads `file_path` and returns a snippet of `context_lines` lines above
    and below `line_number` (1-indexed), with line numbers prefixed.

    Returns an empty string (rather than raising) if the file can't be read,
    so a single missing/renamed file never crashes the whole triage run.
    """
    if not file_path or not os.path.isfile(file_path):
        return "(source file not available for context)"

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return "(source file could not be read for context)"

    total = len(lines)
    if total == 0:
        return "(source file is empty)"

    # line_number is 1-indexed; clamp to valid range.
    center = max(1, min(line_number, total))
    start = max(1, center - context_lines)
    end = min(total, center + context_lines)

    snippet_lines = []
    for ln in range(start, end + 1):
        marker = ">>" if ln == center else "  "
        snippet_lines.append(f"{marker} {ln}: {lines[ln - 1].rstrip()}")

    return "\n".join(snippet_lines)


def build_triage_prompt(findings: list, repo_root: str = ".") -> str:
    """
    Builds the full prompt string sent to Gemini.

    `findings` is the list of raw Semgrep finding dicts (already normalized
    by run_semgrep.py) each expected to have at minimum:
        file, line, rule_id, message, severity
    """
    findings_blocks = []
    for idx, finding in enumerate(findings, start=1):
        file_path = finding.get("file", "")
        line_number = finding.get("line", 0)
        abs_path = os.path.join(repo_root, file_path) if file_path else ""
        context = _extract_code_context(abs_path, line_number)

        findings_blocks.append(
            f"""Finding #{idx}
file: {file_path}
line: {line_number}
rule_id: {finding.get("rule_id", "unknown")}
semgrep_message: {finding.get("message", "")}
semgrep_reported_severity: {finding.get("severity", "unknown")}
code_context:
{context}
"""
        )

    findings_text = "\n---\n".join(findings_blocks) if findings_blocks else "(no findings)"

    prompt = f"""You are a senior application security engineer triaging static analysis (Semgrep) findings for a pull request.

Semgrep's reported severity is rule-based and NOT context-aware. Your job is to RE-RANK each finding's true severity based on actual exploitability given the surrounding code context provided below -- do not simply repeat Semgrep's own severity label.

For each finding, decide:
- true_severity: one of "Critical", "High", "Medium", "Low"
- exploitability: a short phrase explaining how exploitable this actually is given the code context (e.g. "High -- user input flows directly into raw SQL query")
- plain_english_explanation: 1-2 plain-English sentences a developer with no security background can understand
- suggested_fix: a concrete, specific fix (name the actual function/pattern to use)
- is_likely_false_positive: true or false -- true if the code context shows this is not actually exploitable (e.g. input is already sanitized, it's test/demo code, etc.)

Here are the raw findings with surrounding code context:

{findings_text}

Respond with STRICT JSON ONLY. Do not include any explanation, preamble, or markdown code fences -- return only the raw JSON object matching this exact schema:

{{
  "findings": [
    {{
      "file": "app/routes.py",
      "line": 88,
      "rule_id": "python.sqlalchemy.security.sqli",
      "true_severity": "Critical",
      "exploitability": "High -- user input flows directly into raw SQL query",
      "plain_english_explanation": "This line builds a SQL query using string formatting on user input, allowing an attacker to inject arbitrary SQL.",
      "suggested_fix": "Use parameterized queries via SQLAlchemy's text() with bound parameters instead of f-string interpolation.",
      "is_likely_false_positive": false
    }}
  ],
  "summary": "1 critical SQL injection vulnerability found; recommend blocking merge until fixed."
}}

Include one entry in "findings" for every finding listed above, in the same order. The "summary" field should be one or two sentences summarizing the overall triage result."""

    return prompt
