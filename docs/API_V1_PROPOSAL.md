# PMF Engine — Phase 3 Consolidated Business API: Technical Proposal (READ-ONLY DRAFT)

**Status:** design proposal for architectural review. Nothing in this document is implemented. No Xano, Git or settings changes were made while preparing it.
**Baseline:** GitHub `main` = `19f0172` (clean). Xano instance `xgjc-aodb-3a7q`, workspace `pmf` (ID 2), branch `v1` (live, only branch), `allow_push: false`.
**Specs used:** PROJECT_CONTEXT, CLAUDE.md, docs 03/04/05/06/07/08, PROJECT_STATUS, DECISION_LOG D-001…D-031, the ten committed `.xs` tables, `xano/intelligence_validation/REVIEW.md`, bundled XanoScript reference (`@xano/developer-mcp` 2.2.6) and Xano CLI 1.3.4 help/source.

---

## 0. Verified environment (read-only, 2026-10-22)

| Item | Observation |
|---|---|
| Workspace | `pmf` ID 2; `allow_push: false`; branches: `v1` (live) only, no backups |
| Definitions | 16 documents, byte-identical to the Phase 2 read-back: `workspace/pmf`, `user`, 10 business tables, `Authentication` group (`canonical = "xHMmrw_d"`) with `auth/login`, `auth/me`, `auth/signup` |
| Functions / tests / tenants | none (`function list`, `unit_test list`, `workflow_test list`, `tenant list`, `ephemeral list` all empty) |
| Auth | `auth/login` issues 24 h token (`security.create_auth_token`, table `user`); `auth/me` requires `auth = "user"`; `auth/signup` External Access reported OFF by owner (not visible in XanoScript) |

### XanoScript capabilities confirmed for this design
Confirmed in the bundled reference **and** by offline-validating prototypes (scratchpad only):
- `function "pmf/<folder>/<name>"` with `function.run "…" { input = {…} } as $x` (`as` is required).
- Owner check via `$env.PMF_OWNER_USER_ID|to_int` compared to `$auth.id` — validates.
- `db.transaction { stack { … } }` — validates. **`isolation = "serializable"` is rejected by the validator** in every position despite appearing in the docs → do not rely on it.
- `db.query … return = {type: "count" | "exists" | "single" | "list" (+paging)}`, joins + `eval`, null-safe filters `==?`.
- `db.direct_query` (raw SQL with `?` args) — validates; usable for `SELECT … FOR UPDATE` row locks *if* it runs inside the surrounding transaction (**runtime verification required**).
- `precondition` error types: `inputerror` 400, `accessdenied` 403, `notfound` 404, `standard` 500; missing/invalid token → 401 automatically. No native 409 → conflicts return 400 with a distinct message/code.
- `try_catch` / `throw` for converting unique-index violations into 400s.
- Input fields support `sensitive = true` → **masked in request logs**. `sensitive` does not affect API output.
- API group `canonical` must be **unique per instance** (Goodz shares the instance) → use a `pmf-` prefix. Group `active = false` disables the whole group (kill switch).
- **Route collision rule:** a wildcard segment collides with any literal at the same position for the same verb (e.g. `GET customers/{id}` vs `GET customers/search`). The inventory below is collision-free; search is done with query parameters.
- File layout for push: `api/<group>/…`, `function/<folder>/<name>.xs`, `workflow_test/…`, one construct per file.

### Branch vs data isolation (critical)
| Mechanism | Isolates API logic? | Isolates data? | Notes |
|---|---|---|---|
| API branch (`xano branch create dev`, URL `api:<canonical>:dev`) | Yes | **No** — tables and records are shared with live `v1` | Useful for staging logic, not for test data |
| Unit / workflow tests (`xano unit_test run_all`, `workflow_test run_all`) | n/a | **No by default** — CLI help: "Tests share the workspace database" | Workflow tests accept `datasource`; `"live"` *clones the datasource before each run* (docs). Whether writes then stay in the clone is **unverified** |
| Data Source Environments (`db.set_datasource`, test `datasource = "<name>"`) | n/a | Yes, per docs | Availability on this plan **unverified**; none observed |
| **Ephemeral tenant** (`xano ephemeral create`, 1–24 h auto-expiry, own push/pull) | Yes | **Yes** (separate tenant) | Listing works; creation/plan cost **unverified**; creation is a write requiring approval |

**Conclusion:** API work *can* be staged on a separate branch, but a branch alone does **not** keep test records out of the live tables. An isolated dataset requires an ephemeral tenant (preferred), a verified cloned datasource for workflow tests, or a Data Source Environment.

---

## 1. Architecture overview

- **One new API group** `PMF App`, `canonical = "pmf-app"` (decision U3). Existing `Authentication` group unchanged.
- Every business endpoint: `auth = "user"`, first statement `function.run "pmf/auth/require_owner"`, then an **access loader** that fetches the target record, resolves its product through parent references, and verifies `products.owner_user_id == $auth.id`. Missing *or* not-owned records → 404 (no existence leak).
- **Server-controlled fields are never accepted from clients:** `id`, `product_id` on create (taken from the route), `owner_user_id`, `segment_id_snapshot`, `review_status`, `closed_at`, `created_at`, `updated_at`. Unknown/forbidden fields are simply not declared as inputs.
- Raw evidence is never mutated by derived records. Interview/survey text fields are stored untrimmed (D-020); blank-only values are normalized to `null`.
- Pure computations (PMF math, response-state rules, experiment rules) live in DB-free functions so they can be unit-tested without data.

### Owner identification (no invented IDs, no secrets in Git)
- Workspace environment variable **`PMF_OWNER_USER_ID`**, set by the owner in the Xano UI (Workspace Settings → Environment Variables). The value is the numeric `id` returned by the owner's own `GET auth/me` (or shown in Database → `user`).
- Not stored in Git, never pushed (we never use `--env`), never accepted from a client.
- `require_owner` **fails closed**: if the variable is missing/blank → 500 "Owner not configured"; if `$auth.id` differs → 403.
- `products.owner_user_id` is always set server-side to `$auth.id` and checked by every loader — a second, data-level layer (D-001, Batch 0 owner guard).
- Optional hardening (decision U10): add the same check to `auth/login` so non-owner accounts cannot even obtain tokens.

---

## 2. Endpoint inventory (52 new + 3 existing)

Conventions for **all** `PMF App` endpoints unless stated:
- Auth: `auth = "user"` + `require_owner` → 401 (no/invalid token), 403 (non-owner), 500 (owner not configured).
- Record lookups through access loaders → 404 when absent or not owned.
- Lists: Xano paged response (`items`, `curPage`, `nextPage`, `prevPage`, `itemsReceived`, `itemsTotal`), `page` (default 1), `per_page` (default 25, max 100), newest first unless stated.
- Writes set `updated_at = now`. Optional text inputs: blank → `null`.
- Inputs that carry interview/survey/evidence text are declared `sensitive = true` (log masking).
- "Txn" = wrapped in `db.transaction`; "Lock" = parent row locked first (see §4.3).

### A. Authentication & owner session
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| A1 | `POST auth/login` *(existing)* | email, password | `{authToken}` | unchanged (optional U10 owner restriction) | user | — | — | 403 invalid credentials |
| A2 | `GET auth/me` *(existing)* | — | `{id,created_at,name,email}` | unchanged | user | — | — | 401 |
| A3 | `POST auth/signup` *(existing)* | — | — | External Access OFF; unchanged | user | — | — | blocked externally |
| A4 | `GET session` | — | `{user_id, name, email, is_owner: true}` | owner check only; lets the frontend gate the app | user | require_owner | — | 401/403/500 |

