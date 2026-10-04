#!/usr/bin/env python3
"""
Obsidian 'Blog' vault → Jekyll _posts/ 로 옮기고 GitHub에 push한다.

vault가 원본이다. _posts/ 와 assets/posts/ 는 매번 통째로 다시 만든다
(vault에서 지운 글은 블로그에서도 사라진다).

게시 규칙
- vault 안의 모든 .md가 글이 된다. 단 다음은 제외:
  `draft: true`, 본문이 빈 노트, 이름이 `.` 또는 `_`로 시작하는 폴더(_drafts 등),
  templates/ 폴더.
- front matter(Obsidian Properties): title, date, categories, tags, slug — 모두 선택.
  title 없으면 파일명, date 없으면 파일 생성 시각, slug 없으면 파일명.
- [[노트]]·[[노트|별칭]]은 게시된 글끼리 링크로, 게시 안 된 노트면 글자만 남긴다.
  ![[그림.png]]·![[그림.png|300]]은 assets/posts/로 복사해 이미지로.
  ==하이라이트==는 <mark>, %%주석%%은 지운다(블로그에 안 나감).

Usage:
    bin/publish.py             # 변환 + commit + push
    bin/publish.py --no-push   # 변환만 (로컬 미리보기용)
    bin/publish.py --selftest  # 변환 규칙 자체 점검
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

VAULT = Path("/Users/yjunho/Library/Mobile Documents/iCloud~md~obsidian/Documents/Blog")
REPO = Path(__file__).resolve().parent.parent
POSTS = REPO / "_posts"
ASSETS = REPO / "assets" / "posts"
ASSET_URL = "/assets/posts/"
SKIP_DIRS = {"templates"}

EMBED = re.compile(r"!\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(?:\|([^\]]*))?\]\]")
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\((?!https?://|/)([^)\s]+)\)")
HIGHLIGHT = re.compile(r"==(?=\S)(.+?)(?<=\S)==")
COMMENT = re.compile(r"%%.*?%%", re.S)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"}


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Obsidian Properties 수준의 YAML만 읽는다: 스칼라, [a, b], '- a' 블록 리스트."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    end = 3 if text.startswith("---\n---") else text.find("\n---", 4)
    if end < 0:
        return {}, text
    meta: dict = {}
    key = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        m = re.match(r"^\s*-\s+(.*)$", line)
        if m and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(m.group(1).strip().strip("\"'"))
            continue
        k, _, v = line.partition(":")
        key, v = k.strip(), re.sub(r"\s+#.*$", "", v).strip()
        if v.startswith("[") and v.endswith("]"):
            meta[key] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        elif v:
            meta[key] = v.strip("\"'")
        else:
            meta[key] = []
    body = text[end + 4:]
    return meta, body.split("\n", 1)[1] if "\n" in body else ""


def as_list(v) -> list[str]:
    if not v:
        return []
    return v if isinstance(v, list) else [x.strip() for x in v.split(",") if x.strip()]


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.U).strip().lower()
    return re.sub(r"[\s_]+", "-", s) or "post"


def parse_date(v: str | None, fallback: datetime) -> datetime:
    if v:
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                pass
        print(f"  ! date 형식을 못 읽음: {v!r} — 파일 생성 시각으로 대체", file=sys.stderr)
    return fallback


def convert(body: str, links: dict[str, str], assets: dict[str, Path], used: set[Path]) -> str:
    """Obsidian 문법 → kramdown. links: 노트 이름(소문자) → URL, assets: 파일명 → 경로."""
    body = COMMENT.sub("", body)
    body = body.split("%%", 1)[0]  # 닫히지 않은 %%는 Obsidian처럼 끝까지 숨긴다

    def embed(m):
        name, opt = m.group(1).strip(), (m.group(2) or "").strip()
        src = assets.get(unicodedata.normalize("NFC", Path(name).name))
        if src and src.suffix.lower() in IMAGE_EXT:
            used.add(src)
            size = re.fullmatch(r"(\d+)(?:x\d+)?", opt)
            width = f'{{: width="{size.group(1)}"}}' if size else ""
            return f"![{'' if size else opt}]({ASSET_URL}{quote(src.name)}){width}"
        return wikilink(re.match(WIKILINK, m.group(0)[1:]))

    def wikilink(m):
        name, alias = m.group(1).strip(), m.group(3)
        key = Path(name).name
        key = key[:-3] if key.endswith(".md") else key
        text = (alias or key).strip()
        url = links.get(key.lower())
        return f"[{text}]({url})" if url else text

    def md_image(m):
        src = assets.get(unicodedata.normalize("NFC", Path(unquote(m.group(2))).name))
        if not src:
            return m.group(0)
        used.add(src)
        return f"![{m.group(1)}]({ASSET_URL}{quote(src.name)})"

    body = EMBED.sub(embed, body)
    body = WIKILINK.sub(wikilink, body)
    body = MD_IMAGE.sub(md_image, body)
    body = HIGHLIGHT.sub(r"<mark>\1</mark>", body)
    # Jekyll이 본문의 {{ }}·{% %}를 Liquid로 해석하지 않게 하나씩 감싼다
    return re.sub(r"\{[{%]", lambda m: "{% raw %}" + m.group(0) + "{% endraw %}", body)


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def collect():
    if not VAULT.exists():
        sys.exit(f"vault가 없습니다: {VAULT}")
    subprocess.run(["brctl", "download", str(VAULT)], check=False, capture_output=True)

    notes, assets = [], {}
    for p in sorted(VAULT.rglob("*")):
        rel = p.relative_to(VAULT)
        if any(part.startswith((".", "_")) or part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if p.name.endswith(".icloud"):
            print(f"  ! iCloud에서 아직 안 내려온 파일: {rel}", file=sys.stderr)
        elif p.suffix == ".md":
            notes.append(p)
        elif p.is_file() and not p.name.startswith("."):
            name = unicodedata.normalize("NFC", p.name)
            if name in assets:
                print(f"  ! 같은 이름의 파일이 둘: {rel} — 하나만 쓰입니다", file=sys.stderr)
            assets[name] = p

    posts = []
    for p in notes:
        # macOS·iCloud 파일명은 NFD일 수 있어 URL이 어긋나지 않게 NFC로 통일
        text = unicodedata.normalize("NFC", p.read_text(encoding="utf-8"))
        stem = unicodedata.normalize("NFC", p.stem)
        meta, body = split_frontmatter(text)
        if str(meta.get("draft", "")).lower() in ("true", "yes", "1") or not body.strip():
            continue
        date = parse_date(meta.get("date"), datetime.fromtimestamp(p.stat().st_birthtime))
        slug = slugify(meta.get("slug") or stem)
        posts.append({
            "src": p, "body": body, "date": date, "slug": slug,
            "title": meta.get("title") or stem, "stem": stem,
            "categories": as_list(meta.get("categories") or meta.get("category")),
            "tags": as_list(meta.get("tags")),
            "url": f"/{date:%Y/%m/%d}/{quote(slug)}/",
        })
    return posts, assets


def build() -> int:
    posts, assets = collect()
    links = {p["stem"].lower(): p["url"] for p in posts}
    links.update({p["title"].lower(): p["url"] for p in posts})

    shutil.rmtree(POSTS, ignore_errors=True)
    shutil.rmtree(ASSETS, ignore_errors=True)
    POSTS.mkdir()
    used: set[Path] = set()
    seen: dict[str, Path] = {}
    for p in posts:
        name = f"{p['date']:%Y-%m-%d}-{p['slug']}.md"
        if name in seen:
            sys.exit(f"같은 날짜·slug 글이 둘: {seen[name].name}, {p['src'].name} — slug를 다르게 지정하세요")
        seen[name] = p["src"]
        fm = [
            "---",
            f"title: {yaml_str(p['title'])}",
            f"date: {p['date']:%Y-%m-%d %H:%M:%S} +0900",
            f"categories: [{', '.join(yaml_str(c) for c in p['categories'])}]",
            f"tags: [{', '.join(yaml_str(t) for t in p['tags'])}]",
            "layout: post",
            "---",
            "",
        ]
        out = POSTS / name
        out.write_text("\n".join(fm) + convert(p["body"], links, assets, used), encoding="utf-8")
        print(f"  {out.name}")
    if used:
        ASSETS.mkdir(parents=True)
        for src in used:
            shutil.copy2(src, ASSETS / src.name)
    print(f"{len(posts)}개 글, 그림 {len(used)}개")
    return len(posts)


def push(n: int) -> None:
    git = ["git", "-C", str(REPO)]
    subprocess.run(git + ["add", "-A", "_posts", "assets"], check=True)
    if subprocess.run(git + ["diff", "--cached", "--quiet"]).returncode == 0:
        print("바뀐 글이 없습니다.")
        return
    subprocess.run(git + ["commit", "-q", "-m", f"publish: {n} posts ({datetime.now():%Y-%m-%d %H:%M})"], check=True)
    subprocess.run(git + ["push", "-q"], check=True)
    print("push 완료 — 1~2분 뒤 https://younjunho17-web.github.io 에 반영됩니다.")


def selftest() -> None:
    meta, body = split_frontmatter("---\ntitle: 안녕\ntags: [a, b]\ncategories:\n  - 일상\n---\n본문\n")
    assert meta == {"title": "안녕", "tags": ["a", "b"], "categories": ["일상"]}, meta
    assert body == "본문\n", repr(body)
    links = {"첫 글": "/2026/10/04/첫-글/"}
    img = Path("/v/attachments/Pasted image 1.png")
    used: set[Path] = set()
    out = convert(
        "[[첫 글]] [[첫 글|여기]] [[비공개]] ![[Pasted image 1.png|300]] ==강조== %%비밀%%끝",
        links, {img.name: img}, used,
    )
    assert out == (
        "[첫 글](/2026/10/04/첫-글/) [여기](/2026/10/04/첫-글/) 비공개 "
        '![](/assets/posts/Pasted%20image%201.png){: width="300"} <mark>강조</mark> 끝'
    ), out
    assert used == {img}
    assert convert("{{ x }}", {}, {}, set()) == "{% raw %}{{{% endraw %} x }}"
    # 초안이 새지 않아야 하는 입력들
    assert split_frontmatter("\ufeff---\r\ndraft: true # wip\r\n---\r\n비밀")[0] == {"draft": "true"}
    assert split_frontmatter("---\ntags:\n- a\n---\nx")[0] == {"tags": ["a"]}
    assert convert("보임 %% 안 닫힌\n비밀", {}, {}, set()) == "보임 "
    assert convert("[[dir/첫 글.md]]", links, {}, set()) == "[첫 글](/2026/10/04/첫-글/)"
    kimg = Path("/v/사진.png")
    assert convert("![](att/%EC%82%AC%EC%A7%84.png)", {}, {"사진.png": kimg}, set()) == "![](/assets/posts/%EC%82%AC%EC%A7%84.png)"
    assert slugify("Hello, World!") == "hello-world" and slugify("첫 글") == "첫-글"
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        n = build()
        if not a.no_push:
            push(n)
