# CLAUDE.md

## 0. 프로젝트 대원칙: 아트메이트(ArtMate)

2022 개정 미술과 교육과정 기반 초·중등 미술 학습 도우미 에이전트 (Gemini + 랭체인/랭그래프 + 스트림릿).

- **문서 우선**: `spec.md`(What) → `design.md`(How) → `tasks.md`(순서). 작업 전 해당 태스크와 관련 절을 먼저 읽는다.
- **한 번에 한 태스크**: `tasks.md`의 지정된 태스크만 수행한다. 현재 마일스톤 밖의 기능은 만들지 않는다.
- **항상 실행 가능**: 태스크가 끝나면 `streamlit run app.py`가 동작해야 하며, 확인 포인트 점검 방법을 보고한다.
- **문서와 다르면 멈춤**: 설계와 다른 판단이 필요하면 구현 전에 제안하고, 승인 후 문서를 먼저 고친다.
- **단순성 상한**: 최종 구조는 노드 5개, 도구 3개를 넘지 않는다.
- **안전**: API 키는 `.env`에만 둔다. 학생 대화·이미지를 파일이나 DB에 저장하지 않는다.
- **파일 삭제 전 반드시 확인**을 받는다.
- **환경·언어**: Windows, venv, PowerShell 기준 명령. 응답과 코드 주석은 한국어로 간결하게.
- **API 호출 절약**: 무료 사용량 한도가 있으므로, 태스크 점검을 위한 실제 Gemini 호출은 3회 이내로 하고 나머지 점검은 사용자에게 맡긴다.

- **태스크 완료 보고**: 태스크를 끝내면 아래 형식으로 보고한다.
  ## T○ 결과 보고
  - 변경 파일:
  - 구현 요약(3줄 이내):
  - 설계와 다르게 한 점·가정:
  - 실행 방법:
  - 확인 포인트별 점검 방법:
  - 사용자가 해야 할 일:

---

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