### B. Products, segments, customers
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| B1 | `GET products` | page, per_page | paged products (all fields) | only `owner_user_id == $auth.id` | products | require_owner | — | — |
| B2 | `POST products` | name, description?, core_value?, activation_definition?, value_event_definition? | product | `owner_user_id = $auth.id` server-side; name non-blank | products | require_owner, text/normalize | — | 400 |
| B3 | `GET products/{product_id}` | — | product + `counts {segments, customers, interviews, survey_waves, insights, hypotheses}` | owned | products, children (counts) | access/product | — | 404 |
| B4 | `PATCH products/{product_id}` | same fields, all optional | product | owner/product id immutable | products | access/product | — | 400/404 |
| — | *(no product DELETE in V1 — decision U8)* | | | | | | | |
| B5 | `GET products/{product_id}/segments` | page, per_page | paged segments (+`customer_count`) | owned product | segments, customers | access/product | — | 404 |
| B6 | `POST products/{product_id}/segments` | name, description?, criteria? | segment | unique (product_id, name) — pre-check + index | segments | access/product, db/unique_error | — | 400 duplicate name |
| B7 | `PATCH segments/{segment_id}` | name?, description?, criteria? | segment | product immutable; unique name | segments | access/segment | — | 400/404 |
| B8 | `DELETE segments/{segment_id}` | — | `{deleted: true}` | **restrict** if referenced by customers.segment_id, survey_participations.segment_id_snapshot or insights.segment_id | segments + refs | access/segment, guard | Txn | 400 "in use" (with counts) |
| B9 | `GET products/{product_id}/customers` | q? (name/email/company/external_id contains), segment_id?, lifecycle_stage?, page | paged customers (no interview text) | owned product; `segment_id` must be in product | customers | access/product | — | 400/404 |
| B10 | `POST products/{product_id}/customers` | segment_id?, external_id?, name?, email?, company_name?, lifecycle_stage? | customer | segment ∈ product; external_id blank→null; unique (product, external_id) | customers, segments | access/product, integrity/segment_in_product, text/normalize | — | 400 cross-product / duplicate external_id |
| B11 | `GET customers/{customer_id}` | — | customer + `segment {id,name}` + `interviews[] {id, conducted_at}` + `participations[] {id, wave {id,name}, status, segment_id_snapshot}` | owned | customers, interviews, survey_participations, survey_waves, segments | access/customer, survey/participation_status | — | 404 |
| B12 | `PATCH customers/{customer_id}` | segment_id?, external_id?, name?, email?, company_name?, lifecycle_stage? | customer | **product_id immutable**; segment ∈ same product; changing segment never touches snapshots | customers | access/customer, integrity/segment_in_product | — | 400/404 |
| B13 | `DELETE customers/{customer_id}` | — | `{deleted: true}` | restrict if any interviews or survey_participations | customers + refs | access/customer, guard | Txn | 400 "in use" |

### C. Interviews
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| C1 | `GET customers/{customer_id}/interviews` | page | paged `{id, conducted_at, has_notes, has_transcript, evidence_count}` (no raw text) | owned | interviews, insight_evidence | access/customer | — | 404 |
| C2 | `POST customers/{customer_id}/interviews` | conducted_at, notes?, transcript?, existing_alternatives?, problem_context? (all text `sensitive`) | interview | customer owned; untrimmed; blank→null; `conducted_at` ≤ now + 1 day (U16) | interviews | access/customer, text/normalize_raw | — | 400/404 |
| C3 | `GET interviews/{interview_id}` | — | interview (full text) + `customer {id,name}` + `evidence[] {id, insight_id, relationship}` | owned | interviews, customers, insight_evidence | access/interview | — | 404 |
| C4 | `PATCH interviews/{interview_id}` | conducted_at?, notes?, transcript?, existing_alternatives?, problem_context? | interview | customer_id immutable; **if cited by evidence, raw text fields are locked** (U4) | interviews, insight_evidence | access/interview, guard | Lock+Txn | 400 "cited — raw text locked" |
| C5 | `DELETE interviews/{interview_id}` | — | `{deleted: true}` | restrict if cited by evidence | interviews, insight_evidence | access/interview, guard | Txn | 400 "in use" |

### D. Survey waves, eligibility, invitations, responses
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| D1 | `GET products/{product_id}/survey-waves` | page | paged waves + `state` (draft/open/closed) + `eligible_count` | owned | survey_waves, survey_participations | access/product, survey/wave_state | — | 404 |
| D2 | `POST products/{product_id}/survey-waves` | name, eligibility_rule, questionnaire_version, started_at? | wave | trimmed config fields non-blank; `closed_at` not accepted | survey_waves | access/product | — | 400 |
| D3 | `GET survey-waves/{wave_id}` | — | wave + `state` + `funnel {eligible, invited, responded, valid, incomplete}` + `definition_locked` | owned | survey_waves, survey_participations | access/wave, report/count_wave | — | 404 |
| D4 | `PATCH survey-waves/{wave_id}` | name?, started_at?, eligibility_rule?, questionnaire_version? | wave | closed → 400 (D-021); eligibility_rule/questionnaire_version only while **0 participations** (D-005, invariant 7); started_at cannot move after the earliest responded_at | survey_waves, survey_participations | access/wave, survey/assert_wave_open, survey/assert_definition_unlocked | Lock+Txn | 400 closed / definition locked |
| D5 | `POST survey-waves/{wave_id}/close` | — | wave | must be open; sets `closed_at = now` | survey_waves | access/wave | Lock+Txn | 400 already closed |
| D6 | `POST survey-waves/{wave_id}/reopen` | — | wave | must be closed; sets `closed_at = null` (explicit action, D-021; no audit log claimed) | survey_waves | access/wave | Lock+Txn | 400 not closed |
| D7 | `DELETE survey-waves/{wave_id}` | — | `{deleted: true}` | restrict if any participations | survey_waves, survey_participations | access/wave, guard | Txn | 400 "in use" |
| D8 | `GET survey-waves/{wave_id}/participations` | status? (eligible_only/invited/responded/valid/incomplete), segment_id? (snapshot), page | paged `{id, customer {id,name}, segment_id_snapshot, invited_at, responded_at, disappointment_level, status, beneficiary_description, main_benefit, improvement_request}` | owned | survey_participations, customers | access/wave, survey/participation_status | — | 404 |
| D9 | `POST survey-waves/{wave_id}/participations` | `customer_ids: int[]` (1–200) | `{created: [participation…]}` | wave open; every customer ∈ wave's product; no duplicates in body or wave; **snapshot = customer.segment_id at this moment** (server); all-or-nothing | survey_participations, customers, survey_waves | access/wave, survey/assert_wave_open, integrity/customer_in_product, db/unique_error | Lock+Txn | 400 cross-product / duplicate (lists offending ids) / closed |
| D10 | `PATCH participations/{participation_id}` | invited_at?, responded_at?, disappointment_level?, beneficiary_description?, main_benefit?, improvement_request? (texts `sensitive`, untrimmed) | participation + `status` | wave open; responses require wave started (`started_at` ≤ responded_at) (D-018); D-022: level without responded_at → 400; responded_at without level → allowed (incomplete); responded_at ≤ now; snapshot/customer/wave immutable | survey_participations, survey_waves | access/participation, survey/assert_wave_open, survey/validate_response | Lock(wave)+Txn | 400 closed / not started / invalid state |
| D11 | `DELETE participations/{participation_id}` | — | `{deleted: true}` | wave open; no response recorded; not cited by evidence | survey_participations, insight_evidence | access/participation, guard | Lock(wave)+Txn | 400 |

### E. PMF scoring and reporting
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| E1 | `GET survey-waves/{wave_id}/report` | segment_id? (filter by snapshot), unsegmented? (bool) | **PMF report** (§5) with `overall`, `selected`, `by_segment[]`, `first_time_only`, `warnings[]` | owned; segment must belong to product | survey_participations, survey_waves, segments | access/wave, report/build_wave_report | read-only | 400 segment not in product / 404 |
| E2 | `GET products/{product_id}/pmf-history` | — | waves ordered by started_at (nulls last): `{wave {id,name,started_at,closed_at,questionnaire_version}, overall {valid_response_count, very_count, pmf_percent}, comparable_with_previous, warnings[]}` | owned; never fabricates trends; flags incomparable consecutive waves | as E1 | report/build_wave_report (summary mode) | read-only | 404 |

### F. Insights and evidence
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| F1 | `GET products/{product_id}/insights` | type?, review_status?, segment_id?, confidence?, page | paged insights + `evidence_count {supports, contradicts}` + `hypothesis_count` | owned | insights, insight_evidence, hypotheses | access/product | — | 404 |
| F2 | `POST products/{product_id}/insights` | type, statement, confidence?, segment_id? | insight (`review_status = draft` always) | segment ∈ product | insights | access/product, integrity/segment_in_product | — | 400 |
| F3 | `GET insights/{insight_id}` | — | insight + `evidence[] {id, relationship, excerpt, source_field, source {kind: interview|survey, id, customer {id,name}, date, wave?}}` + `hypotheses[] {id, statement, status}` | owned | insights, insight_evidence, interviews, survey_participations, customers, survey_waves, hypotheses | access/insight, evidence/source_summary | — | 404 |
| F4 | `PATCH insights/{insight_id}` | type?, statement?, confidence?, segment_id? | insight | segment ∈ product; on a **reviewed** insight, changing `type`/`statement` reverts to draft if no hypotheses, else 400 (U5); confidence edits allowed | insights, hypotheses | access/insight, integrity/segment_in_product | Lock+Txn | 400 |
| F5 | `POST insights/{insight_id}/review` | — | insight | draft → reviewed only with ≥1 **valid** evidence row (invariant 6) | insights, insight_evidence (+ sources) | access/insight, insight/count_valid_evidence | Lock+Txn | 400 no evidence / already reviewed |
| F6 | `POST insights/{insight_id}/unreview` | — | insight | reviewed → draft; blocked if hypotheses exist (they require reviewed insights) (U6) | insights, hypotheses | access/insight | Lock+Txn | 400 |
| F7 | `DELETE insights/{insight_id}` | — | `{deleted: true}` | restrict if any evidence or hypotheses | insights + refs | access/insight, guard | Txn | 400 "in use" |
| F8 | `POST insights/{insight_id}/evidence` | interview_id? XOR survey_participation_id?, source_field?, excerpt (`sensitive`, untrimmed), relationship | evidence | **XOR**; source exists and ∈ insight's product; `source_field` whitelist by source type (C3/D-028); cited field non-blank on the source; survey source must have `responded_at` (and level for PMF-category citations); excerpt non-blank; warn (not block) on identical duplicate (`warnings[]`) | insight_evidence, interviews, survey_participations, customers, survey_waves | access/insight, evidence/validate_source | Lock(insight)+Txn | 400 with specific reason |
| F9 | `PATCH evidence/{evidence_id}` | excerpt?, relationship?, source_field? | evidence | sources (interview/participation ids) immutable — delete & recreate to change; re-validate source_field/excerpt | insight_evidence (+source) | access/evidence, evidence/validate_source | Lock(insight)+Txn | 400 |
| F10 | `DELETE evidence/{evidence_id}` | — | `{deleted: true}` | if insight reviewed and this is its last valid evidence → 400 (REVIEW rule 3) | insight_evidence, insights | access/evidence, insight/count_valid_evidence | Lock(insight)+Txn | 400 |

