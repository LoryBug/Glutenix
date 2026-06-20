# Agent Instructions

This repository uses a lightweight planning and traceability workflow. Follow it by default unless the user explicitly asks for a faster one-off change.

## Default Workflow

For substantial work, use this sequence:

1. Discuss and refine the plan before implementation.
2. Use a parent issue for broad feature areas, architectural changes, scientific/modeling decisions, datasets, APIs, or multi-step work.
3. Break approved plans into implementation issues that include goal, context, implementation notes, watch-outs, acceptance criteria, and validation.
4. Implement each issue on a dedicated feature branch.
5. Return through a PR with a light bug-focused review.
6. Open cleanup issues after accumulated feature work when duplication, unclear boundaries, stale docs, or fragile tests appear.

The detailed workflow lives in `docs/development-workflow.md`.

## When To Stay Lightweight

Do not over-process tiny changes.

Use a direct small change when the task is clearly scoped, low risk, and does not affect architecture, public API, data semantics, calibration logic, or scientific interpretation.

If unsure, ask one short clarification question or propose the smallest useful issue split.

## Issues And Templates

Use these GitHub templates:

- Parent plans: `.github/ISSUE_TEMPLATE/parent-plan.yml`
- Implementation tasks: `.github/ISSUE_TEMPLATE/implementation-task.yml`
- Cleanup work: `.github/ISSUE_TEMPLATE/cleanup.yml`
- Bugs: `.github/ISSUE_TEMPLATE/bug.yml`

Implementation issues should be clear enough for a smaller model or future contributor to execute safely.

## Branches And Commits

Use one branch per issue when working through the full workflow.

Suggested branch names:

- `feat/123-short-description`
- `fix/123-short-description`
- `cleanup/123-short-description`
- `docs/123-short-description`

Use small factual commits. Prefer messages like:

- `feat: add coverage endpoint refs #123`
- `test: cover OOD warning flags refs #123`
- `docs: record coverage limitations refs #123`

## Reviews

Default review style is light and bug-focused:

- Does the change satisfy the issue acceptance criteria?
- Are there obvious bugs or behavioral regressions?
- Are tests adequate for the risk?
- Are evidence, calibration, and data limitations documented when relevant?
- Is follow-up cleanup needed instead of expanding the current PR?

Use `.github/pull_request_template.md` for PRs.

## ADRs

Use ADRs only for durable decisions that should remain in the repository.

Good ADR candidates:

- calibration strategy changes
- model confidence semantics
- data provenance rules
- major API contracts
- architecture/module boundaries

ADR files live in `docs/adr/`; start from `docs/adr/0000-template.md`.

## Validation

Before finishing implementation work, run the relevant checks:

- Backend: `uv run pytest -q`
- Frontend/API-contract changes: `npm run build` in `frontend/`
- Docs/template-only changes: at minimum inspect diff and run `git diff --check`

If a check is skipped, state why.
