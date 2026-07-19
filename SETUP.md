# SETUP.md — TriageIQ Setup Guide
 
This guide assumes you're comfortable with basic Git commands but new to
GitHub Actions / Secrets. Every step below is click-by-click.
 
---
 
## 1. Prerequisites
- A GitHub account
- A repo you can push to (this repo, or your own fork/copy of it)
- A Google Gemini API key (free tier is enough for light/demo use) —
  get one at https://aistudio.google.com/apikey
## 2. Push this repo to GitHub
 
If you haven't already pushed this project:
 
```bash
cd triageiq
git init
git add .
git commit -m "Initial commit: TriageIQ SAST pipeline"
git branch -M main
git remote add origin https://github.com/<your-username>/triageiq.git
git push -u origin main
```
 
## 3. Add your GEMINI_API_KEY as a GitHub Actions secret
 
This is the step most likely to trip people up — follow exactly:
 
1. Go to your repository on **github.com** (e.g. `github.com/<your-username>/triageiq`).
2. Click the **"Settings"** tab along the top of the repo page (it's near the
   right side, next to "Insights" — you need to be the repo owner/admin to see it).
3. In the left sidebar, scroll down to the **"Security"** section and click
   **"Secrets and variables"**.
4. Click **"Actions"** (this expands under "Secrets and variables").
5. You'll see tabs for "Secrets" and "Variables" — make sure **"Secrets"** is selected.
6. Click the green **"New repository secret"** button (top right of that page).
7. In the **"Name"** field, type exactly: `GEMINI_API_KEY`
8. In the **"Secret"** field, paste your Gemini API key (no quotes, no extra spaces).
9. Click **"Add secret"**.
You should now see `GEMINI_API_KEY` listed under "Repository secrets" (the
value itself is hidden — that's expected and correct).
 
> You do **not** need to manually add a `GITHUB_TOKEN` secret — GitHub
> automatically provides this to every workflow run.
 
## 4. Confirm the workflow file is in place
 
Check that `.github/workflows/sast.yml` exists in your pushed repo. On
GitHub.com, click the **"Code"** tab, then navigate `.github` → `workflows`
→ you should see `sast.yml` listed. If you don't see it, your `git push`
in step 2 may not have included it — run `git status` locally to check
for untracked files.
 
## 5. Trigger a test run
 
1. Create a new branch:
```bash
   git checkout -b test-triageiq
```
2. Make a small edit to `test_repo_samples/vulnerable_app.py` (or leave it
   as-is — it already contains intentional vulnerabilities for testing).
3. Commit and push the branch:
```bash
   git add .
   git commit -m "Test TriageIQ pipeline"
   git push -u origin test-triageiq
```
4. Go to your repo on GitHub.com. You should see a yellow banner: *"test-triageiq
   had recent pushes"* with a green **"Compare & pull request"** button. Click it.
5. On the "Open a pull request" page, confirm the base branch is `main`
   and the compare branch is `test-triageiq`, then click the green
   **"Create pull request"** button.
## 6. Watch it run
 
1. On the pull request page you just created, click the **"Checks"** tab
   (next to "Conversation", "Commits", "Files changed").
2. You'll see **"TriageIQ SAST Scan"** running (a yellow dot = in progress,
   green check = passed, red X = failed).
3. Click on it to see live logs from each step (`Run Semgrep`,
   `AI Triage + Post PR Comment`, `Fail on critical findings`).
4. Once it finishes, go back to the **"Conversation"** tab of the PR — you
   should see a new comment from `github-actions[bot]` titled
   **"🛡️ TriageIQ Security Triage"** listing the findings.
## 7. Confirm gating behavior
 
- `vulnerable_app.py` contains a SQL injection pattern that Gemini should
  flag as **Critical** — this should make the `Fail on critical findings`
  step show a red X.
- Fix the SQL injection (switch to a parameterized query), push again to
  the same branch, and confirm: the PR comment updates in place (same
  comment, not a new one), the Critical count drops to 0, and the check
  turns green even if lower-severity findings remain.
## 8. Troubleshooting
 
| Symptom | Likely cause |
|---|---|
| Workflow doesn't appear on the PR at all | `sast.yml` wasn't pushed, or it's not under `.github/workflows/` exactly |
| Step "AI Triage + Post PR Comment" fails immediately | `GEMINI_API_KEY` secret is missing or misspelled (must match exactly, case-sensitive) |
| PR comment never appears, but the workflow shows green | Check `permissions:` in `sast.yml` includes `pull-requests: write` |
| `pip install` fails locally when testing scripts on your machine | Use `python3 -m pip install -r requirements.txt`, not bare `pip` |
 
## 9. Local testing (optional, before pushing)
 
You can sanity-check the Python scripts locally without a real Gemini key
or GitHub context — they're written to fail gracefully and print a preview
instead of crashing when `GEMINI_API_KEY` / `GITHUB_TOKEN` aren't set.
 
```bash
cd scripts
python3 -m pip install -r ../requirements.txt
python3 -c "import gemini_client, prompt_builder, triage_engine, post_pr_comment, check_gate, run_semgrep; print('all modules import cleanly')"
```