### G. Hypotheses and experiments
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| G1 | `GET products/{product_id}/hypotheses` | status?, priority?, insight_id?, page | paged hypotheses + `insight {id, statement}` + `experiment_count` | owned (join via insights.product_id) | hypotheses, insights, experiments | access/product | — | 404 |
| G2 | `POST insights/{insight_id}/hypotheses` | statement, expected_outcome, success_metric, priority? | hypothesis (`status = proposed`) | insight must be **reviewed** (D-022/REVIEW rule 4) | hypotheses, insights | access/insight, insight/assert_reviewed | Lock(insight)+Txn | 400 insight not reviewed |
| G3 | `GET hypotheses/{hypothesis_id}` | — | hypothesis + `insight {…}` + `experiments[]` (full) | owned | hypotheses, insights, experiments | access/hypothesis | — | 404 |
| G4 | `PATCH hypotheses/{hypothesis_id}` | statement?, expected_outcome?, success_metric?, priority?, status? | hypothesis | insight_id immutable; status transitions per §4.6 (U7) | hypotheses, experiments | access/hypothesis, validation/validate_hypothesis_status | Lock+Txn | 400 invalid transition |
| G5 | `DELETE hypotheses/{hypothesis_id}` | — | `{deleted: true}` | restrict if experiments exist | hypotheses, experiments | access/hypothesis, guard | Txn | 400 "in use" |
| G6 | `POST hypotheses/{hypothesis_id}/experiments` | name, method, started_at?, ended_at?, baseline?, target?, observed_result?, conclusion?, decision?, notes? | experiment | experiment rules §4.6 | experiments | access/hypothesis, validation/validate_experiment | — | 400 |
| G7 | `PATCH experiments/{experiment_id}` | same fields optional | experiment | hypothesis_id immutable; merged-state rules §4.6 | experiments | access/experiment, validation/validate_experiment | — | 400 |
| G8 | `DELETE experiments/{experiment_id}` | — | `{deleted: true}` | allowed only while `conclusion` and `decision` are null (U8: recorded outcomes are provenance) | experiments | access/experiment | — | 400 |

### H. Dashboard and lookups
| ID | Route | Body / params | Response | Business validation | Tables | Functions | Txn | Errors |
|---|---|---|---|---|---|---|---|---|
| H1 | `GET products/{product_id}/overview` | — | `{product, customers {total, by_lifecycle}, segments_count, interviews_count, latest_wave {wave, funnel, pmf_percent, valid_response_count, warnings} | null, insights {draft, reviewed}, hypotheses {by_status}, recent_experiments[5]}`; empty-state friendly, no fabricated trends | owned | all | access/product, report/build_wave_report (summary) | read-only | 404 |
| H2 | `GET products/{product_id}/lookups` | include? (segments, customers, waves, interviews, reviewed_insights) | minimal `{id, label}` lists for pickers (customer label = name or external_id or `#id`; interview label = date + customer) | owned | various | access/product | read-only | 404 |

**Removed as redundant:** segment/participation/experiment detail GETs (covered by parent detail payloads), product-wide interview list (covered by H2 `interviews` lookup), separate invitation/response endpoints (single D10 PATCH).

**Route collision check:** depth-2 wildcard routes all start with distinct literals; depth-3 routes all use `<literal>/{id}/<literal>`; no literal sits at a wildcard position for the same verb. ✔

---

## 3. Reusable function architecture (`function/pmf/…`, ~30 functions)

| Function | Purpose | DB | Unit-testable without data |
|---|---|---|---|
| `pmf/auth/require_owner(auth_id)` | env var present; `auth_id == PMF_OWNER_USER_ID` | no | partially (env) |
| `pmf/access/product(product_id, auth_id)` | get product; owned → record else 404 | yes | — |
| `pmf/access/segment`, `customer`, `interview`, `wave`, `participation`, `insight`, `evidence`, `hypothesis`, `experiment` | load record, walk parents to product, verify ownership; return `{record, product_id}` | yes | — |
| `pmf/integrity/segment_in_product(segment_id?, product_id)` | null OK; else segment exists and same product | yes | — |
| `pmf/integrity/customer_in_product(customer_id, product_id)` | same for customers | yes | — |
| `pmf/text/normalize(value, trim)` | blank→null; trim only for founder-written fields | no | ✔ |
| `pmf/text/is_blank(value)` | whitespace-only check for raw text | no | ✔ |
| `pmf/db/unique_error(error)` | map unique-index violations to 400 with readable message | no | ✔ |
| `pmf/lock/row(table, id)` | `SELECT … FOR UPDATE` via `db.direct_query` inside caller's transaction (fallback: touch `updated_at`) — see §4.3 | yes | — |
| `pmf/survey/wave_state(wave)` | draft (no start / future start) / open / closed | no | ✔ |
| `pmf/survey/assert_wave_open(wave)` | `closed_at == null` | no | ✔ |
| `pmf/survey/assert_definition_unlocked(wave_id)` | zero participations | yes | — |
| `pmf/survey/validate_response(wave, current, patch)` | D-018 + D-022 + time bounds; returns merged state | no | ✔ |
| `pmf/survey/participation_status(p)` | eligible / invited / valid / incomplete / anomaly | no | ✔ |
| `pmf/report/count_wave(wave_id, segment_mode, segment_id?)` | DB counts per bucket (§5) | yes | — |
| `pmf/report/compute_pmf(counts)` | percentages, rates, null on zero denominator, no integer truncation | no | ✔ (fixture numbers) |
| `pmf/report/comparability(wave, product_id)` | definition changes vs previous wave, repeat respondents, small sample, open wave, unsegmented, anomalies | yes | — |
| `pmf/report/build_wave_report(wave_id, filter, mode)` | assemble §5 contract | yes | — |
| `pmf/evidence/validate_source(insight, input)` | XOR, ownership/product, whitelist, non-blank cited field, survey responded | yes | rules part ✔ |
| `pmf/evidence/source_summary(evidence)` | customer/date/wave display data | yes | — |
| `pmf/insight/count_valid_evidence(insight_id)` | evidence rows whose source still satisfies validate_source | yes | — |
| `pmf/insight/assert_reviewed(insight)` | review_status == reviewed | no | ✔ |
| `pmf/validation/validate_experiment(merged)` | §4.6 | no | ✔ |
| `pmf/validation/validate_hypothesis_status(current, next, experiments)` | §4.6 | partly | ✔ |
| `pmf/guard/count_references(entity, id)` | counts used by restricted deletes | yes | — |

---

## 4. Invariant enforcement

### 4.1 Mapping (D-001…D-031 + logical invariants)
| Invariant | Enforcement |
|---|---|
| Non-owner access, incl. product creation | `require_owner` on every business endpoint + loaders check `owner_user_id`; signup External Access off |
| No client-supplied product authority | product taken from route + verified; child product derived from parents |
| Cross-product contamination | `integrity/*` on every reference write (customer.segment, wave.customer, insight.segment, evidence source) |
| Snapshot immutable | set only in D9 from `customer.segment_id`; never an input; never updated |
| Duplicate participation | unique index + pre-check + body de-dup + error mapping, inside txn |
| Closed wave | D4/D9/D10/D11 call `assert_wave_open`; reopen explicit (D6) |
| Eligibility/questionnaire consistency | locked once any participation exists (D4) |
| Denominator = valid responses | `count_wave` valid = responded_at ≠ null ∧ level ∈ {very, somewhat, not} |
| Zero valid → null | `compute_pmf` returns `pmf_percent: null`, never 0 |
| Segment PMF uses snapshot | `count_wave` filters `segment_id_snapshot` only |
| Restricted deletes | §2 deletes: restrict when referenced; no product delete |
| Evidence XOR, source checks | `validate_source` |
| Survey evidence needs response + non-blank field | `validate_source` |
| Reviewed insight needs valid evidence | F5, F10, F4 |
| Hypotheses only on reviewed insights | G2 (+ F6 blocks unreview with hypotheses) |
| Experiment consistency | `validate_experiment` |
| Raw evidence preserved | untrimmed storage; cited interview text locked (U4); evidence sources immutable |
| Customer product immutable | B12 has no product input |

