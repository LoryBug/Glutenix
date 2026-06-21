# Documentation Classification

This document records the public/private boundary for Glutenix documentation. It is an audit trail for issue #78 and a maintenance guide for future documentation work.

## Policy

- Public documentation must be useful to an external reader and safe to publish.
- Generated documentation should be refreshed by scripts rather than edited by hand when it contains derived tables, counts, or benchmark metrics.
- Working notes may stay public only when they are clearly labeled as non-authoritative project notes.
- Private material belongs in the local gitignored `private/` directory, not in tracked files.
- Private material includes personal notes, raw unpublished lab notes, unreviewed extraction scratch, reviewer comments, credentials, and publication/social-media drafts written for personal reuse.
- Public citations should include enough source metadata for traceability, but copied article text, paywalled tables, and raw PDF excerpts should not be committed.

The local `private/` directory is intentionally ignored by Git. If private material is accidentally staged, remove it from the index with `git rm --cached <path>` and keep only sanitized summaries in public docs.

## Current Classification

| Path | Class | Public Action |
|---|---|---|
| `docs/application-workflow.md` | Public | Keep as workflow documentation. |
| `docs/application-targets-research.md` | Working note | Keep labeled as research notes until converted into generated target/source docs. |
| `docs/bread-baking-calibration-report.md` | Generated | Keep public; future automation should own derived tables and counts. |
| `docs/demo-narrative.md` | Public | Keep as demo guidance after removing personal/social draft content. |
| `docs/development-workflow.md` | Public | Keep as contributor workflow documentation. |
| `docs/evidence-map.md` | Public | Keep as evidence summary; later derive counts/citation lists from source metadata. |
| `docs/flavor-heuristic-model.md` | Public | Keep as model-limitation documentation. |
| `docs/generated/bibliography.md` | Generated | Keep public; regenerate from `data/literature/sources.json`. |
| `docs/generated/evidence-summary.md` | Generated | Keep public; regenerate from structured literature records. |
| `docs/literature-coverage-ood.md` | Public | Keep as coverage/OOD interpretation documentation. |
| `docs/literature-extraction-template.md` | Public | Keep as extraction template. |
| `docs/literature-first-validation-roadmap.md` | Public | Keep as validation strategy documentation. |
| `docs/literature-triage.md` | Working note | Keep labeled as triage, not extraction record; migrate stable citations into the source registry in #79. |
| `docs/massive-validation-benchmark.md` | Working note | Keep labeled as simulation benchmark, not experimental validation. |
| `docs/ml-residual-benchmark.md` | Generated | Keep public; future automation should check generated block freshness. |
| `docs/pasta-cooking-calibration-report.md` | Generated | Keep public; future automation should own derived tables and counts. |
| `docs/pasta-v1-workflow.md` | Public | Keep as application workflow documentation. |
| `docs/pizza-v1-literature-audit.md` | Public | Keep as conservative Pizza V1 evidence-boundary documentation. |
| `docs/review-cleanup-audit.md` | Working note | Keep as historical audit only until remaining useful items are issue-tracked or retired. |
| `docs/target-profile-calibration.md` | Public | Keep as target calibration design documentation. |
| `docs/adr/README.md` | Public | Keep as ADR index. |
| `docs/adr/0000-template.md` | Public | Keep as ADR template. |

## Private Candidates Removed From Public Docs

- Personal-origin wording was removed from the README in favor of a project-focused description.
- The first-person LinkedIn-style draft was removed from `docs/demo-narrative.md`; publication drafts belong in `private/`.

## Follow-Up Work

- #79 should introduce a single source registry for literature citations and stable source IDs.
- #80 should automate checks for generated documentation freshness and citation consistency.
