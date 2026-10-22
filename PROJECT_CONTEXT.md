# PMF Engine — Project Context

_Last updated: 2026-10-22. Source of truth for implementation handoffs._

## Mission
Build a personal-use web application that helps a founder systematically discover and improve software product-market fit (PMF). It connects original customer evidence to research findings, testable hypotheses, experiments, and decisions. It is not merely a survey dashboard.

## Origin and references
The idea combines Eric Migicovsky's Y Combinator talk on customer interviews with Rahul Vohra's published Superhuman PMF engine. Read [Research & References](docs/02-RESEARCH_AND_REFERENCES.md).

## Current status
- GitHub repository: https://github.com/jperaleselizondo-hash/pmf (private).
- **Design baseline:** initial system logic and technology-independent 10-table model are documented.
- **Implementation:** not started. No Xano tables, APIs, credentials, WeWeb pages, or MCP edits have been made for this project.
- **Next task:** inspect available Xano/WeWeb workspaces and MCP access, then propose a physical Xano schema implementing the documented logical model. Obtain approval before backend or frontend mutations.

## Approved direction
- **Audience:** one owner/operator for the first release; not a multi-tenant SaaS.
- **Stack:** Xano database/auth/backend + WeWeb frontend.
- **Developer workflow:** discuss scope with ChatGPT; Claude Code in Cursor inspects docs and tools, proposes a narrow change, executes when approved, and reports evidence; human reviews and decides what to do next.
- **Data:** start with manual entry of customers, interviews, survey participation/responses, insights, hypotheses, and experiments.
- **Model:** 10 business tables across Market, Research, Intelligence, Validation. Xano's required authentication infrastructure is outside the 10.
- **PMF:** measure percent of eligible, valid respondents selecting "very disappointed"; segment and cohort denominators must remain visible. PMF score is an indicator, not proof.
- **Safety:** no secrets or raw customer datasets in GitHub; no production writes/publish without explicit approval.

## Canonical documents
1. [Problem / vision](docs/01-PROBLEM_AND_VISION.md)
2. [Research / references](docs/02-RESEARCH_AND_REFERENCES.md)
3. [PMF system logic](docs/03-PMF_SYSTEM_LOGIC.md)
4. [Logical data model](docs/04-LOGICAL_DATA_MODEL.md)
5. [MVP web app](docs/05-MVP_WEB_APP.md)
6. [Technical architecture](docs/06-TECHNICAL_ARCHITECTURE.md)
7. [Implementation sequence](docs/07-IMPLEMENTATION_PLAN.md)
8. [Test plan](docs/08-TEST_PLAN.md)
9. [Decisions](docs/DECISION_LOG.md)
10. [Current status](docs/PROJECT_STATUS.md)

## Definition of first useful release
From the private web UI, the owner can create a product/segment/customer, record an interview, run or manually register a PMF survey wave with eligible participants and responses, inspect an accurate denominator-based PMF breakdown, link an insight to original evidence, create a hypothesis/experiment, and capture its result.

## Scope guardrails
Do not implement organization accounts, automated surveys, product event ingestion, monetization, background AI agents, or public collaboration in V1. Future phases can integrate analytics and commercial validation while preserving the evidence → hypothesis → experiment chain.

## For any new Claude session
Read this file, [CLAUDE.md](CLAUDE.md), [PROJECT_STATUS](docs/PROJECT_STATUS.md), [DECISION_LOG](docs/DECISION_LOG.md), and whichever functional spec is relevant. Compare repository statements with actual connected Xano/WeWeb environments rather than assuming that documentation implies deployment.
