# PMF Engine — Project Context

_Last updated: 2026-10-23. Source of truth for implementation handoffs._

## Mission
Build a personal-use web application that helps a founder systematically discover and improve software product-market fit (PMF). It connects original customer evidence to research findings, testable hypotheses, experiments, and decisions. It is not merely a survey dashboard.

## Origin and references
The idea combines Eric Migicovsky's Y Combinator talk on customer interviews with Rahul Vohra's published Superhuman PMF engine. Read [Research & References](docs/02-RESEARCH_AND_REFERENCES.md).

## Current status
- GitHub repository: https://github.com/jperaleselizondo-hash/pmf (private).
- **Backend (Xano `pmf`, workspace 2, branch `v1`):** 10 business tables and the `PMF App` API (48 endpoints, 34 functions) are live and passed automated QA on 2026-10-23 (unit 66/0, HTTP 64/64). Tables are empty. See [Backend handoff](docs/BACKEND_HANDOFF.md).
- **Frontend:** not started; WeWeb vs coded frontend on Vercel is undecided.
- **Project paused** after backend QA until after the Goodz launch. Outstanding owner actions are listed in the handoff.

## Approved direction
- **Audience:** one owner/operator for the first release; not a multi-tenant SaaS.
- **Stack:** Xano database/auth/backend is selected; frontend is **undecided** between WeWeb and a coded frontend deployed on Vercel. Do not start frontend work or commit to a framework yet.
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
Read this file, [CLAUDE.md](CLAUDE.md), [PROJECT_STATUS](docs/PROJECT_STATUS.md), [DECISION_LOG](docs/DECISION_LOG.md), and whichever functional spec is relevant. Compare repository statements with actual connected Xano resources; the frontend (WeWeb vs coded app on Vercel) is intentionally undecided. Do not assume that documentation implies deployment.
