# Contributing

5인 팀 공모전 저장소의 협업 규칙이다. 사람 기여자와 AI 에이전트(Claude · Codex 등) 작업 모두 동일 규칙을 따른다.

## 작업 흐름

`main` pull → 작업 브랜치 생성 → commit → push → PR → 리뷰 → merge.
`main`에 직접 push 하지 않는다. merge는 팀 확인 후 수행한다.

## 브랜치 네이밍

`<type>/<short-topic>` 형식 (예: `feat/mundlak-oos`, `docs/readme-structure`).
AI 에이전트도 `claude/*`·`codex/*` 같은 임의 브랜치를 만들지 않고 위 규칙을 따른다.

## 커밋 메시지

[Conventional Commits](https://www.conventionalcommits.org)를 따른다: `feat` · `fix` · `docs` · `refactor` · `chore`.

## Pull Request

무엇을 · 왜 · 리뷰 포인트만 간단히 적는다. 결과 수치를 바꾸는 PR은 해당 산출표(`results/tables/`)를 재생성한 근거를 함께 남긴다.

## 데이터 취급 (필수)

- **KYHPS 원자료·가공자료(`data/raw/`, `data/processed/`)는 절대 커밋하지 않는다.** 승인 기반 제한자료이며 재배포가 금지된다(→ [`data/README.md`](data/README.md)).
- `*.csv`·`*.sav`·`*.dta` 등 개인단위 데이터가 스테이징에 포함되지 않았는지 커밋 전 확인한다(`.gitignore`로 1차 차단).
- 노트북은 출력 셀을 지운 뒤 커밋한다(데이터 미리보기 유출 방지).
