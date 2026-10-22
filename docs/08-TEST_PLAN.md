# 08 — V1 Test Plan

Use only synthetic example customers and responses until access/retention practices are agreed.

## Identity and access
- Unauthenticated API requests fail; non-authenticated WeWeb visitor cannot view data.
- Unauthorized product IDs and forged related record IDs do not bypass owner/product checks.
- API credentials never appear in repository or public client configuration.

## Market and research
- Product A's segment cannot be assigned to Product B's customer.
- Prospects can be entered without an existing software account or email.
- An interview belongs to one customer; later edits to insights do not overwrite raw interview notes.
- A product/customer with referenced evidence cannot be destructively deleted without the designed safeguard.

## Surveys / scoring
Fixture: Product A, Wave 1: 5 eligible; 4 invited; 3 valid responses (1 very, 1 somewhat, 1 not); 2 not responded.

Expected: eligible=5, invited=4, valid=3, very=1, PMF=33.333...%. Nonrespondents are excluded from PMF denominator. Response rate among invited recipients must reflect whether the valid replies were invited rather than assuming every reply was emailed.

- Duplicate (wave_id, customer_id) must fail.
- Survey customer from another product must fail.
- A completed response without a valid disappointment category must not count.
- Wave with no valid responses returns PMF=null and sample=0.
- Segment filtering uses segment_id_snapshot, not customer's current segment_id.
- A segment move after invitation leaves historical reports unchanged.
- Percentage calculation does not truncate integer division.
- Closed wave prevents inappropriate edits under defined rules, if locking is enabled.
- Repeated survey respondent appears in cross-wave history and must be flagged for longitudinal interpretation.

## Insight provenance
- Evidence row requires exactly one source FK.
- Source from another product fails.
- Reviewer cannot mark a source-less insight as reviewed.
- Evidence displays both supports and contradicts relationships.
- Hypothesis points to an existing insight; experiment to an existing hypothesis.

## End-to-end founder scenario
1. Log in.
2. Create one product and two segments.
3. Create prospect and active customers, then interviews.
4. Create survey wave and participants, answer a subset.
5. Inspect score overall and by segment.
6. Create reviewed insight with excerpts from different source records.
7. Create a measurable hypothesis and an experiment.
8. Record observed outcome and decision.
9. Reload and verify original and derived records still link correctly.

## Release evidence
For each test record expected vs actual, endpoint/page, test environment, date, and any failure/rollback. Production publication requires a separate explicit authorization.
