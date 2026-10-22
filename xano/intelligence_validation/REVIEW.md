# Final schema batch: Intelligence + Validation (DRAFT)

**Status:** Design drafts only. Not offline validated, not server dry-run, not approved for merge or deployment.

**Git branch:** `feat/final-schema-batch`. Keep these files separate from the `main` branch while Research Batch 2 is deployed.

**Tables:** `insights`, `insight_evidence`, `hypotheses`, `experiments` under `table/` so a future Xano CLI dry-run can use `-d ./xano/intelligence_validation`.

**Source:** `docs/04-LOGICAL_DATA_MODEL.md`. Uses Market/Research physical conventions, including `created_at`, nullable API-managed `updated_at`, plural names, relational reference metadata and indexes. All output handling must enforce owner authorization independently of `sensitive` metadata.

## Schema review questions
- Are low confidence for new insights and medium priority for new hypotheses appropriate defaults? Draft/review and proposed status default to `draft`/`proposed`.
- Xano validator/server must confirm `enum type` works as a field name and all enum values/defaults are valid.
- Review whether marking inferred statements and experiment notes/measurements sensitive is desired.
- Should `source_field` remain optional free text? Proposed yes, with API field-name validation.
- No redundant product IDs have been added to hypotheses, evidence or experiments. All product ownership is resolved through parent references.

## Rules that require later API enforcement
1. `insights.segment_id` must refer to a segment belonging to the insight's product.
2. Every evidence row must refer to **exactly one** original source: interview XOR survey participation; verify the source exists and belongs to the insight's product. Verify excerpts/source_field are meaningful and traceable.
3. `review_status=reviewed` requires >=1 existing evidence record. Reject deleting the last evidence from a reviewed insight; reviewed status transitions must be deliberate.
4. Only create hypotheses from reviewed insights. Restrict deleting any record cited by evidence/hypotheses/experiments.
5. Validate required text is nonblank, timestamps are chronological when supplied, and status/conclusion/decision combinations make sense in API workflows.
6. Preserve original interview/survey answers and historical segment snapshots. Evidence and survey data must never be silently rewritten by changes to derived insights.
7. Every API endpoint requires the designated authenticated owner; restrict cross-product references and mutations.

## Deployment gate
1. Wait for Research Batch 2 to be pushed, read back and documented, with its table GUIDs committed on `main`.
2. Pull current `main` and reconcile this feature branch without overwriting Research updates.
3. Have Claude run offline XanoScript syntax **and semantic** validation and inspect the definitions; resolve review points before merging into `main`.
4. Commit reviewed schema to `main`; user verifies auth/signup External Access disabled and permits temporary `allow_push=true` in `pmf`, workspace 2 only.
5. Dry-run only: `xano workspace push -p pmf -w 2 -b v1 -d ./xano/intelligence_validation --dry-run`; accept only four CREATE operations and no modifications, then obtain separate authorization for an interactive actual push without `--force`.
6. Re-disable `allow_push`, compare read-back definitions, preserve assigned table GUIDs, verify existing schema/auth untouched, and update the status/decision logs.

**Never run the real push from this branch or before the review gates.**