### 4.2 Response-state rules (D-018, D-022)
- `disappointment_level` set ⇒ `responded_at` must be set (else 400).
- `responded_at` without level ⇒ **incomplete** (kept, excluded from score).
- Any response field requires wave `started_at` not null and `started_at` ≤ `responded_at` ≤ now.
- Clearing `responded_at` also requires clearing level (else 400); clearing is blocked if the participation is cited by evidence.
- Status: `valid` (responded + level), `incomplete` (responded, no level), `invited` (invited_at, no responded_at), `eligible` (neither), `anomaly` (level without responded_at — should not exist; counted, never scored).

### 4.3 Concurrency and transactions
Single owner ⇒ realistic races are double-submits and multiple tabs, but invariants must still hold.
- **Uniqueness races** (participation, segment name, external_id): guaranteed by unique indexes; violations mapped to 400.
- **Multi-row invariants** (last evidence of reviewed insight; hypothesis vs unreview; close vs response edit; definition edit vs first participation): inside `db.transaction`, **lock the parent row first** (`insights` or `survey_waves`), then re-read counts/state, then write. Under PostgreSQL READ COMMITTED a second transaction blocks on the lock and re-reads committed state afterwards.
  - Preferred lock: `db.direct_query "SELECT id FROM <table> WHERE id = ? FOR UPDATE"`; fallback: `db.edit` of the parent's `updated_at`.
  - **Must be verified at runtime** (does `db.direct_query` join the surrounding transaction? physical table names with `sql_names: false`?). `isolation = "serializable"` is not usable (validator rejects it).
- Bulk participation add (D9) is all-or-nothing in one transaction.

### 4.4 Errors
Xano standard envelope `{code, message}`; `message` begins with a stable machine token, e.g. `WAVE_CLOSED: …`, `DUPLICATE_PARTICIPATION: …`, `CROSS_PRODUCT_REFERENCE: …`, `EVIDENCE_SOURCE_XOR: …`, `INSIGHT_NOT_REVIEWED: …`, `IN_USE: …`. Messages never echo sensitive input text.

### 4.5 Sensitive data
- Owner-only access is the protection; `sensitive` flags on inputs mask logs.
- List endpoints omit large raw text (interview bodies, transcripts) — detail endpoints return it.
- No endpoint returns `user.password` or tokens; loaders use explicit `output` field lists.
- API group `history` set low (U11) to limit stored request statements.

### 4.6 Hypothesis / experiment rules (proposed, U7)
- Experiment: `ended_at` ≥ `started_at` when both set; `ended_at` requires `started_at`; `conclusion` requires `ended_at` (or explicit observed_result) and non-blank `observed_result`; `decision` requires `conclusion`.
- Hypothesis status: `proposed → testing` requires ≥1 experiment; `→ validated` requires ≥1 experiment with conclusion `supported`; `→ rejected` requires ≥1 `refuted` **or** explicit rejection without experiments (decision U7); `validated/rejected → testing` allowed (re-test). Arbitrary jumps otherwise rejected.

---

## 5. PMF reporting contract (E1)

Definitions (docs/03, D-006, D-022):
- **eligible** = participations in wave (∩ segment filter)
- **invited** = `invited_at` ≠ null
- **responded** = `responded_at` ≠ null
- **valid** = responded ∧ level ∈ {very, somewhat, not}
- **incomplete** = responded ∧ level = null
- **PMF %** = 100 × very / valid; valid = 0 → `null`
- **invited response rate** = valid responses among invited / invited; invited = 0 → `null`. Manually entered responses (valid ∧ not invited) are reported separately and excluded from this rate.

```json
{
  "wave": {"id": 1, "name": "W1", "product_id": 1, "state": "closed",
           "started_at": 0, "closed_at": 0,
           "questionnaire_version": "v1", "eligibility_rule": "…"},
  "filter": {"segment_id": null, "unsegmented": false, "segment": null},
  "selected": {
    "eligible_count": 5, "invited_count": 4, "responded_count": 3,
    "valid_response_count": 3, "incomplete_response_count": 0, "anomaly_count": 0,
    "counts": {"very": 1, "somewhat": 1, "not": 1},
    "pmf_percent": 33.33333333333333,
    "distribution_percent": {"very": 33.333, "somewhat": 33.333, "not": 33.333},
    "invited_valid_count": 2, "manual_valid_count": 1,
    "invited_response_rate": 0.5,
    "response_rate_denominator": "invited_count",
    "sample_note": "directional"
  },
  "overall": { "...same shape, no filter..." : "" },
  "by_segment": [
    {"segment": {"id": 11, "name": "A1"}, "...same counts...": ""},
    {"segment": null, "label": "unsegmented", "...": ""}
  ],
  "first_time_only": {"excluded_repeat_respondents": 0, "...same counts...": ""},
  "warnings": [
    {"code": "SMALL_SAMPLE", "detail": "3 valid responses"},
    {"code": "WAVE_OPEN", "detail": "results provisional"},
    {"code": "DEFINITION_CHANGED", "detail": "questionnaire_version differs from previous wave W0"},
    {"code": "REPEAT_RESPONDENTS", "detail": "1 participant responded in an earlier wave"},
    {"code": "UNSEGMENTED_PARTICIPANTS", "detail": "1 participant had no segment at eligibility"},
    {"code": "NO_VALID_RESPONSES", "detail": "PMF undefined"},
    {"code": "DATA_ANOMALY", "detail": "category without responded_at"}
  ],
  "generated_at": 0
}
```
- `pmf_percent` returned at full precision (decimal arithmetic); formatting is a frontend concern. Tests compare with tolerance 1e-9.
- Segment names are current names; the bucket key is the snapshot id.
- No telemetry, no AI classification; champion / convertible / adjacent groupings stay a human analysis (insights).

---

## 6. Test plan (synthetic data only)

### 6.1 Fixtures
- Users: **OWNER** (designated), **INTRUDER** (second user, created only in the isolated environment).
- Product A ("Synthetic Product A"), Product B.
- Segments: A1 "Solo founders", A2 "Agencies" (A); B1 (B).
- Customers A: C1, C2 (A1); C3, C4 (A2); C5 (none); C6 (A1); C7 (A2). B: CB1 (B1).
- Wave W1 (A, v1, started): eligible C1–C5; invited C1–C4; responses: C1 very (invited), C2 somewhat (invited), C5 not (**not invited — manual**); C3, C4 no response.
  - **Expected overall:** eligible 5, invited 4, valid 3, very 1, somewhat 1, not 1, incomplete 0, PMF = 33.333…%, invited_response_rate = 2/4 = 0.5, manual_valid 1.
  - **By segment:** A1 valid 2 → 50%; A2 valid 0 → `null`; unsegmented valid 1 → **0.0** (not null).
- Wave W2 (A, v2): C1 (repeat), C6, C7 — repeat-respondent and definition-change checks.
- Wave W3 (A): eligible C6, no responses → zero denominator.
- Interviews I1 (C1), I2 (C3); IB1 (CB1).

