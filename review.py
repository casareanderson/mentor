"""proctor — AI code review engine.

Reads a git diff and says what is wrong with it, in a shape a person can act on. It never edits, commits, pushes,
merges or approves anything — it only reports. The one place it can be wrong is by naming a file or line that is not
in the diff, so every finding is fact-checked against the diff before it is trusted (`check()`): a finding that names
a file not in the diff is dropped, and a line outside the file's hunks is cleared.

Standalone: no database, no warden config. Point it at any OpenAI-compatible endpoint with environment variables:
    MENTOR_URL / OPENROUTER_URL         endpoint base (default https://openrouter.ai/api/v1)
    MENTOR_MODEL                        model (default qwen/qwen3.7-flash)
    MENTOR_API_KEY / OPENROUTER_API_KEY the API key
"""
import json
import os
import re

SYSTEM = """You are proctor, a careful code reviewer for a small homelab/side-business estate.
You are given a git diff, and (usually) the pull request title and description for context. Review the DIFF ONLY for
things that would actually cause harm or surprise: security holes (injection, secrets in code or logs, unsafe
shell/docker/path handling, broken authz), silent data loss, a regression, or a mistake the author clearly did not
intend. Ignore style, naming and nitpicks unless they hide a bug. Say nothing that is not visible in the diff, and
name files exactly as they appear in the diff. If the diff is truncated, review only what you can see.

Reply with JSON only, no markdown fences, no commentary outside the JSON:
{"verdict": "approve" | "comment" | "changes",
 "summary": "one or two sentences",
 "findings": [{"severity": "high" | "med" | "low", "file": "path", "line": 0,
               "title": "short title", "why": "what is wrong and why it matters"}]}
"changes" = must not merge as-is; "comment" = worth fixing, not blocking; "approve" = nothing worth reporting.
A file or line you cannot determine may be empty / 0."""

VERDICT_EVENT = {"approve": "APPROVE", "comment": "COMMENT", "changes": "REQUEST_CHANGES"}
MAX_DIFF = 24000


def _cfg():
    url = os.environ.get("MENTOR_URL") or os.environ.get("OPENROUTER_URL") or "https://openrouter.ai/api/v1"
    model = os.environ.get("MENTOR_MODEL") or "qwen/qwen3.7-flash"
    key = os.environ.get("MENTOR_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or ""
    return url.rstrip("/") + "/chat/completions", model, key


def _parse(text):
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output: " + text[:120])
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                text = text[start:i + 1]
                break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fixed = re.sub(r",\s*([}\]])", r"\1", text).replace("\u201c", '"').replace("\u201d", '"')
        return json.loads(fixed)


def _diff_map(diff):
    files, ranges, cur = set(), {}, None
    for line in diff.splitlines():
        m = re.match(r"^diff --git a/(\S+) b/(\S+)", line)
        if m:
            cur = m.group(2); files.add(cur); continue
        m = re.match(r"^\+\+\+ b/(\S+)", line)
        if m:
            cur = m.group(1); files.add(cur); continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if m and cur:
            start = int(m.group(1))
            n = int(m.group(2)) if m.group(2) else 1
            ranges.setdefault(cur, []).append((start, start + n - 1))
    return files, ranges


def _matches(path, files):
    p = re.sub(r"^[ab]/", "", (path or "").strip().lstrip("/"))
    if not p:
        return False
    return p in files or any(f.endswith(p) for f in files if p) or any(p.endswith(f) for f in files if f)


def check(diff, findings):
    files, ranges = _diff_map(diff)
    kept, dropped = [], 0
    for f in findings:
        path = f.get("file") or ""
        if path and not _matches(path, files):
            dropped += 1
            continue
        line = f.get("line") or 0
        if path and line:
            p = re.sub(r"^[ab]/", "", path.strip().lstrip("/"))
            rs = ranges.get(p) or [rng for f_ in ranges if f_.endswith(p) for rng in ranges[f_]]
            if rs and not any(s <= line <= e for s, e in rs):
                f["line"] = 0
                f["line_unverified"] = True
        kept.append(f)
    return kept, dropped


def render_body(verdict, summary, findings):
    sev = {"high": "\U0001F534", "med": "\U0001F7E0", "low": "\U0001F7E1"}
    lines = ["_proctor \u00b7 AI code review (advisory)_", ""]
    if summary:
        lines += [summary.strip(), ""]
    for f in findings:
        loc = f.get("file") or "?"
        if f.get("line"):
            loc += f":{f['line']}"
        lines.append(f"- {sev.get(f.get('severity'), '\u2022')} **`{loc}`** \u2014 {f.get('title', '')}: {f.get('why', '')}")
    return "\n".join(lines)


def review(diff, title="", body="", url=None, model=None, key=None):
    import requests
    url = url or _cfg()[0]
    model = model or _cfg()[1]
    key = key if key is not None else _cfg()[2]
    ctx = []
    if title:
        ctx.append(f"PR title: {title}")
    if body:
        ctx.append(f"PR description: {body[:2000]}")
    text = ("\n".join(ctx) + "\n\n" if ctx else "") + (diff or "")[:MAX_DIFF]
    r = requests.post(url, timeout=120,
                      headers={"Authorization": "Bearer " + key} if key else {},
                      json={"model": model, "temperature": 0.1, "max_tokens": 2000,
                            "reasoning": {"enabled": False},
                            "messages": [{"role": "system", "content": SYSTEM},
                                         {"role": "user", "content": text}]})
    r.raise_for_status()
    out = (r.json()["choices"][0].get("message") or {}).get("content") or ""
    out = re.sub(r"(?s)<think>.*?</think>", "", out).strip()
    d = _parse(out)
    d.setdefault("verdict", "comment")
    d.setdefault("summary", "")
    d.setdefault("findings", [])
    d["model"] = model
    return d
