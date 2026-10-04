# younjunho17-web.github.io

Jekyll 블로그 (Twenty Ten 스타일). 글은 Obsidian `Blog` vault에서 쓰고, 이 repo로는 퍼블리시만 한다.

- Live: https://younjunho17-web.github.io
- Vault: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Blog/`
- 이전 사이트: `quartz-archive`(Quartz 위키), `leperche-archive` 브랜치

## 글 쓰기 → 게시

1. Obsidian `Blog` vault에서 노트 작성. Properties(front matter)는 전부 선택:
   ```yaml
   title: 제목            # 없으면 파일명
   date: 2026-10-04 15:30 # 없으면 파일 생성 시각
   categories: [일상]
   tags: [a, b]
   slug: english-url      # 없으면 파일명이 주소가 됨
   draft: true            # 게시 제외
   ```
   쓰는 중인 글은 `_drafts/` 폴더에 두거나 `draft: true`. 본문의 `<!--more-->` 위까지만 첫 화면에 나온다.
2. 게시: `bin/publish.py` (vault → `_posts/` 변환 + commit + push). 1~2분 뒤 반영.

`_posts/`와 `assets/posts/`는 매번 vault에서 새로 만들어지므로 손으로 고치지 않는다.

## 로컬 미리보기

```bash
bin/publish.py --no-push
PATH=/opt/homebrew/opt/ruby/bin:$PATH bundle exec jekyll serve   # http://localhost:4000
```

## 꾸미기

- 색·폰트: `assets/style.css` 맨 위 `:root` 변수
- 헤더 사진: `assets/header.jpg` 교체 (940×198 비율)
- 사이트 제목·태그라인·Blogroll: `_config.yml`
