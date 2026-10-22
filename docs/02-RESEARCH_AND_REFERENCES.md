# 02 — Research and References

## Primary reference A: Eric Migicovsky, Y Combinator
- Video: [How to Talk to Users — YC Startup School](https://www.youtube.com/watch?v=MT4Ig2uqjTc) (Y Combinator, July 25, 2019).
- Presentation/transcript: [How to Talk to Users](https://yc-startup-school.relayto.com/e/how-to-talk-to-users-rmdawvc59tr6j).

### What we take from it
- Founders should remain directly connected to users.
- Discuss customers' lives and actual past behavior rather than pitching a solution or asking hypothetical questions.
- Five interview prompts: hardest part; last time it happened; why hard; what they tried; what they dislike about existing solutions.
- At prototype stage, weigh economic severity, frequency, and budget/authority.
- Interviews inform the move from idea → prototype → launched product.

### Our design adaptation
Store customers and interview evidence in structured records. Allow unlaunched products with prospects. Capture source observations before creating interpretations.

## Primary reference B: Rahul Vohra, Superhuman
- Original essay: [How Superhuman Built an Engine to Find Product–Market Fit](https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit/) (First Round Review, November 2018).
- Author's republication: [Superhuman blog](https://blog.superhuman.com/how-superhuman-built-an-engine-to-find-product-market-fit/).

### Superhuman's measurement
Ask active, qualified users:
1. How would you feel if you could no longer use this product? (Very / somewhat / not disappointed)
2. What type of people would benefit most?
3. What is the main benefit you receive?
4. How can we improve the product?

Compute the share of valid respondents selecting "very disappointed." The commonly cited 40% is a directional Sean Ellis benchmark, not a statistically certain declaration of fit. Superhuman reported an initial 22% and later improvements, partly by identifying high-expectation customers (HXC).

### Four-step optimization loop
1. Segment supporters to identify HXC.
2. Analyze what supporters value and what holds back somewhat-disappointed users who value the same benefit.
3. Improve the core benefit and remove relevant obstacles.
4. Repeat measurement using comparable customers and cohorts.

### Our design adaptation
Store eligibility, wave and segment snapshots; separate raw survey answers from qualitative insights; link insights to hypothesis-driven experiments; report denominators and interpretation limits.

## Methodological cautions
- A higher *filtered segment* PMF score is not necessarily product improvement. Always retain unfiltered and segment-specific baselines.
- Survey results can be biased by eligibility, nonresponse, repeated respondents, and changing customer mix.
- Small samples have considerable uncertainty. Around 40 responses can give direction, not precision.
- Stated dependence should eventually be cross-checked against product use, realized customer value, renewals, and paid demand.
- A procurement product and a daily-use product may require different definitions of adequate exposure and retention.

## Sourced vs proposed
**From YC and Superhuman:** interviews, survey questions, HXC, core-benefit alignment, 40% heuristic, repetition.

**Our application design:** 7 modules; 10-table V1 schema; manual evidence links; hypothesis/experiment register; four-dimension PMF dashboard; single-owner app; Xano/WeWeb implementation plan. These are design proposals, not claims that the cited authors prescribed this architecture.