### 6.2 Matrix (abbreviated IDs; full expected values per row)
| ID | Category | Scenario | Expected |
|---|---|---|---|
| S01 | Security | Every endpoint without token (automated sweep of inventory) | 401 |
| S02 | Security | Every endpoint with INTRUDER token | 403 |
| S03 | Security | `PMF_OWNER_USER_ID` unset (isolated env) | 500 fail-closed on all business endpoints |
| S04 | Security | Owner requests B-product IDs via A routes / forged ids | 404 |
| S05 | Security | Mass assignment: send owner_user_id, product_id, segment_id_snapshot, review_status, closed_at in bodies | ignored; server values persist |
| S06 | Security | No response anywhere contains `password` or tokens | pass |
| S07 | Security | Error messages do not echo excerpt/notes text | pass |
| S08 | Security | Request history shows sensitive inputs masked (isolated env) | pass |
| S09 | Security | `auth/signup` external call | blocked |
| M01 | Market | Create product → owner_user_id = OWNER | pass |
| M02 | Market | Duplicate segment name in A | 400; same name in B OK |
| M03 | Market | Customer A with segment B1 | 400 CROSS_PRODUCT |
| M04 | Market | Two customers with blank external_id | both OK (null) |
| M05 | Market | Duplicate external_id in A | 400; same in B OK |
| M06 | Market | Prospect without email/account | OK |
| M07 | Market | PATCH customer product_id | not accepted |
| R01 | Research | Interview for C1; later insight edits don't change notes | notes byte-identical |
| R02 | Research | Edit cited interview text | 400 locked (U4) |
| R03 | Research | Delete customer with interview | 400 IN_USE |
| W01 | Survey | Add C1–C5 to W1 | 5 created, snapshots = current segments |
| W02 | Survey | Re-add C1 to W1 | 400 DUPLICATE |
| W03 | Survey | Body with duplicate ids / CB1 included | 400, nothing created (all-or-nothing) |
| W04 | Survey | Level without responded_at | 400 |
| W05 | Survey | responded_at without level | 200, counted incomplete |
| W06 | Survey | Response before wave started / wave without started_at | 400 |
| W07 | Survey | Change questionnaire_version after participants | 400; before participants OK |
| W08 | Survey | Close W1, then PATCH response / add participant / delete participant / edit definition | 400 ×4 |
| W09 | Survey | Reopen W1, edit, close again | 200s |
| W10 | Survey | Move C2 A1→A2 after eligibility | W1 report unchanged; C2 snapshot still A1 |
| W11 | Survey | Delete wave with participations | 400 |
| P01 | Numeric | W1 overall | 33.333…% (not 33, not 0), counts as fixture |
| P02 | Numeric | W1 segment A1 / A2 / unsegmented | 50.0 / null / 0.0 |
| P03 | Numeric | W3 | valid 0, pmf null, warning NO_VALID_RESPONSES |
| P04 | Numeric | invited_response_rate excludes manual C5 | 0.5, manual_valid 1 |
| P05 | Numeric | 2 very of 3 valid | 66.666…% (no truncation) |
| P06 | Numeric | segment filter uses snapshot not current segment | per W10 |
| P07 | Cohort | W2 report | REPEAT_RESPONDENTS(1), DEFINITION_CHANGED, first_time_only excludes C1 |
| P08 | Cohort | Open wave | WAVE_OPEN warning |
| P09 | Numeric | Incomplete responses never change pmf | pass |
| E01 | Evidence | Both interview_id and participation_id | 400 XOR |
| E02 | Evidence | Neither | 400 XOR |
| E03 | Evidence | Insight A citing IB1 | 400 CROSS_PRODUCT |
| E04 | Evidence | Survey source C3 (no response) | 400 |
| E05 | Evidence | source_field `main_benefit` blank on source | 400 |
| E06 | Evidence | source_field `transcript` on survey source / `foo` | 400 |
| E07 | Evidence | Blank excerpt | 400 |
| E08 | Evidence | Supports + contradicts on same insight | both listed in F3 |
| E09 | Evidence | Identical duplicate excerpt | 200 + warning |
| I01 | Insight | Review with 0 evidence | 400 |
| I02 | Insight | Review with 1 valid evidence | 200 |
| I03 | Insight | Delete last evidence of reviewed insight | 400 |
| I04 | Insight | Edit statement of reviewed insight with/without hypotheses | 400 / reverts to draft |
| I05 | Insight | Unreview with hypotheses | 400 |
| V01 | Validation | Hypothesis on draft insight | 400 |
| V02 | Validation | ended_at < started_at | 400 |
| V03 | Validation | decision without conclusion | 400 |
| V04 | Validation | status validated without supported experiment | 400 |
| V05 | Validation | Delete hypothesis with experiments; delete concluded experiment | 400 / 400 |
| C01 | Concurrency | 2 parallel adds of same participant | exactly one success |
| C02 | Concurrency | Parallel delete of last two evidence rows of reviewed insight | ≥1 remains |
| C03 | Concurrency | Close wave while response PATCH in flight | no response written after close commit |
| C04 | Concurrency | Parallel hypothesis create + unreview | never hypothesis on draft insight |
| X01 | E2E | docs/08 founder scenario steps 1–9 + docs/05 definitions of done 1–8 | all pass after reload |

### 6.3 Test layers
1. **Unit tests** inline (`test "…"` blocks) on pure functions (`compute_pmf`, `validate_response`, `participation_status`, `validate_experiment`, `normalize`) — no DB writes.
2. **HTTP black-box suite** in Git (`tests/api/`, Python stdlib, synthetic fixtures, tokens via environment variables at runtime, never committed) executing the matrix against an **isolated environment**.
3. Optional **workflow tests** only if a non-live datasource is verified.

### 6.4 Where to run (no live records)
- **Preferred:** ephemeral tenant (1–24 h): push tables + API + functions, create OWNER/INTRUDER users and env var inside the tenant, run the suite, let it expire. Requires approval + plan availability check.
- **Alternative:** workflow tests with `datasource = "live"` clone — only after a probe proves writes stay in the clone.
- **Alternative:** a Data Source Environment, if the plan supports it.
- **Not recommended:** synthetic records in live `v1` with cleanup (consumes IDs, risks residue, requires deletes in production).
- **If no isolation is available:** stop and decide (risk acceptance) — do not silently test in live.

---

## 7. One-batch implementation plan

### 7.1 Dependency order (internal checkpoints)
1. CP0 — owner env var set (UI) and verified via a read-only probe; test environment approved and created.
2. CP1 — pure functions + unit tests (text, survey state, pmf math, experiment rules).
3. CP2 — `require_owner`, access loaders, integrity, lock helper (+ runtime lock verification).
4. CP3 — API group + Market (B) + `session` (A4).
5. CP4 — Interviews (C).
6. CP5 — Surveys (D) + report (E).
7. CP6 — Insights/evidence (F).
8. CP7 — Hypotheses/experiments (G) + dashboard/lookups (H).
9. CP8 — full matrix + concurrency + E2E in isolated env → live dry-run → separately approved push → read-only live smoke.

### 7.2 Expected files (Git)
```
xano/app/
  api/pmf_app/api_group.xs                 # canonical "pmf-app"
  api/pmf_app/…                            # 52 endpoint files (exact paths follow the CLI pull layout, e.g. <route>_<VERB>.xs)
  function/pmf/auth/require_owner.xs
  function/pmf/access/{product,segment,customer,interview,wave,participation,insight,evidence,hypothesis,experiment}.xs
  function/pmf/integrity/{segment_in_product,customer_in_product}.xs
  function/pmf/text/{normalize,is_blank}.xs
  function/pmf/db/unique_error.xs
  function/pmf/lock/row.xs
  function/pmf/survey/{wave_state,assert_wave_open,assert_definition_unlocked,validate_response,participation_status}.xs
  function/pmf/report/{count_wave,compute_pmf,comparability,build_wave_report}.xs
  function/pmf/evidence/{validate_source,source_summary}.xs
  function/pmf/insight/{count_valid_evidence,assert_reviewed}.xs
  function/pmf/validation/{validate_experiment,validate_hypothesis_status}.xs
  function/pmf/guard/count_references.xs
tests/api/  (runner, fixtures, matrix — no secrets)
docs/09-API_CONTRACT.md
docs/PROJECT_STATUS.md, docs/DECISION_LOG.md (updates)
```
Push directory `-d ./xano/app` contains no `table/` → table definitions cannot be touched by the API push.

### 7.3 Development & deployment strategy
1. Feature branch `feat/api-v1` in Git; offline validation + semantic lint + unit tests locally.
2. Isolated environment (ephemeral tenant) receives tables + `xano/app`; full matrix runs there.
3. Optional API branch `dev` in workspace 2 for staging logic only — **no writes** (shared data).
4. Live: set `PMF_OWNER_USER_ID` (UI) → temporary `allow_push` → `xano workspace push -p pmf -w 2 -b v1 -d ./xano/app --dry-run` (expect only CREATEs: 1 group, 52 queries, ~30 functions; 0 updates/deletes; no table/auth changes) → user-run interactive push → push off (CLI-verified) → read-back diff → read-only smoke (401/403 sweep, `GET session`, `GET products` empty) → signup lock re-check.

### 7.4 Rollback
- Immediate kill switch: set `active = false` on `pmf-app` group (one-file push) → all business endpoints stop; auth unaffected.
- Full removal: delete the group/functions in the UI (or a reviewed `--sync --delete` only with explicit approval).
- Optional pre-deploy backup branch of `v1` (`branch create`, approval) — logic only.
- No data migrations, no table changes → no data rollback needed.

### 7.5 Expected changes
- **Xano live:** +1 API group, +52 endpoints, ~+30 functions, +1 env var (owner-set). No table/auth changes, no records.
- **Xano isolated env:** temporary tenant with synthetic data (expires).
- **GitHub:** files in §7.2 via PR.

---

## 8. Risks, unresolved decisions, approvals

### Risks
1. **No verified isolated dataset yet** — tests could otherwise touch live tables.
2. Row-lock pattern and transaction semantics unverified at runtime; `serializable` unavailable.
3. Owner ID not yet recorded; mis-set env var locks the owner out (fail-closed) — recoverable via UI.
4. Endpoints pushed to `v1` are live immediately (protected by auth + owner check).
5. Request history may retain non-sensitive-marked data; keep `sensitive` on all text inputs.
6. Xano writeback may rename endpoint files on first pull — accept server layout.
7. 52 endpoints in one batch — mitigated by checkpoints and the full matrix.

