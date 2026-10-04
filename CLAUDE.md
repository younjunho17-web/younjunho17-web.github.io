# 블로그 repo

Jekyll 3.10 블로그(Twenty Ten 스타일), GitHub Actions(`actions/jekyll-build-pages`)로 Pages 배포. 사용법은 README.md.

- 원본은 Obsidian `Blog` vault. `_posts/`, `assets/posts/`는 `bin/publish.py`가 생성하는 산출물이라 직접 편집 금지.
- 변환 규칙을 바꾸면 `bin/publish.py --selftest`를 갱신·통과시킨다.
- 로컬 Ruby는 Homebrew Ruby 4 — github-pages gem 미지원이라 Gemfile은 jekyll 3.10을 직접 지정(배포에는 안 쓰임).
- 카피는 plain·functional. 문장 중간 이탤릭 금지.
