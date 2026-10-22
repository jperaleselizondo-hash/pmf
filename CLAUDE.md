# Claude Code — Working Agreement

This repo is the specification and development record for a **personal-use PMF Engine web app** (Xano backend; frontend decision between WeWeb and a Vercel-hosted coded app is deferred).

## At the start of each session
1. Read PROJECT_CONTEXT.md, docs/PROJECT_STATUS.md, docs/DECISION_LOG.md, and the relevant specification.
2. Inspect repository branch, working tree, and remote before touching files.
3. Discover actual connected Xano MCP capabilities and identify the Xano workspace named `pmf` by observed identifiers. Frontend tool discovery is deferred until frontend selection. Never assume a connection, token, workspace ID, or operation exists because it is planned.
4. Clearly distinguish what is documented, what is implemented, what was tested, and what is live.

## Change discipline
- Default to read-only inspection and a scoped proposal first.
- Obtain explicit approval before modifying Xano schema/data/endpoints, frontend resources, credentials, or production settings.
- Prefer a verified Xano development branch and, later, frontend preview environments. Never publish, merge, or deploy without approval.
- Make one small, testable change at a time. Show expected affected resources before edits.
- After changes, verify the actual state, capture test evidence, and state exactly what changed.
- Do not overwrite unrelated work or claim success based solely on MCP write responses.
- Use native Xano constructs observed in the actual `pmf` workspace rather than inventing tool parameters or IDs. Choose frontend conventions only after the later frontend decision.

## Architecture rules
- One private/admin user in V1. Authentication and authorization are mandatory.
- The 10 tables in docs/04-LOGICAL_DATA_MODEL.md are logical business entities; Xano system auth tables are separate.
- Enforce same-product ownership across related records; never trust a client-supplied product ID as authorization.
- Keep customer statements separate from derived interpretations.
- Preserve participant eligibility and segment snapshots for historical survey analysis.
- PMF score denominator = eligible valid respondents in the specified wave/segment, NOT invitations or all contacts.
- Do not silently recalculate old cohorts under new criteria.
- Evidence links identify the precise source record and whether it supports or contradicts the insight.

## Secrets, privacy, releases
- Never store tokens, API keys, passwords, customer exports, or real transcripts in GitHub.
- Limit personal data collection; protect interviews and survey responses behind auth.
- Use synthetic test data wherever possible.
- Record any irreversible operation or production risk before execution.
- Ask for approval if anything would materially increase scope.

## End-of-task report format
Provide: (1) baseline/branch, (2) exact files/resources modified, (3) observed tests and results, (4) risks/limitations, (5) commit/version and publish status, (6) next recommended small task. Update docs/PROJECT_STATUS.md and docs/DECISION_LOG.md for approved durable changes, without claiming undocumented work is finished.
