# 06 — Technical Architecture: Xano + Frontend TBD + Claude

## Responsibility boundaries
| Component | Responsibility |
| --- | --- |
| Xano | Persistent relational records, authentication, authorization, validation, read/write APIs, PMF aggregation |
| Frontend (TBD) | Private frontend navigation, forms, details, survey interface, results and error states. Options: WeWeb, or coded app deployed on Vercel |
| Claude Code (Cursor) | Inspect and implement approved scopes via repository and connected MCP tooling |
| GitHub pmf repo | Documentation, decisions, implementation record; later code/config exports where feasible |

The 10 business tables are from [Logical Data Model](04-LOGICAL_DATA_MODEL.md). Xano's authentication/user system is required but is **not** counted among these ten.

## Data flow
Authenticated owner in frontend → Xano API → relational business tables.

Xano returns raw resources and calculated report payloads. Whichever frontend we select will display them but must not authoritatively calculate PMF, set eligibility, authorize access, or enforce foreign-key semantics.

## Authentication and authorization
- Use Xano's supported authentication mechanisms, confirmed from the workspace during implementation.
- All application endpoints are authenticated; restrict usage to the owner initially.
- Validate record ownership/product consistency on the server even if frontend controls are hidden.
- Never rely on a product_id from an untrusted request as proof of access.
- Keep API tokens and environment secrets in tool/project secret stores, never in Git.

## API contract (logical proposal, not yet implemented)
| Domain | Minimum operations |
| --- | --- |
| Products / segments | List, detail, create, update |
| Customers | List/search, detail, create, update |
| Interviews | List per customer, detail, create, update |
| Survey waves | List, detail, create; close wave |
| Survey participations | List eligible, add unique participant, invite timestamp, submit/update response |
| Insights and evidence | List, detail, create/update insight, attach/remove source links, review |
| Hypotheses / experiments | CRUD with linked records and outcome capture |
| PMF report | Wave summary: eligible, invited, valid responses, counts by category, score, segmented breakdowns |

Use the real workspace's API naming conventions when implementing. No endpoint paths above are a claim that corresponding endpoints exist.

## Core report response (illustrative)
~~~json
{
  "wave_id": 42,
  "segment_id": null,
  "eligible_count": 20,
  "invited_count": 18,
  "valid_response_count": 10,
  "very_count": 4,
  "somewhat_count": 5,
  "not_count": 1,
  "pmf_percent": 40.0,
  "questionnaire_version": "v1"
}
~~~
This is hypothetical example data, not actual product measurements. An empty denominator returns pmf_percent: null.

## Claude / MCP collaboration
1. Have Claude read PROJECT_CONTEXT.md, CLAUDE.md, status and logical schema.
2. Inspect connected Xano MCP capabilities and workspace `pmf` **read-only**. Frontend tool inspection is deferred.
3. Compare real capabilities with this specification and propose a physical schema/API delta.
4. Human approves the exact change scope.
5. Implement first in dev/unpublished environments, using the APIs and component IDs observed.
6. Test CRUD and calculated results against controlled synthetic fixtures.
7. Report affected resources, evidence, risks, revision identifiers and publish status.
8. Commit durable documentation updates after approved changes.

If a needed MCP connector or write action is missing, stop at the verified boundary; do not pretend a task was completed. Manual console actions can be documented as explicit instructions for the user.

## Environments and deployment
- Prefer separate Xano development and production states; record actual workspace/branch naming after inspection.
- Frontend decision is deferred: WeWeb is a visual builder; Vercel is a hosting/deployment platform, so a Vercel route also needs a chosen frontend framework/codebase. Prefer preview environments; any deployment is separately approved.
- Maintain a rollback plan before destructive changes.
- Start with a manually operated private app; avoid scheduled jobs/background automations until needed.
- Treat survey answers and interview notes as potentially identifying: minimize data, protect access, and provide deletion/export handling appropriate to actual use.

## Deferred integrations
Telemetry (e.g., Mixpanel), billing, email surveys, file uploads, AI tagging and recommendations are later phases. Do not introduce integration tables without a real data contract and use case.
