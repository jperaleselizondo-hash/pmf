# 04 — Technology-Independent Relational Data Model (V1)

## Scope
Ten **business-domain** tables, four domains. Xano platform authentication records are not included in the ten. Use stable primary keys and foreign keys; timestamps are UTC. Field types below are conceptual, not finalized Xano physical types.

## A. Market
### 1. products
| Field | Type | Meaning |
| --- | --- | --- |
| id | identifier, PK | Product |
| name | short text, required | Name |
| description | long text | Description |
| core_value | long text | Main value hypothesis |
| activation_definition | long text | What activation would mean |
| value_event_definition | long text | What realized customer value would mean |
| created_at | timestamp | Created |

### 2. segments
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Segment |
| product_id | FK → products, required | Belongs to product |
| name | short text, required | Segment label |
| description | long text | Target customer |
| criteria | long text | Inclusion rules |
| created_at | timestamp | Created |

### 3. customers
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Individual person |
| product_id | FK → products, required | Product |
| segment_id | FK → segments, nullable | Primary current segment |
| external_id | text, nullable | Optional external product/user reference |
| name | text, nullable | Person |
| email | text, nullable | Contact |
| company_name | text, nullable | Organization name (no organizations table yet) |
| lifecycle_stage | enum | prospect / active / former |
| created_at | timestamp | Created |

## B. Research
### 4. interviews
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Interview |
| customer_id | FK → customers, required | Interviewee |
| conducted_at | timestamp, required | When held |
| notes | long text | Raw original notes |
| transcript | long text, nullable | Optional verbatim content |
| existing_alternatives | long text | Current workaround/solution |
| problem_context | long text | Past incident and consequences |
| created_at | timestamp | Created |

### 5. survey_waves
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Survey round |
| product_id | FK → products, required | Product |
| name | text, required | Round name |
| eligibility_rule | long text, required | Exposure/eligibility criteria fixed for wave |
| questionnaire_version | text, required | Question wording version |
| started_at | timestamp | Start |
| closed_at | timestamp, nullable | End |
| created_at | timestamp | Created |

### 6. survey_participations
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Person in a wave, including nonrespondents |
| survey_wave_id | FK → survey_waves, required | Wave |
| customer_id | FK → customers, required | Qualified participant |
| segment_id_snapshot | FK → segments, nullable | Primary segment **at qualification** |
| invited_at | timestamp, nullable | Invitation |
| responded_at | timestamp, nullable | Completed response |
| disappointment_level | enum, nullable | very / somewhat / not |
| beneficiary_description | long text, nullable | Who benefits? |
| main_benefit | long text, nullable | Main value? |
| improvement_request | long text, nullable | What could improve? |
| created_at | timestamp | Qualified/recorded |

**Unique:** (survey_wave_id, customer_id). When a wave is created, its eligible set is recorded explicitly; membership alone does not count as a completed response.

## C. Intelligence
### 7. insights
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Finding |
| product_id | FK → products, required | Product |
| segment_id | FK → segments, nullable | Target segment |
| type | enum | problem / benefit / obstacle / customer_characteristic |
| statement | long text, required | Interpreted finding |
| confidence | enum | low / medium / high |
| review_status | enum | draft / reviewed |
| created_at | timestamp | Created |

### 8. insight_evidence
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Evidence link |
| insight_id | FK → insights, required | Finding |
| interview_id | FK → interviews, nullable | Source interview |
| survey_participation_id | FK → survey_participations, nullable | Source response |
| source_field | text, nullable | Specific survey answer, e.g. main_benefit |
| excerpt | long text, required | Verifiable observation |
| relationship | enum | supports / contradicts |
| created_at | timestamp | Created |

**XOR rule:** exactly one of interview_id or survey_participation_id must be non-null. An excerpt must accurately match or summarize the source; when possible retain verbatim text.

## D. Validation
### 9. hypotheses
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Testable proposal |
| insight_id | FK → insights, required | Primary supporting insight |
| statement | long text, required | Proposed causal explanation/change |
| expected_outcome | long text, required | Anticipated behavior/result |
| success_metric | text, required | Measurement definition |
| priority | enum | low / medium / high |
| status | enum | proposed / testing / validated / rejected |
| created_at | timestamp | Created |

### 10. experiments
| Field | Type | Meaning |
| --- | --- | --- |
| id | PK | Validation activity |
| hypothesis_id | FK → hypotheses, required | Tested hypothesis |
| name | text, required | Experiment |
| method | text, required | Interview, prototype, feature test, etc. |
| started_at | timestamp, nullable | Start |
| ended_at | timestamp, nullable | End |
| baseline | long text | Prior result/measurement |
| target | long text | Defined expected result |
| observed_result | long text | What actually happened |
| conclusion | enum, nullable | supported / refuted / inconclusive |
| decision | enum, nullable | adopt / iterate / reject / investigate |
| notes | long text | Method and limitations |
| created_at | timestamp | Created |

## Relationships / cardinality
| Parent → Child | Cardinality |
| --- | --- |
| products → segments, customers, survey_waves, insights | each 1:N |
| segments → customers | 1:N, optional customer assignment |
| customers → interviews, survey_participations | each 1:N |
| survey_waves → survey_participations | 1:N |
| insights → insight_evidence, hypotheses | each 1:N |
| interviews → insight_evidence | 1:N |
| survey_participations → insight_evidence | 1:N |
| hypotheses → experiments | 1:N |

One source can support several insights; an insight can cite several sources. This is modeled with insight_evidence, not free-text source IDs.

## Critical integrity invariants
1. All paths refer to the **same product**: customer.segment.product = customer.product; participation.customer.product = wave.product; evidence source product = insight.product; insight.segment.product = insight.product.
2. A segment snapshot is assigned at eligibility; it never automatically updates when current segment changes.
3. A qualified completed response has responded_at AND a valid disappointment_level. Incomplete responses are reported separately and never enter the score.
4. Only one participation per (wave, customer); duplicates must be rejected.
5. An evidence link has exactly one source FK (interview OR survey participation) and a meaningful excerpt.
6. Reviewed insight must have at least one evidence link. A hypothesis references an insight.
7. Historical waves are not silently reinterpreted when questionnaire/eligibility criteria change.
8. Delete policy: use deliberate cascade/restrict rules. For V1, **restrict deletion of records referenced by evidence/hypotheses**, and confirm destructive deletion elsewhere; preserve provenance.
9. External IDs may be null. If present, avoid duplicates within the same product.
10. All reads and writes require authenticated owner authorization in the API.

## Key analytical queries (logical)
- Wave PMF: count valid responses by disappointment_level; percentage very / all valid; 0 denominator => N/A.
- Segmented wave PMF: same, filtering segment_id_snapshot.
- Survey funnel: eligible → invited → responded; distinguish invited response rate from manually entered responses.
- Insight detail: all supporting/contradicting excerpts and their source customer/date.
- Hypothesis history: related insight, experiments, outcomes, and recorded decisions.

## Explicitly deferred
No organizations, users/roles domain, product_events, metrics, billing, AI classifications, cohorts, audit event store, or automated surveys. These may be added later without invalidating the evidence chain.