### Decisions requested
| ID | Decision | Recommendation |
|---|---|---|
| U1 | Owner identity source | `PMF_OWNER_USER_ID` env var (UI-set) + `owner_user_id` data check |
| U2 | Test environment | Ephemeral tenant (probe availability first) |
| U3 | API grouping | One group `pmf-app` |
| U4 | Editing cited interview raw text | Lock cited raw text fields |
| U5 | Editing reviewed insight statement/type | Revert to draft if no hypotheses, else block |
| U6 | Unreview with hypotheses | Block |
| U7 | Hypothesis status transitions | §4.6 rules |
| U8 | Delete matrix | No product delete; restrict all referenced deletes; concluded experiments not deletable |
| U9 | Small-sample warning threshold | Configurable constant; value to decide (e.g. 40) |
| U10 | Restrict `auth/login` to owner | Recommended hardening |
| U11 | API request history level | Low/minimal |
| U12 | Pagination defaults | 25 / max 100 |
| U13 | Lock mechanism | `FOR UPDATE` via direct_query if verified; else parent `updated_at` touch |
| U14 | `conducted_at` / `responded_at` future tolerance | ≤ now + 1 day / ≤ now |

### Approvals required before/within implementation
1. Approve this contract (or amendments) and decisions U1–U14.
2. Owner sets `PMF_OWNER_USER_ID` in the Xano UI (value never committed).
3. Create an ephemeral tenant (or alternative) for testing; create synthetic users/data there.
4. Create Git feature branch and commit source files.
5. Temporary `allow_push` for the live dry-run; separately approved interactive live push.
6. Optional: `dev` API branch, backup branch, `auth/login` owner restriction.

---

# Appendix R — Architectural Review and Implementation Gates (2026-10-22)

**Status:** review addendum. The original proposal above (sections 0–8) is preserved unchanged. Nothing here is implemented or deployed. Implementation, environment creation and any Xano change remain **unauthorized** until the owner approves the gates in R7.

Legend — **[V]** verified platform behavior (observed via CLI/metadata, live read-only request, offline validator, or CLI source); **[D]** stated in bundled Xano documentation but not exercised; **[A]** assumption requiring runtime verification.

## R1. Review outcome
The general architecture (single owner guard, access loaders resolving ownership through parent references, server-controlled fields, pure functions for scoring/rules, restricted deletes, PMF report contract) is accepted in principle by the owner and the ChatGPT review. The decisions below are **recommendations awaiting explicit owner approval**; none is recorded in DECISION_LOG yet.

## R2. U1–U14 resolution

| ID | Topic | Classification | Recommended resolution |
|---|---|---|---|
| U1 | Owner identity | Recommended for approval | Workspace env var `PMF_OWNER_USER_ID`, set by the owner in the Xano UI from their own `auth/me` id; fail closed (500) when unset, 403 on mismatch; plus `products.owner_user_id` data check. Value never in Git or client input. |
| U2 | Test environment | **Conditional** | Ephemeral tenant in workspace 2 if entitlement and cost are confirmed; otherwise the account sandbox only if the owner confirms it holds no Goodz work. See R4. |
| U3 | API grouping | Recommended for approval | One group `PMF App`, canonical `pmf-app` (instance-unique prefix). |
| U4 | Cited interview text | Recommended for approval | Once an interview is cited by evidence, `notes`, `transcript`, `existing_alternatives`, `problem_context` are locked; `conducted_at` stays editable. Same lock for cited survey answer fields and for clearing a cited response. |
| U5 | Editing reviewed insight | Recommended for approval | `type`/`statement` edits on a reviewed insight revert it to draft when it has no hypotheses; blocked when hypotheses exist. `confidence`/`segment_id` edits allowed. |
| U6 | Unreview with hypotheses | Recommended for approval | Block. |
| U7 | Hypothesis transitions | Recommended for approval (revised in R3.1) | See R3.1. |
| U8 | Delete matrix | Recommended for approval | No product delete; restricted deletes for all referenced records; concluded experiments not deletable; participations deletable only while unanswered, uncited and wave open. |
| U9 | Small-sample threshold | **Unresolved — owner input** | Configurable constant (proposed default 40, as a warning only, never altering the score). The project docs say only that small samples are directional; the exact number is a product decision. |
| U10 | Owner-only login | Recommended for approval | Add the `PMF_OWNER_USER_ID` check to `auth/login` in the same batch (non-owners cannot obtain tokens). Requires editing an existing auth endpoint → included in the live dry-run diff as the only expected UPDATE. |
| U11 | Request history | Recommended for approval | Group `history` low; `sensitive = true` on every input carrying interview, survey or evidence text. |
| U12 | Pagination | Recommended for approval | `per_page` default 25, max 100. |
| U13 | Lock mechanism | Recommended for approval (revised) | Lock by a **no-op self-update** of the parent row (`db.edit` writing an unchanged field) inside `db.transaction`; no raw SQL. See R3.3. |
| U14 | Timestamp tolerance | Recommended for approval (revised in R3.2) | See R3.2. |

## R3. Technical uncertainties resolved

### R3.1 Hypothesis state transitions (replaces §4.6 hypothesis part)
| From → To | Rule |
|---|---|
| proposed → testing | ≥1 experiment exists |
| proposed → rejected | allowed (abandoned before testing) |
| testing → validated | ≥1 experiment with `conclusion = supported` |
| testing → rejected | ≥1 experiment with `conclusion = refuted` |
| validated / rejected → testing | allowed (re-test) |
| any → proposed | only when 0 experiments |
| proposed → validated | not allowed (must test first) |
Status never changes automatically when experiments are added or concluded (no silent state changes). Mixed outcomes (supported and refuted) are permitted; the owner chooses, and the report shows all experiment conclusions. Experiment rules from §4.6 stand: `ended_at ≥ started_at`; `ended_at` requires `started_at`; `conclusion` requires non-blank `observed_result`; `decision` requires `conclusion`.

### R3.2 Timestamp semantics (U14)
- Storage: Xano `timestamp` (UTC epoch milliseconds) **[D]**; clients may send ISO-8601 or epoch; responses return epoch.
- `interviews.conducted_at`: when the conversation happened; backfilled past dates allowed; future values rejected beyond now + 24 h (time-zone slack).
- `survey_waves.started_at`: start of the measurement window; may be historical for backfilled waves; required before any response (D-018); cannot move later than the earliest `responded_at`.
- `survey_waves.closed_at`: the moment the wave was **locked**. The close action accepts an optional `closed_at` (≥ latest `responded_at`, ≤ now; default now) so historical waves can record their real end. Reopen clears it (D-021).
- `invited_at`: optional; may precede `started_at`; when both `invited_at` and `responded_at` are set, `invited_at ≤ responded_at`.
- `responded_at`: `started_at ≤ responded_at ≤ now`. Historical manual entry is allowed; such responses are reported as manual when `invited_at` is null.
- `created_at`: system record time (participation `created_at` = qualification record time, D-005); never client-supplied.

### R3.3 Row locking, direct SQL and transactions
- **[V]** `db.transaction { stack { … } }` passes the offline validator; `isolation = "serializable"` is rejected in every position → not usable.
- **[V]** `db.direct_query` with `?` placeholders and `arg = [...]` passes the validator; **[D]** docs require `arg` binding and forbid string concatenation.
- **[V]** Workspace preference `sql_names: false` and instance flag `direct_query_access: true`. **[A]** With `sql_names: false`, physical PostgreSQL table names are likely internal identifiers rather than `survey_waves` etc., so raw SQL would have to reference generated names — fragile across environments (isolated tenant vs live).
- **Decision:** do not use raw SQL in V1. Serialize multi-row invariants by a **no-op self-update of the parent row** (`db.edit` on `survey_waves` / `insights` writing an unchanged field) as the first statement inside `db.transaction`, then re-read counts/state, then write. **[A]** This relies on Xano executing the transaction stack in one PostgreSQL transaction (row lock held until commit). Concurrency tests C01–C04 must prove it in the isolated environment before live deployment; if they fail, the fallback is accepting the residual single-owner race and documenting it.
- Unique-index races remain covered by the indexes themselves **[V]** (indexes live; violation-to-400 mapping **[A]**).

### R3.4 Endpoint count and reductions
Original inventory: **52 new** endpoints (+3 existing auth). Proposed reductions that keep every V1 workflow in docs/05 and docs/08:
| Change | Saves | Rationale |
|---|---|---|
| Drop A4 `GET session`; the frontend uses `GET auth/me` + `GET products` (403 ⇒ not owner) | 1 | No unique data |
| Merge D5/D6 into `POST survey-waves/{wave_id}/status` `{action: "close"|"reopen", closed_at?}` | 1 | One transition endpoint, same rules |
| Merge F5/F6 into `POST insights/{insight_id}/review-status` `{review_status}` | 1 | One transition endpoint, same rules |
| Fold E2 `pmf-history` into H1 overview as `waves[]` summaries | 1 | Overview already computes per-wave summaries |
**Recommended V1 count: 48 new endpoints.** Further cuts (e.g. dropping deletes) would remove the docs/05 "correct mistakes / confirm destructive actions" workflow and are not recommended.

