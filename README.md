# younjunho17-web.github.io

[Quartz 4](https://quartz.jzhao.xyz/)로 빌드되는 개인 위키.
소스 노트는 별도 Obsidian vault에 있고, `publish: true` 가 켜진 것만 `content/`로 동기화돼 GitHub Pages로 배포된다.

- Live: https://younjunho17-web.github.io
- Vault: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Claude/`
- 기존 Leperche 사이트: `leperche-archive` 브랜치

## Workflow

1. Obsidian에서 노트 작성 — vault에 모든 것이 살고, 일부만 `publish: true`
2. 게시 준비됐으면:
   ```bash
   bin/sync-vault.py            # vault → content/ 동기화
   git add content && git commit -m "publish: ..."
   git push
   ```
3. GitHub Action이 `npx quartz build` 후 Pages로 배포

`bin/sync-vault.py --dry-run` 으로 무엇이 바뀔지 먼저 확인 가능.

## Local preview

```bash
bin/sync-vault.py
npx quartz build --serve     # http://localhost:8080
```

## Vault 규약

vault 루트의 `CLAUDE.md` 참고. 요약:

- Front-matter `publish: true` 인 노트만 사이트로 나감
- `daily/`, `_drafts/`, `_meta/`, `templates/` 폴더는 통째로 제외
- 카테고리: `radiology`, `pathology`, `infectious-disease`, `career`
