# 03 — PMF System Logic (V1)

## Objective
Operate a closed learning loop: define market → collect original evidence → measure attachment → create reviewed insights → form hypotheses → test → record learnings.

## Seven logical modules
| Module | Responsibility | V1 |
| --- | --- | --- |
| 1. Market definition | Define products, customer segments, core promise and value-event definition | Yes, manual |
| 2. Customer discovery | Interview prospects/users about real incidents and workarounds | Yes |
| 3. Product experience | Measure activation, value events and retention | Definitions only; telemetry later |
| 4. PMF measurement | Survey qualified customers and calculate scored breakdowns | Yes |
| 5. Insight engine | Interpret benefits, problems, obstacles and evidence | Yes, human-reviewed |
| 6. Experiment engine | Prioritize hypotheses, record tests and outcomes | Yes |
| 7. PMF intelligence | Combine signals into recommendations | Basic reports only; advanced intelligence later |

## Operating workflow
1. Create product and a small set of distinguishable segments.
2. Add prospects or users; record interviews with first-hand accounts.
3. Propose insights with type, relevant segment, confidence, and source evidence links. Evidence can support or contradict.
4. Define a survey wave: eligibility rule, questionnaire version, time window. Add each eligible customer once, with segment snapshot at eligibility.
5. Record invitations and responses. Empty responses do not contribute to the PMF score.
6. Analyze all valid responses plus target-segment subsets. Identify the HXC profile from very-disappointed responses; review the shared main-benefit themes.
7. Treat somewhat-disappointed customers whose perceived core benefit aligns with champions as potentially convertible. Investigate their obstacles separately from unrelated feature requests.
8. Form a hypothesis linked to a reviewed insight. Define predicted change and success metric. Run and conclude an experiment.
9. Review PMF/experiment evidence; decide adopt, iterate, reject, or investigate further. Repeat.

## PMF formula and denominator
For each chosen survey wave and optional segment:

PMF % = 100 × count(valid responses where disappointment_level = very) / count(all valid responses).

A valid response must have responded_at and one of: very, somewhat, not. If denominator is 0: return N/A, never 0%. Show eligible count, invited count, qualified respondent count, response rate, and segment used.

Snapshot segment membership when participation is created. Report whole-wave score as well as filtered segment score. Do not treat a changed mix as an improved product.

For the primary trend, favor first-time eligible respondents and comparable eligibility/questionnaire versions; flag if cohorts overlap or definitions changed. Small samples are directional.

## Qualitative categorization
- Champions: "very disappointed." Learn what they love.
- Convertible candidates: "somewhat disappointed" and recognize the champion group's core benefit. Identify obstacles.
- Adjacent needs: "somewhat disappointed" but focused on a different benefit. Investigate separately.
- Low attachment: "not disappointed." Consider customer-fit or positioning explanations.

These groupings are **analyses** derived from responses, not immutable values entered by customers. V1 can document them in reviewed insights; no model-generated classification is necessary.

## Recommended decision rules
| Observed pattern | Possible next action |
| --- | --- |
| Few/no users | Interview prospects, investigate current alternatives |
| Qualified users cannot describe value | Reassess positioning, onboarding, and real pain |
| Strong champions in one segment | Articulate HXC and test focused acquisition |
| Champions exist; convertible users report shared blocker | Design a targeted, falsifiable experiment |
| High reported dependence; weak observed engagement | Investigate before concluding PMF (requires later telemetry) |
| Strong engagement; weak payments | Examine economic buyer and willingness to pay (later commercial data) |
| Changing survey mix | Compare like-for-like cohorts and report both filtered/unfiltered results |

Recommendations require rationale and founder review; no blind automatic roadmap generation.

## Routine
Continuous evidence capture; weekly interview/insight review; monthly comparable survey and experiment review where sample sizes permit; quarterly reconsideration of segment, HXC, and core-value hypothesis.

## What this version cannot determine
V1's manual data can measure stated attachment and structured learning. It **cannot** automatically verify whether users get value, retain, or pay. Do not display those as real metrics until supported integrations exist.
