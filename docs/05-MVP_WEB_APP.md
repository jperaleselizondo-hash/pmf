# 05 — Personal-Use Web App Specification

## Target user and navigation
One authenticated owner. No public content or tenant administration.

Suggested frontend navigation (implementation technology TBD):
- Overview
- Market (Products / Segments)
- Customers
- Research (Interviews / PMF Surveys)
- Insights
- Validation (Hypotheses / Experiments)

Desktop-first is acceptable for initial release, but main read/create flows should remain usable on mobile.

## Screens and minimum tasks

### Overview
Select a product; see customer count, latest wave, eligible/invited/responded counts, PMF score with sample denominator, and recent experiments. Empty state should explain the next useful action. Never fabricate charts or historical trends.

### Market
Create/edit a product and segments. Capture core_value, activation_definition, and value_event_definition as qualitative definitions (not live tracking).

### Customers
Create, search, filter, and edit a prospect/active/former customer. Optional segment and contact details. Customer detail shows interviews and survey participations. Warn about sensitive data collection.

### Interviews
Add date, interviewee, raw notes, past incidents, workarounds, and optional transcript. Preserve original wording separately from later interpretation.

### PMF Surveys
Create a survey wave with frozen eligibility rule and questionnaire version. Add eligible customers (unique per wave), record optional invitations and their four Superhuman responses. Display raw responses and qualified PMF analysis overall/filtered by snapshotted segment.

### Insights
Create an insight type/statement/confidence; attach interview or survey evidence, mark supports/contradicts, preserve excerpt. Reviewed status only after at least one valid evidence link. Customer evidence is readable from the insight detail.

### Hypotheses and Experiments
Create hypothesis from an insight, specify measurable expected outcome and priority. Attach one or more experiments, record baseline, target, observed result, conclusion, decision, and notes.

## Essential interactions
- CRUD via Xano APIs, with server-side validation and informative errors.
- Product context applied consistently. Other products' customer records may not be linked.
- Search/filter, pagination only when needed; prefer straightforward forms.
- Each record detail has direct navigation to related records.
- Confirm destructive actions; referenced evidence should be protected from accidental loss.
- Loading, zero-data, validation-error, and unauthorized states must be handled.

## Definitions of done for V1
1. Owner can log in, log out, and cannot access data while logged out.
2. Create a product, a segment, two customers and two interviews.
3. Create a wave containing three eligible customers, one nonrespondent, and two valid replies.
4. Correct denominator and overall/segment breakdown appear, with N/A when zero responses.
5. Create an insight citing the original interview; add a contradictory source.
6. Create a hypothesis and experiment; record the result and decision.
7. On reload, all saved relationships and original evidence remain intact.
8. Cross-product links, duplicate participation, and invalid evidence references are rejected at the backend.

## UX constraints
This is a personal research workbench, not a client-facing survey product. Do not spend V1 time on landing pages, marketing design, multi-language UI, pricing, onboarding automation, or complex visualization.