### R3.5 Owner authorization in isolated testing
- The isolated environment has its own `user` table and its own environment variables **[D]** (tenant/sandbox docs: "own database, environment variables").
- Procedure: push schema + code → create two synthetic users (OWNER, INTRUDER) inside the isolated environment (temporarily enabling its signup endpoint, or adding rows in its database UI) → read OWNER's id via that environment's `auth/me` → set `PMF_OWNER_USER_ID` in that environment's env vars → run the suite. Live `PMF_OWNER_USER_ID` and the live owner account are never used for testing.
- `require_owner` code is identical in both environments; only the env value differs.

### R3.6 Error codes and naming — verification status
| Claim | Status |
|---|---|
| Missing/invalid token → 401 `ERROR_CODE_UNAUTHORIZED` | **[V]** live `GET auth/me` without token returned 401 |
| `precondition` error types `inputerror` 400, `accessdenied` 403, `notfound` 404, `standard` 500 | **[D]** docs; **[V]** syntax (existing `auth/login` uses `accessdenied`); HTTP status of each type at runtime **[A]** until tested |
| No native 409 | **[D]** (not listed among error types) |
| `canonical` unique per instance | **[D]**; `pmf-app` passes the validator **[V]**; collision only detectable by server dry-run (Goodz canonicals intentionally not inspected) |
| Route collision rule (wildcard vs literal, same verb) | **[D]**; inventory checked against it |
| `sensitive = true` masks inputs in logs | **[D]** |
| `active = false` disables an API group | **[D]** |

## R4. Testing isolation — read-only findings
| Option | Evidence | Isolated data | Receives schema/auth | Copies live records | Goodz impact | Cost / entitlement |
|---|---|---|---|---|---|---|
| **Ephemeral tenant** (`xano ephemeral …`) | **[V]** CLI 1.3.4 commands exist; `ephemeral list -w 2` → "No ephemeral tenants found"; create = `POST /api:meta/workspace/2/ephemeral` with name, `expires_hours` (1–24), description only (CLI source) | **[D]** tenants have their own database, env vars and configuration | Not from the create call; **[A]** contents pushed afterwards with `xano ephemeral push` (supported, dry-run available) | **[A]** none unless `--records` is pushed | None — workspace-scoped | **[V]** instance package `essential2`, add-on `tenants = 0`, tenant-center permissions present; **entitlement and price unknown** — a single create attempt would reveal entitlement; price must be checked in Xano billing first |
| **Account sandbox** (`xano sandbox …`) | **[D]** paid plans only (essential2 is paid); singleton per user; own env vars, unit/workflow tests; promote via browser review | Yes **[D]** | Via `sandbox push` | No, unless `--records` | **Risk:** account-level singleton; may currently hold a Goodz workspace; switching requires `sandbox reset`, which wipes it. `sandbox get` auto-creates. Not inspected. | Included in paid plans **[D]** |
| Data Source Environments | **[V]** add-on `data_sources = 0`; role permission only `workspace:datasource:live` | — | — | — | — | **Not available** without purchase **[A]** |
| API branch `dev` | **[D]** logic only; data shared with live | **No** | — | — | — | — |
| Workflow tests with `datasource = "live"` | **[D]** "clones entire datasource before each run"; **[V]** CLI help: tests "share the workspace database" | **Unproven** | — | clone of live | None | — |
| Second workspace (`pmf-test`) | **[V]** add-on `workspaces = 0`; plan workspace limit unknown | Yes | Full push | No | None | Unknown limit |
| Live `v1` with synthetic data | — | **No** | — | — | None | **Not recommended** |

**Write-guarantee rule for any option:** the HTTP test runner refuses to start unless its base URL host differs from the live host and matches the configured isolated host; credentials and env values come from runtime environment variables only, never Git.

**Promotion/discard:** the same Git sources are pushed to the isolated environment and, after the full matrix passes, to live `v1` (dry-run first). Test fixtures exist only in the isolated environment: an ephemeral tenant auto-expires (or is deleted on approval); a sandbox would be reset only with explicit owner approval.

**Preferred:** ephemeral tenant — workspace-scoped (no Goodz exposure), disposable, own DB/env/users, direct push supported. **Fallback:** sandbox, only after the owner confirms it holds no Goodz work. **No-go:** API branch alone, live synthetic data.

## R5. Final shared-function inventory (34)
`pmf/auth/require_owner`; `pmf/access/{product, segment, customer, interview, wave, participation, insight, evidence, hypothesis, experiment}`; `pmf/integrity/{segment_in_product, customer_in_product}`; `pmf/text/{normalize, is_blank}`; `pmf/db/unique_error`; `pmf/lock/{wave, insight}` (no-op self-update); `pmf/survey/{wave_state, assert_wave_open, assert_definition_unlocked, validate_response, participation_status}`; `pmf/report/{count_wave, compute_pmf, comparability, build_wave_report}`; `pmf/evidence/{validate_source, source_summary}`; `pmf/insight/{count_valid_evidence, assert_reviewed}`; `pmf/validation/{validate_experiment, validate_hypothesis_status}`; `pmf/guard/count_references`.
(Replaces §3 `pmf/lock/row`, which depended on raw SQL.)

## R6. Changes to the original plan
- Endpoint count 52 → 48 (R3.4).
- Lock mechanism: raw SQL removed (R3.3).
- U10 adds one expected UPDATE (`auth/login`) to the live dry-run; every other expected operation is a CREATE.
- Hypothesis and timestamp rules refined (R3.1, R3.2).

## R7. Approvals required, in order
1. Approve R2 recommendations and decide U9 (threshold) — then record them in DECISION_LOG.
2. Owner checks Xano billing/plan for ephemeral-tenant entitlement and price (read-only, UI).
3. Approve **one** feasibility action: `xano ephemeral create "pmf-api-test" --expires-hours 2 -p pmf -w 2` (creates a billable-or-included, auto-expiring tenant). Alternative: owner confirms the sandbox is unused by Goodz, then approves `sandbox get` / `sandbox reset`.
4. Approve pushing schema + API sources and synthetic users/env var into that isolated environment only.
5. Approve Git feature branch `feat/api-v1` for implementation sources.
6. Owner sets live `PMF_OWNER_USER_ID` in the Xano UI before live deployment.
7. Temporary live `allow_push` for the dry-run; separately approved interactive live push; push disabled and CLI-verified afterwards.

---

# Appendix R8 — Owner-Approved Design (2026-10-22, supersedes R2–R7 where different)

