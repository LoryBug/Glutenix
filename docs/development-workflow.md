# Development Workflow

This workflow keeps Glutenix traceable without making small changes bureaucratic.

## 1. Plan Before Building

Use a parent issue for work that changes architecture, scientific assumptions, datasets, APIs, or several files.

The parent issue should capture:

- Goal.
- Why it matters.
- Non-goals.
- Proposed sub-issues.
- Risks and tradeoffs.
- Completion criteria.

Small obvious fixes can skip the parent issue and use a single implementation issue.

## 2. Create Implementation Issues

Each implementation issue should be clear enough that a smaller model or future contributor can start safely.

It should include:

- Goal.
- Context.
- Implementation notes.
- Watch-out section.
- Acceptance criteria.
- Validation commands.

Prefer several small issues over one vague large issue.

## 3. Branch Per Issue

Use one branch per issue.

Suggested names:

- `feat/123-literature-coverage`
- `fix/124-confidence-warning`
- `cleanup/130-calibration-modules`
- `docs/131-evidence-map`

## 4. Commit Style

Keep commits small and factual.

Recommended examples:

- `feat: add coverage endpoint refs #123`
- `test: cover OOD warning flags refs #123`
- `docs: record coverage limitations refs #123`

Use `Closes #123` in the PR description when the issue is fully implemented.

## 5. Pull Request And Light Review

Every feature branch should return through a PR.

The default review is intentionally light and bug-focused:

- Does it satisfy the issue?
- Are there obvious bugs or regressions?
- Are tests adequate for the risk?
- Are evidence/data limitations documented?
- Is the change small enough to merge safely?

If the review finds broader design debt, open a cleanup issue instead of expanding the PR.

## 6. Periodic Cleanup

Open a cleanup issue after roughly 5-8 feature issues, or earlier if these signals appear:

- duplicated logic
- unclear module boundaries
- fragile tests
- stale docs
- API responses growing inconsistently
- calibration or confidence logic becoming hard to reason about

Cleanup issues should preserve behavior unless they explicitly state otherwise.

## 7. Durable Decisions

Issues and PRs explain day-to-day work. For decisions that should remain in the repository, add a short ADR in `docs/adr/`.

Use an ADR when a choice is:

- architectural
- scientific/modeling-related
- hard to reverse
- likely to be questioned later

Do not write ADRs for every task.

## Suggested Labels

Minimal label set:

- `type: plan`
- `type: feature`
- `type: bug`
- `type: cleanup`
- `type: docs`
- `area: calibration`
- `area: engine`
- `area: api`
- `area: frontend`
- `area: data`
- `risk: low`
- `risk: medium`
- `risk: high`

Labels are useful, but issue content is the source of truth.

## Definition Of Done

An issue is done when:

- acceptance criteria are satisfied
- tests/builds relevant to the change pass
- docs are updated if behavior, data, evidence, or API contracts changed
- generated docs are refreshed or checked with `uv run python scripts/validate_doc_counts.py` when literature data or citation metadata changes
- follow-up work is captured as issues, not left only in chat
- the PR has had a light bug-focused review
