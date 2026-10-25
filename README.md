# proctor

**An AI code reviewer you can run from a terminal.** Point it at a git diff and it tells you what's wrong — security
holes, silent data loss, regressions, mistakes the author didn't intend — in a shape you can act on.

**It only reports.** It never edits, commits, pushes, merges or approves anything; a human still merges.

![Licence: AGPL-3.0](https://img.shields.io/badge/licence-AGPL--3.0-blue) [![Buy Me a Coffee](https://raw.githubusercontent.com/casareanderson/.github/main/badges/bmc-yellow.svg)](https://buymeacoffee.com/iamc_tech)

`proctor` is the standalone code-review engine behind warden's PR reviewer. Part of the [warden family](#the-warden-family).

## What it does

```
$ git diff | proctor diff -

proctor — changes
The patch adds a shell call built from an untrusted filename.

  🔴 [app/upload.py:41] shell injection — subprocess.run(f"...{filename}...", shell=True) with an untrusted filename
  🟡 [app/upload.py] missing size cap — the file is read into memory with no limit
```

For every finding proctor names the file and line, then — the bit most AI reviewers skip — **checks itself against the
diff**:

- a finding that names a file not in the diff is **dropped** (a hallucination),
- a line outside that file's hunks is **cleared** (`line_unverified`),

so the output you act on only ever points at code that is actually in the patch.

## Why

Code-review models are cheap and fast, but they invent: they name a function that isn't in the diff, quote a line that
doesn't exist, flag a bug that isn't there. `proctor` is built around the one failure that matters — the file/line it
points at — and refuses to trust a finding it can't tie back to the diff.

It reviews the **diff only**: injection, secrets in code or logs, unsafe shell/docker/path handling, broken authz,
silent data loss, a regression, or a mistake the author clearly didn't intend. Style and nitpicks are ignored unless
they hide a bug.

## Verdicts

| Verdict | Meaning |
|---|---|
| `approve` | nothing worth reporting |
| `comment` | worth fixing, not blocking |
| `changes` | must not merge as-is |

Findings carry a `severity` (`high` / `med` / `low`), a `file`, a `line`, a short `title` and `why`.

## Install

```bash
git clone https://github.com/casareanderson/proctor.git
cd proctor
pip install requests   # the only dependency, used by `proctor pr`
```

## Use

```bash
# a diff from stdin
git diff | ./proctor diff -

# a diff file
./proctor diff path/to.patch

# fetch a PR from GitHub and review it
GITHUB_TOKEN=... ./proctor pr owner/repo#123
```

See [docs/EXAMPLES.md](docs/EXAMPLES.md) for a GitHub Actions recipe and [docs/SETUP.md](docs/SETUP.md) for the
endpoint/model configuration.

## Configuration

Any OpenAI-compatible endpoint works — OpenRouter, a local Ollama, etc.

```bash
export OPENROUTER_API_KEY=sk-or-...      # or MENTOR_API_KEY
export MENTOR_MODEL=qwen/qwen3.7-flash   # default
export MENTOR_URL=https://...            # override the endpoint base (default OpenRouter)
export GITHUB_TOKEN=...                  # only needed for `proctor pr`
```

## Limits (read these)

- **It's advisory.** `proctor` never merges, blocks or approves anything. It hands you a verdict; you decide.
- **It sees only the diff.** Context that isn't in the diff (the code around it, the ticket, intent) is invisible.
  That's deliberate — it keeps the review grounded — but a correct-looking change can still be wrong.
- **The model can still be wrong about *why*.** The fact-check catches wrong *files and lines*; it can't catch a
  wrong *judgement* on a real line. Read the `why`, don't rubber-stamp it.

## The warden family

| Tool | Watches | Runs as |
|---|---|---|
| [warden](https://github.com/casareanderson/warden) | Intrusions, bans, vulnerabilities, patches and AI agents | A server + web console |
| [sieve](https://github.com/casareanderson/sieve) | Known vulnerabilities + plain-text secrets | A CLI: `pipx install sieve-scan` |
| [ephor](https://github.com/casareanderson/ephor) | What AI agents connect to, download and can access | A dependency-free CLI |
| [farrier](https://github.com/casareanderson/farrier) | Applies the patches sieve finds, with your approval | A CLI |

## Licence

AGPL-3.0-or-later.
