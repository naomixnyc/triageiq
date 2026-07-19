"""
vulnerable_app.py

⚠️ DEMO-ONLY FILE. ⚠️
This file intentionally contains insecure code patterns so TriageIQ has
something realistic to scan and triage for demo/portfolio purposes.
Do NOT copy these patterns into real applications.

Intentional vulnerabilities included:
  1. SQL injection via string formatting (line ~24)
  2. Hardcoded secret / API key (line ~10)
  3. Unsanitized eval() of user input (line ~34)

Note: the original ruleset config (p/security-audit + p/owasp-top-ten only)
caught only #3 on first test. See ../LEARNINGS.md for why, and what
changed (added p/python + p/secrets rulesets).
"""

import sqlite3

# --- 2. Hardcoded secret (intentional, for demo) ---------------------------
API_KEY = "sk_live_51Hc8T2eZvKYlo2C0demoKEYdoNOTuse0000000000"  # noqa: S105


def get_user_by_username(username: str):
    """
    --- 1. SQL injection via string formatting (intentional, for demo) ---
    User input is interpolated directly into the SQL string instead of
    using parameterized queries, allowing arbitrary SQL injection.
    """
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()


def run_user_expression(expr: str):
    """
    --- 3. Unsanitized eval() (intentional, for demo) ---
    Directly evaluates a user-supplied expression string, allowing
    arbitrary code execution.
    """
    result = eval(expr)  # noqa: S307
    return result


if __name__ == "__main__":
    # Example (unsafe) usage -- demo only.
    print(get_user_by_username("alice"))
    print(run_user_expression("2 + 2"))
# a comment
