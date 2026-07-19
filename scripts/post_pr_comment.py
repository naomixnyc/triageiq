"""
post_pr_comment.py
Formats the parsed triage result into a Markdown PR comment and
posts it to the pull request, editing a prior TriageIQ comment in
place (identified by a hidden HTML marker) instead of spamming a
new comment on every push.
"""

import os
import sys

HIDDEN_MARKER = "<!-- triageiq-bot -->"

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
SEVERITY_EMOJI = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵"}


def _sort_key(finding: dict):
    return SEVERITY_ORDER.get(finding.get("true_severity", "Low"), 4)


def format_comment_body(triage_result: dict, total_raw_findings: int = None) -> str:
    """
    Builds the Markdown PR comment body from the parsed triage result.
    """
    findings = triage_result.get("findings", [])
    summary = triage_result.get("summary", "")
    ai_failed = triage_result.get("ai_triage_failed", False)

    kept = [f for f in findings if not f.get("is_likely_false_positive", False)]
    filtered_out = [f for f in findings if f.get("is_likely_false_positive", False)]
    kept.sort(key=_sort_key)

    critical = [f for f in kept if f.get("true_severity") == "Critical"]
    high = [f for f in kept if f.get("true_severity") == "High"]
    medium_low = [f for f in kept if f.get("true_severity") in ("Medium", "Low")]

    raw_count = total_raw_findings if total_raw_findings is not None else len(findings)
    headline_parts = []
    if critical:
        headline_parts.append(f"{len(critical)} Critical")
    if high:
        headline_parts.append(f"{len(high)} High")
    if medium_low:
        headline_parts.append(f"{len(medium_low)} Low/Medium")
    headline = ", ".join(headline_parts) if headline_parts else "No actionable findings"

    lines = []
    lines.append(f"## 🛡️ TriageIQ Security Triage — {headline} (filtered from {raw_count} raw findings)")
    lines.append("")

    if ai_failed:
        lines.append("> ⚠️ **AI triage step failed** — showing raw Semgrep results without re-ranking. See the Actions log for details.")
        lines.append("")

    if summary:
        lines.append(f"_{summary}_")
        lines.append("")

    # Critical + High get full detail inline.
    for finding in critical + high:
        emoji = SEVERITY_EMOJI.get(finding.get("true_severity"), "⚪")
        lines.append(f"### {emoji} {finding.get('true_severity')}: {finding.get('rule_id')}")
        lines.append(f"**`{finding.get('file')}:{finding.get('line')}`**")
        lines.append(finding.get("plain_english_explanation", ""))
        lines.append(f"**Fix:** {finding.get('suggested_fix', '')}")
        lines.append("")

    if medium_low:
        lines.append("<details>")
        lines.append(f"<summary>{len(medium_low)} low/medium-severity finding(s) (click to expand)</summary>")
        lines.append("")
        for finding in medium_low:
            lines.append(
                f"- `{finding.get('file')}:{finding.get('line')}` — "
                f"{finding.get('plain_english_explanation', '')} "
                f"({finding.get('true_severity')})"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if filtered_out:
        lines.append("<details>")
        lines.append(
            f"<summary>{len(filtered_out)} finding(s) filtered as low-confidence/false-positive by AI triage</summary>"
        )
        lines.append("")
        lines.append(
            f"Semgrep flagged {len(filtered_out)} additional item(s) that TriageIQ's AI triage assessed as "
            "low real-world exploitability given code context. See the full Semgrep report in the Actions log for details."
        )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if not critical and not high and not medium_low and not filtered_out:
        lines.append("No issues found. ✅")
        lines.append("")

    lines.append(HIDDEN_MARKER)
    return "\n".join(lines)


def post_or_update_comment(triage_result: dict):
    """
    Posts the formatted comment to the current PR, editing a prior
    TriageIQ comment in place if one exists. No-ops (with a printed
    message) if the required GitHub env vars aren't set, so this script
    can also be run locally/in tests without a GitHub context.
    """
    github_token = os.environ.get("GITHUB_TOKEN", "")
    repo_name = os.environ.get("REPO", "")
    pr_number_raw = os.environ.get("PR_NUMBER", "")

    body = format_comment_body(triage_result)

    if not (github_token and repo_name and pr_number_raw):
        print("[post_pr_comment] Missing GITHUB_TOKEN/REPO/PR_NUMBER; skipping actual PR post.")
        print("[post_pr_comment] --- comment preview ---")
        print(body)
        print("[post_pr_comment] --- end preview ---")
        return

    try:
        pr_number = int(pr_number_raw)
    except ValueError:
        print(f"[post_pr_comment] Invalid PR_NUMBER '{pr_number_raw}'; skipping PR post.", file=sys.stderr)
        return

    try:
        from github import Github
    except ImportError:
        print("[post_pr_comment] PyGithub not installed; skipping actual PR post.", file=sys.stderr)
        print(body)
        return

    gh = Github(github_token)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    existing_comment = None
    for comment in pr.get_issue_comments():
        if HIDDEN_MARKER in (comment.body or ""):
            existing_comment = comment
            break

    if existing_comment:
        existing_comment.edit(body)
        print(f"[post_pr_comment] Updated existing TriageIQ comment on PR #{pr_number}.")
    else:
        pr.create_issue_comment(body)
        print(f"[post_pr_comment] Posted new TriageIQ comment on PR #{pr_number}.")
