# BillGO Exchange Analytics — Project Memo

**To:** BillGO Data Analytics Engineer hiring manager
**From:** Vedavyas Muddati
**Re:** Reference implementation — why this work sample speaks to the role
**Date:** April 2026

## Context

The public BillGO Exchange story — 100 SMB enrollments/year ramping to 2,500/month, CEO Dan Holt's "10-day check to next-day virtual card" pitch, Satya Panda's mandate for 3× revenue at 65% COGS reduction — describes a business that needs an analytics engineer to own the substrate that proves the pivot works. Four questions follow directly: are cohorts retaining, are virtual cards succeeding first-try, which acquisition channels pay back, and are payments reconciling to accounting systems.

This project is a reference implementation of all four. It models 4,942 synthetic SMBs, 109,532 invoices, and 351,270 payment events across 18 months through a Kimball-style star schema (6 raw tables → 6 staging views → 2 dimensions + 2 facts → 4 marts), with 15 pytest data quality assertions protecting the pipeline. The repo is at [github.com/Veda8927/billgo-analytics-engineer](https://github.com/Veda8927/billgo-analytics-engineer) and the dashboard is a self-contained HTML at `docs/dashboard.html`.

Everything in the rest of this memo is a finding this project surfaced, a decision it required, or a claim about the role fit the work demonstrates.

## Finding 1 — Direct sales wastes 80× the CAC of organic

`mart_channel_unit_economics` joins SMB cohorts, acquisition records, captured invoices, and interchange revenue, then computes blended CAC, activation rate, and wasted CAC (acquired but never activated) per channel. The headline: direct sales has a blended CAC of $418, an activation rate of 77.8%, and $138K of CAC spent on SMBs that never activated — roughly 80× the waste of organic ($2K) despite comparable activation rates across all five channels. Under a 65% COGS reduction mandate, this is the first channel a CFO points at. In production, the next move is to decompose CAC by salesperson, deal size, and close-duration to find whether the waste concentrates on a specific sub-segment or is distributed evenly — which decides whether the fix is channel rebalance or motion improvement.

## Finding 2 — 3-month retention is degrading as acquisition scales

`mart_smb_cohort_retention` uses a cumulative definition (an SMB is "retained at month N" if their last captured payment is at or after month N, not if they transacted specifically in month N). The initial version used point-in-time retention, which produced 45% month-0 retention for the Oct 2024 cohort — an impossibility caught by the sanity check that retention cannot rise from month 0 to month 1. The fixed cumulative mart shows the Oct 2024 cohort at 97.6% 3-month retention and the Dec 2025 cohort at 88.6%, with every intervening cohort trending downward. Three hypotheses worth investigating on real data: channel mix drift toward higher-CAC paid channels, SMB size-tier mix shifting smaller, or onboarding capacity per CSM declining as enrollment volume scales 5×.

## Finding 3 — Large SMBs generate the majority of dollar-weighted reconciliation risk

`mart_reconciliation_exceptions` flags 9,910 captured invoices (10.1% of all captures) as partial, unmatched, or slow-reconciled. An initial 48-hour slow-reconciliation threshold produced 46K exceptions — misaligned with the generator's 12–72h delay distribution, which is the exact category of bug that ships to production when an analyst doesn't validate against actual data. Adjusted to 96h, the mart stabilizes. Large SMBs (10% of the enrolled base) produce the majority of dollar-weighted risk on the partial_small_delta and partial_large_delta buckets, supporting a tiered Ops SLA.

## Data quality — what separates this project from a standard work sample

Two bugs were deliberately planted in the synthetic data generator: a 0.5%-rate decimal-scale bug (interchange_fee written in basis points instead of dollars — $134,455 on a $50K capture) and a 0.2%-rate orphan-event bug (virtual cards missing their `vc_issued` event). The pytest suite caught both on the first run — 4 tests failed red with specific row counts and example IDs. A transactional SQL cleanup script fixed the 499 decimal rows and synthesized 197 replacement issuance rows tagged `evt_fix_*` for audit. All 15 tests passed green after the fix. The red/green output is captured in `docs/test_outputs/` as text artifacts, not screenshots.

The decimal bug is the same class I caught at my previous role, where I flagged a 100× loyalty-points conversion error before it hit revenue reporting. Planting a known bug class here, writing the test in advance, and watching it fire is the analytics engineering loop I run on production data every week at Nosh.

## What this says about me for this role

The JD asks for 3+ years. I have 1 year post-grad and 8 months at Nosh/Palette Labs. The years are the gap — the work isn't. This project does what a DA Engineer would do on day 30: build the cohort, lifecycle, and unit economics marts that frame every exec conversation, plus the DQ tests that keep the marts trustworthy. At Nosh I cut monthly operating loss 80% ($27K → $4.5K) working with the COO and finance team on the same CAC/LTV/contribution-margin model that sits inside `mart_channel_unit_economics` here. The domain is different; the work is the same.

I'd welcome a 20-minute call to walk through any of the four marts, the DQ cycle, or the $138K finding in more detail.

---

**Vedavyas Muddati**
[linkedin.com/in/vedavyas-muddati](https://linkedin.com/in/vedavyas-muddati)
[github.com/Veda8927/billgo-analytics-engineer](https://github.com/Veda8927/billgo-analytics-engineer)

*All data in this project is synthetic. Not affiliated with BillGO, Inc.*