## R8.1 Approved design rules
| ID | Approved rule |
|---|---|
| U1 | Designated owner = workspace env var `PMF_OWNER_USER_ID` (set in the Xano UI from the owner's own `auth/me` id). Every business endpoint calls `pmf/auth/require_owner` first: unset/blank → 500 `OWNER_NOT_CONFIGURED`; mismatch → 403. `products.owner_user_id` is always server-set and checked by every access loader. Never in Git, never client-supplied. |
| U2 | Isolated testing environment required before any write test (see R8.4); live `v1` is never used for write tests. |
| U3 | One API group `PMF App`, canonical `pmf-app`. |
| U4 | Interview raw text (`notes`, `transcript`, `existing_alternatives`, `problem_context`) and survey answers (`invited_at` excluded) are immutable once cited by any evidence row; a cited response cannot be cleared. |
| U5 | Reviewed insight: `type`/`statement` edits revert to draft when no hypotheses exist, otherwise 400. |
| U6 | Reviewed → draft blocked when hypotheses exist. |
| U7 | Hypothesis transitions per R3.1; no automatic status changes. |
| U8 | No product delete; deletes restricted when referenced; concluded experiments (conclusion or decision set) not deletable; participations deletable only when unanswered, uncited and wave open. |
| U9 | `SMALL_SAMPLE` warning when the selected scope has **fewer than 30 valid responses**. Informational only; never a statistical claim, PMF threshold or score modifier. |
| U10 | **Existing `auth/login`, `auth/me`, `auth/signup` are NOT modified.** Owner authorization is enforced on every business endpoint instead. The live dry-run must therefore show **zero UPDATEs**. |
| U11 | `PMF App` group request history minimized (`history = 0`, runtime effect to verify); every input carrying interview, survey-answer or evidence text is `sensitive = true`. |
| U12 | `page` default 1; `per_page` default 25, max 100. |
| U13 | Parent-row locking (no-op self-update inside `db.transaction`) is **provisional**. It is accepted for critical invariants only after isolated concurrency tests C01–C04 pass; a failed strategy is not acceptable and blocks deployment. |
| U14 | Historical timestamps allowed. `interviews.conducted_at` ≤ now + 5 minutes. Survey: `started_at ≤ responded_at ≤ now + 5 minutes` (clock-skew tolerance), `invited_at ≤ responded_at` when both set, actual historical response times preserved. `closed_at` optional on close: ≥ latest `responded_at`, ≤ now. |
| Evidence | Survey evidence requires `source_field` ∈ {`beneficiary_description`, `main_benefit`, `improvement_request`}, non-blank on the cited row, and `responded_at` set. Interview evidence: `source_field` optional; when given ∈ {`notes`, `transcript`, `existing_alternatives`, `problem_context`} and non-blank; when omitted the interview must have at least one non-blank raw field. Evidence source ids are immutable. |
| PATCH | Optional fields: omitted/null = unchanged. Nullable fields are cleared only via an explicit `clear: text[]` input listing field names (validated against an allow-list). Blank founder text normalizes to null. |

## R8.2 Conditions still requiring verification (not approved as working)
1. Isolated environment availability, entitlement and cost (ephemeral tenant preferred; sandbox only if unused by Goodz).
2. `db.transaction` executes as one PostgreSQL transaction and the parent no-op update holds a row lock until commit (C01–C04).
3. Runtime HTTP status for `inputerror`/`accessdenied`/`notfound`/`standard`; behavior of `throw` names.
4. Unique-index violation behavior inside transactions (expected: transaction aborts; error surfaced).
5. `history = 0` effect on request history; masking of `sensitive` inputs.
6. Canonical `pmf-app` free at instance level (server dry-run).
7. `$env` value type (string) and `|to_int` comparison.
8. `output = [...]` projections on `db.query` honored at runtime.

## R8.3 Final endpoint inventory (48)
| # | Verb | Route |
|---|---|---|
| 1 | GET | `products` |
| 2 | POST | `products` |
| 3 | GET | `products/{product_id}` |
| 4 | PATCH | `products/{product_id}` |
| 5 | GET | `products/{product_id}/segments` |
| 6 | POST | `products/{product_id}/segments` |
| 7 | PATCH | `segments/{segment_id}` |
| 8 | DELETE | `segments/{segment_id}` |
| 9 | GET | `products/{product_id}/customers` |
| 10 | POST | `products/{product_id}/customers` |
| 11 | GET | `customers/{customer_id}` |
| 12 | PATCH | `customers/{customer_id}` |
| 13 | DELETE | `customers/{customer_id}` |
| 14 | GET | `customers/{customer_id}/interviews` |
| 15 | POST | `customers/{customer_id}/interviews` |
| 16 | GET | `interviews/{interview_id}` |
| 17 | PATCH | `interviews/{interview_id}` |
| 18 | DELETE | `interviews/{interview_id}` |
| 19 | GET | `products/{product_id}/survey-waves` |
| 20 | POST | `products/{product_id}/survey-waves` |
| 21 | GET | `survey-waves/{wave_id}` |
| 22 | PATCH | `survey-waves/{wave_id}` |
| 23 | DELETE | `survey-waves/{wave_id}` |
| 24 | POST | `survey-waves/{wave_id}/status` (`action`: close/reopen) |
| 25 | GET | `survey-waves/{wave_id}/participations` |
| 26 | POST | `survey-waves/{wave_id}/participations` |
| 27 | PATCH | `participations/{participation_id}` |
| 28 | DELETE | `participations/{participation_id}` |
| 29 | GET | `survey-waves/{wave_id}/report` |
| 30 | GET | `products/{product_id}/insights` |
| 31 | POST | `products/{product_id}/insights` |
| 32 | GET | `insights/{insight_id}` |
| 33 | PATCH | `insights/{insight_id}` |
| 34 | DELETE | `insights/{insight_id}` |
| 35 | POST | `insights/{insight_id}/review-status` |
| 36 | POST | `insights/{insight_id}/evidence` |
| 37 | PATCH | `evidence/{evidence_id}` |
| 38 | DELETE | `evidence/{evidence_id}` |
| 39 | GET | `products/{product_id}/hypotheses` |
| 40 | POST | `insights/{insight_id}/hypotheses` |
| 41 | GET | `hypotheses/{hypothesis_id}` |
| 42 | PATCH | `hypotheses/{hypothesis_id}` |
| 43 | DELETE | `hypotheses/{hypothesis_id}` |
| 44 | POST | `hypotheses/{hypothesis_id}/experiments` |
| 45 | PATCH | `experiments/{experiment_id}` |
| 46 | DELETE | `experiments/{experiment_id}` |
| 47 | GET | `products/{product_id}/overview` (includes `waves[]` PMF summaries) |
| 48 | GET | `products/{product_id}/lookups` |
Existing and unchanged: `POST auth/login`, `GET auth/me`, `POST auth/signup` (External Access off).

## R8.4 Final shared-function inventory (34)
`pmf/auth/require_owner`; `pmf/access/{product, segment, customer, interview, wave, participation, insight, evidence, hypothesis, experiment}`; `pmf/integrity/{segment_in_product, customer_in_product}`; `pmf/text/{normalize, is_blank}`; `pmf/util/patch_data`; `pmf/lock/{wave, insight}`; `pmf/survey/{wave_state, assert_wave_open, assert_definition_unlocked, validate_response, participation_status}`; `pmf/report/{count_wave, compute_pmf, comparability, build_wave_report}`; `pmf/evidence/{validate_source, source_summary}`; `pmf/insight/{count_valid_evidence, assert_reviewed}`; `pmf/validation/{validate_experiment, validate_hypothesis_status}`; `pmf/guard/count_references`.
Change vs R5: `pmf/db/unique_error` replaced by `pmf/util/patch_data` (duplicates are pre-checked; index violations surface as transaction errors). `pmf/report/count_wave` is pure (aggregates rows already loaded by `build_wave_report`).

## R8.5 Test safety protocol (updated after source hardening at `5905671`)

**Status:** source guard and offline tests implemented, but ephemeral-tenant identity/URL semantics and all HTTP requests remain unverified against Xano. The test runner must refuse unknown tenant configurations rather than relax safety checks.

1. **Pure URL configuration:** HTTPS only; no embedded credentials, unexpected ports, queries or fragments; hard-deny the known live host; business path must be exactly `/api:pmf-app` or `/api:pmf-app:<branch>`. Authentication URL must use `/api:<auth-canonical>[:branch]` on the same host and branch. Tenant-specific path prefixes are not documented and are therefore refused until verified with Xano. `PMF_TEST_ENV_HOST` is **retired**; do not use operator-typed host strings as an identity guarantee.
2. **Authoritative ephemeral identity:** the suite reads `xano ephemeral get <name> -p pmf -w 2 -o json` before requests. Metadata must contain the selected name, valid `ephemeral_expires_at` with at least 10 minutes left, a usable state, and `xano_domain`; the test host must match that tenant's domain and must not equal the live host. Field shapes/URL format require first-tenant verification.
3. **Read-only canary:** `GET auth/me` must identify two distinct synthetic users with `@pmf-test.invalid` email values; the owned product list must be complete on one page (at most 100 records) and contain only `SYNTH-`-prefixed names.
4. **Restricted HTTP client:** requests may use only the 48 approved business routes and `GET auth/me`, only on the verified host. Do not follow redirects.
5. **Security sweep gate:** S01 (without a token) and S02 (as a non-owner) always run, even with `--only`. A failure aborts before creating the normal synthetic fixture. These sweeps use real HTTP methods and could write if authorization is broken; run them **only in the isolated tenant**, never in live.
6. **Concurrency gate U13:** C01–C04 use fresh records per trial and a synchronized release (default 25, minimum 10 trials). Fail on any broken final-state invariant, request error or insufficient client-side overlap (less than 80%). Client overlap alone is not proof of server overlap. In the isolated tenant, a reviewed **negative-control variant without locks** must expose at least one C02–C04 race violation; restore the production-intended lock implementation before any further full-suite run. Never run the negative-control variant against live.
7. **Evidence:** Offline results (49/49 unit tests and 18/18 static negative controls, reported at `5905671`) validate the test harness and implementation shape only. Xano runtime tests, inline unit tests, ownership, rollback, enum behavior and transaction/locking semantics remain pending.

**Implementation source:** `feat/api-v1` at `5905671d70b2377f2d69add4c43d1474aa17c015`, particularly `tests/api/{safety.py,http_client.py,concurrency.py,pmf_api_tests.py}` and `tests/README.md`. Deployment is still unauthorized.

## R8.6 Approvals still required
- **Current status:** 48 endpoints and 34 functions prepared on `feat/api-v1`; no Xano endpoints/functions/tenants added; live workspace `pmf` has ten business tables and three existing auth APIs only. Direct push was unexpectedly reported **true** in the latest read; user must disable it and verify the CLI returns `allow_push: false` before further changes.
- **Next gate:** read-only Xano Billing/plan confirmation of ephemeral-tenant entitlement and price. No charge-creating action or tenant creation is approved by this document.
- **Later separate approvals:** one time-limited isolated-tenant creation; schema/auth/API push into that tenant only; fixture accounts/env; full runtime test suite and concurrency negative control; merging reviewed sources; setting live owner env var; live dry-run; separately approved interactive push; CLI-verified push disabled afterwards.
- Existing `auth/login`, `auth/me`, `auth/signup` remain unchanged (U10).
