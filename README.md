# PMF Engine

A private, personal-use web application to discover, measure, and improve software product-market fit (PMF) through traceable customer evidence, surveys, insights, hypotheses, and experiments.

**Status:** Documentation/design phase — the owner has created a Xano workspace named `pmf`, but its schema and MCP connectivity have not yet been verified; no frontend has been built.

## Project documents

Start with [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md). Claude Code should also read [CLAUDE.md](CLAUDE.md) before any implementation.

| Document | Purpose |
| --- | --- |
| [Problem & vision](docs/01-PROBLEM_AND_VISION.md) | Why the product should exist, who it serves, and scope |
| [Research & references](docs/02-RESEARCH_AND_REFERENCES.md) | YC customer interviews, Superhuman PMF methodology, caveats |
| [PMF system logic](docs/03-PMF_SYSTEM_LOGIC.md) | Seven modules, workflow, calculations, and decision rules |
| [Relational data model](docs/04-LOGICAL_DATA_MODEL.md) | Initial 10-table logical schema, relationships, and integrity rules |
| [MVP web app](docs/05-MVP_WEB_APP.md) | User workflows, pages, and acceptance criteria |
| [Technical architecture](docs/06-TECHNICAL_ARCHITECTURE.md) | Xano backend, frontend options, authentication, APIs, and Claude MCP workflow |
| [Implementation plan](docs/07-IMPLEMENTATION_PLAN.md) | Phases, sequencing, gates, and next actionable tasks |
| [Test plan](docs/08-TEST_PLAN.md) | Minimum end-to-end and data integrity test cases |
| [Decision log](docs/DECISION_LOG.md) | Decisions and deferred tradeoffs |
| [Project status](docs/PROJECT_STATUS.md) | Current baseline and immediate next step |

## Guiding rule

**Customer → Original evidence → Reviewed insight → Testable hypothesis → Experiment → Learning.**

The product should preserve this traceability without confusing customer opinions, product usage, and commercial proof.

## Planned tools

- **Xano:** relational database, authentication, backend API, computed PMF statistics
- **Frontend (decision deferred):** WeWeb builder or a coded web app deployed on Vercel; choose after Xano backend work.
- **Claude Code in Cursor:** implementation support through available MCP integrations and repository documentation
- **GitHub:** source of truth for project decisions, specifications, and eventually source/configuration artifacts

Nothing in this repository should contain API credentials, customer personal data exports, or production secrets.
