# mentor

An AI code reviewer you can run from a terminal. Point it at a git diff and it tells you what's wrong — security
holes, silent data loss, regressions, mistakes the author didn't intend — in a shape you can act on.

**It only reports.** It never edits, commits, pushes, merges or approves anything. A human still merges.

`mentor` is the standalone version of the code-review engine behind warden's review collector.

## Install

```bash
git clone https://github.com/casareanderson/mentor.git
cd mentor
pip install requests
```

## Use

```bash
# review a diff from stdin
git diff | ./mentor diff -

# review a diff file
./mentor diff path/to.patch

# fetch a PR from GitHub and review it
GITHUB_TOKEN=... ./mentor pr owner/repo#123
```

Environment variables (any OpenAI-compatible endpoint works — OpenRouter, a local Ollama, etc.):

```bash
export OPENROUTER_API_KEY=sk-or-...   # or MENTOR_API_KEY
export MENTOR_MODEL=qwen/qwen3.7-flash
```

## What it does

1. Sends the diff (plus the PR title/description if you gave one) to the model.
2. Parses the verdict — `approve`, `comment`, or `changes` — and a list of findings.
3. **Fact-checks every finding against the diff.** A finding that names a file not in the diff is dropped; a line
   outside that file's hunks is cleared. This is the one way a model can be confidently wrong, so it's never trusted.

## Licence

AGPL-3.0.
