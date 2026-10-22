# Final schema batch: Intelligence + Validation (DRAFT)

**Status:** Locally validated by Claude (4/4 XanoScript files and semantic checks), reviewed and revised for C1–C5. Revised files have NOT been revalidated yet, server dry-run has not occurred, and deployment/merge is not approved.

**Git branch:** `feat/final-schema-batch`. Keep these files separate from the `main` branch while Research Batch 2 is deployed.

**Tables:** `insights`, `insight_evidence`, `hypotheses`, `experiments` under `table/` so a future Xano CLI dry-run can use `-d ./xano/intelligence_validation`.

**Source:** `docs/04-LOGICAL_DATA_MODEL.md`. Uses Market/Research physical conventions, including `created_at`, nullable API-managed `updated_at`, plural names, relational reference metadata and indexes. All output handling must enforce owner authorization independently of `sensitive` metadata.

## Schema review decisions (C1–C5, 2026-10-22)
- **C1 Sensitive fields:** mark `insights.statement`, `insight_evidence.excerpt`, `experiments.observed_result`, and `experiments.notes` as sensitive; not `experiments.baseline`, `experiments.target`, or `hypotheses.statement`. Metadata alone is NOT API authorization or guaranteed field redaction.
- **C2 Trimming:** `filters=trim` on experiment `baseline`, `target`, `observed_result`, and `notes`. Keep original research interview/survey answers and evidence excerpts untrimmed; use evidence fields for verbatim quotations.
- **C3 Provenance:** keep nullable, trimmed, validated-text `source_field` (not enum). For interviews allow `notes`, `transcript`, `existing_alternatives`, `problem_context`. For survey participations allow `beneficiary_description`, `main_benefit`, `improvement_request`. If provided, the field must exist on and contain nonblank source content; a survey participation is citable only after `responded_at`.
- **C4 Multiple excerpts:** one source may support several distinct excerpts for an insight. No unique source constraint; warn on identical duplication in the API.
- **C5 Query index:** replace global `(review_status, created_at DESC)` with `(product_id, review_status, created_at DESC)` to serve product-scoped status lists.
- Defaults approved as drafted: low insight confidence, draft insight review status, medium hypothesis priority, proposed hypothesis status. `type` and `relationship` enum fields remain explicit and required. The server must verify enum field names/values.
- Child tables carry parent references rather than redundant product IDs. Ownership and product consistency must be enforced in all APIs.

## Remaining review gates
- Revalidate these **revised** source files (offline syntax, semantic checks, negative controls). The previously reported validator pass was against the prior draft.
- Close Research Batch 2 first: user disables direct push, verifies signup lock and empty Research tables; Claude verifies read-back then commits Research GUIDs/docs on `main`.
- Never merge into `main`, enable CLI push or deploy the final batch until the Research closure is verified.

## Rules that require later API enforcement
1. `insights.segment_id` must refer to a segment belonging to the insight's product.
2. Every evidence row must refer to **exactly one** original source: interview XOR survey participation; verify the source exists and belongs to the insight's product. Verify excerpts/source_field are meaningful and traceable.
3. `review_status=reviewed` requires >=1 existing evidence record. Reject deleting the last evidence from a reviewed insight; reviewed status transitions must be deliberate.
4. Only create hypotheses from reviewed insights. Restrict deleting any record cited by evidence/hypotheses/experiments.
5. Validate required text is nonblank, timestamps are chronological when supplied, and status/conclusion/decision combinations make sense in API workflows.
6. Preserve original interview/survey answers and historical segment snapshots. Evidence and survey data must never be silently rewritten by changes to derived insights.
7. Every API endpoint requires the designated authenticated owner; restrict cross-product references and mutations.

## Deployment gate
1. Research Batch 2 tables have reportedly been pushed and read back, but **not closed**: first disable direct push; confirm signup lock/empty tables, and commit GUIDs/docs on `main`.
2. Pull current `main` and reconcile this feature branch without overwriting Research updates.
3. Have Claude run offline XanoScript syntax **and semantic** validation and inspect the definitions; resolve review points before merging into `main`.
4. Commit reviewed schema to `main`; user verifies auth/signup External Access disabled and permits temporary `allow_push=true` in `pmf`, workspace 2 only.
5. Dry-run only: `xano workspace push -p pmf -w 2 -b v1 -d ./xano/intelligence_validation --dry-run`; accept only four CREATE operations and no modifications, then obtain separate authorization for an interactive actual push without `--force`.
6. Re-disable `allow_push`, compare read-back definitions, preserve assigned table GUIDs, verify existing schema/auth untouched, and update the status/decision logs.

**Never run the real push from this branch or before the review gates.**
