#!/usr/bin/env python3
"""Fail if the repo contains things that must never be committed: tokens, e-mail addresses, or
real workspace/item GUIDs (only the all-zero placeholder GUID is allowed).

It scans what git would commit: every path .gitignore excludes is skipped (config.yaml, schema/,
captures/, your '*.Report/' working folders ...), so a configured checkout still passes.

Usage: python3 tools/secret_scan.py [folder]   -> exit code 1 on any hit
Adapt WHITELIST if your fork legitimately needs an address or an id in the docs.
"""
import fnmatch, pathlib, re, sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
GUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOKEN = re.compile(r"(eyJ[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})")
WHITELIST = {"00000000-0000-0000-0000-000000000000", "noreply@github.com"}
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
TEXT_EXT = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".dax", ".pbir", ".platform", ".toml", ".cfg", ".ini", ""}
GITIGNORE = [l.strip() for l in (ROOT / ".gitignore").read_text().splitlines()
             if l.strip() and not l.startswith("#")] if (ROOT / ".gitignore").exists() else []


def ignored(rel: pathlib.Path) -> bool:
    """Minimal .gitignore: a pattern matches the whole relative path or any one path segment; a
    leading '!' un-ignores; a trailing '/' is dropped. Enough for this repo's .gitignore."""
    hit = False
    for pat in GITIGNORE:
        p = pat.lstrip("!").rstrip("/")
        if fnmatch.fnmatch(rel.as_posix(), p) or any(fnmatch.fnmatch(seg, p) for seg in rel.parts):
            hit = not pat.startswith("!")
    return hit


hits = 0
for p in ROOT.rglob("*"):
    if not p.is_file() or any(part in SKIP_DIRS for part in p.parts): continue
    if p.suffix.lower() not in TEXT_EXT or ignored(p.relative_to(ROOT)): continue
    try:
        text = p.read_text(errors="ignore")
    except Exception:
        continue
    for m in GUID.findall(text):
        if m.lower() not in WHITELIST:
            hits += 1; print(f"{p}: GUID {m}")
    for m in EMAIL.findall(text):
        if m not in WHITELIST:
            hits += 1; print(f"{p}: EMAIL {m}")
    for m in TOKEN.findall(text):
        hits += 1; print(f"{p}: TOKEN-LIKE {m[:10]}...")
print("secret_scan hits:", hits)
sys.exit(1 if hits else 0)
