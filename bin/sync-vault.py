#!/usr/bin/env python3
"""
Sync published notes from the Obsidian vault into Quartz's content/.

Walks the vault, finds every .md whose front-matter contains `publish: true`,
copies it into content/ at the same relative path, and prunes anything in
content/ that no longer corresponds to a published source note.

Excluded folders are skipped entirely — `publish: true` inside them is ignored.

iCloud notes that are evicted (".icloud" placeholder) are force-downloaded via
`brctl download` before being read.

Usage:
    bin/sync-vault.py            # sync once
    bin/sync-vault.py --dry-run  # show what would change
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

VAULT = Path(
    "/Users/yjunho/Library/Mobile Documents/iCloud~md~obsidian/Documents/Claude"
)
REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"

EXCLUDED_DIRS = {".obsidian", ".trash", "daily", "_drafts", "_meta", "templates"}
EXCLUDED_FILES = {"CLAUDE.md"}


def ensure_icloud_downloaded(path: Path) -> Path:
    """If `path` is an iCloud placeholder (.icloud), trigger download and wait."""
    if path.name.startswith(".") and path.name.endswith(".icloud"):
        subprocess.run(["brctl", "download", str(path.parent)], check=False)
        real = path.parent / path.name[1:-len(".icloud")]
        for _ in range(50):
            if real.exists():
                return real
            import time
            time.sleep(0.1)
        return real
    return path


def parse_frontmatter(text: str) -> dict[str, str]:
    """Tiny YAML-ish front-matter parser. Only top-level scalar keys."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip("\n")
    out: dict[str, str] = {}
    for line in block.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        out[key.strip()] = val.strip().strip("\"'")
    return out


def is_published(md_path: Path) -> bool:
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return False
    fm = parse_frontmatter(text)
    return fm.get("publish", "").lower() == "true"


def walk_vault() -> list[Path]:
    """Return all .md paths in vault, skipping excluded dirs."""
    out: list[Path] = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".obsidian")]
        for name in files:
            if not name.endswith(".md"):
                continue
            if name in EXCLUDED_FILES:
                continue
            out.append(Path(root) / name)
    return out


def collect_assets_referenced(md_files: list[Path]) -> set[Path]:
    """Find image/file references via Obsidian wikilinks or markdown image syntax."""
    import re
    assets: set[Path] = set()
    wikilink = re.compile(r"!\[\[([^\]|#]+)")
    mdimg = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    for md in md_files:
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in wikilink.finditer(text):
            rel = m.group(1).strip()
            cand = (md.parent / rel).resolve() if "/" in rel else None
            if cand and cand.exists():
                assets.add(cand)
            else:
                for found in VAULT.rglob(rel):
                    assets.add(found)
                    break
        for m in mdimg.finditer(text):
            ref = m.group(1).strip().split()[0]
            if ref.startswith("http"):
                continue
            cand = (md.parent / ref).resolve()
            if cand.exists():
                assets.add(cand)
    return assets


def sync(dry_run: bool = False) -> int:
    if not VAULT.exists():
        print(f"ERROR: vault not found at {VAULT}", file=sys.stderr)
        return 1

    md_files = walk_vault()
    published = [p for p in md_files if is_published(p)]
    assets = collect_assets_referenced(published)

    wanted: dict[Path, Path] = {}
    for src in published:
        rel = src.relative_to(VAULT)
        wanted[CONTENT / rel] = src
    for src in assets:
        try:
            rel = src.relative_to(VAULT)
        except ValueError:
            continue
        wanted[CONTENT / rel] = src

    existing: set[Path] = set()
    if CONTENT.exists():
        for root, _dirs, files in os.walk(CONTENT):
            for name in files:
                if name == ".gitkeep":
                    continue
                existing.add(Path(root) / name)

    to_copy = []
    for dst, src in wanted.items():
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            to_copy.append((src, dst))
    to_delete = [p for p in existing if p not in wanted]

    print(f"vault: {len(md_files)} md files, {len(published)} published, {len(assets)} assets")
    print(f"plan: copy {len(to_copy)}, delete {len(to_delete)}")

    if dry_run:
        for src, dst in to_copy:
            print(f"  COPY   {src.relative_to(VAULT)}")
        for p in to_delete:
            print(f"  DELETE {p.relative_to(CONTENT)}")
        return 0

    for src, dst in to_copy:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for p in to_delete:
        p.unlink()
        try:
            p.parent.rmdir()
        except OSError:
            pass

    CONTENT.mkdir(exist_ok=True)
    gitkeep = CONTENT / ".gitkeep"
    if not any(CONTENT.iterdir()):
        gitkeep.touch()

    print("done")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(sync(dry_run=args.dry_run))
