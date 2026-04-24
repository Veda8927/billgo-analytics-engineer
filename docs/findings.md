# Findings from the BillGO Exchange Analytics Reference Implementation

Three findings surfaced by building this project against synthetic data. Each
maps to a current BillGO hiring priority and would translate to a real
investigation in production data.

## Finding 1 — Direct sales wastes disproportionate CAC

**Mart:** `mart_channel_unit_economics`

Direct sales has the highest per-SMB CAC ($418), the lowest activation rate
(77.8%), and the highest absolute wasted CAC on never-activated SMBs
(~$138K in our synthetic data, ~80x more than organic).

**Implication:** For a company mandated to cut COGS 65% (Satya Panda's public
mandate) while tripling revenue, direct sales is a prime candidate for either
channel-mix rebalancing or activation-playbook improvement.

**Maps to hiring priority:** Director of Product – Customer Acquisition,
VP Direct Marketing – Customer Acquisition, Business Analyst – Customer
Acquisition. All three roles would own decisions informed by this mart.

## Finding 2 — 3-month retention is degrading as acquisition scales

**Mart:** `mart_smb_cohort_retention`

The Oct 2024 cohort hit 100% 3-month retention. The Dec 2025 cohort hit 88.6%.
Each intervening cohort trends downward. This pattern in real data would
indicate that scaling acquisition is pulling in SMBs who activate at similar
rates (77-81% across channels) but retain differently over time.

**Hypothesis to investigate:** channel mix shifting toward higher-CAC
paid channels, SMB size-tier mix shifting smaller, or onboarding capacity
per SMB declining as enrollment volume scales 5x.

**Maps to hiring priority:** Director of Product – Customer Management,
Business Analyst – Customer Management.

## Finding 3 — Data quality bugs in raw events contaminate mart-level KPIs

**Affects:** `mart_channel_unit_economics` (inflated LTV/CAC ratios 10-1000x)

A 0.5%-rate decimal-scale bug in interchange_fee (writing basis points instead
of dollars, e.g. $5,880 instead of $58.80) silently inflates revenue-per-SMB
by ~10x and makes LTV/CAC ratios appear 3 orders of magnitude too high.
A separate 0.2%-rate orphan-event bug (VCs missing their vc_issued event)
would corrupt first-time-success-rate calculations if unflagged.

Both bugs were planted in the generator and caught in Step 5 data quality
tests before they reach downstream BI.

**Process implication:** Data quality tests at the staging-to-mart boundary
are not optional in a fintech pipeline. A single decimal bug that survives
to an exec dashboard is the kind of incident that triggers board-level
scrutiny. Tests must be automated and fail the pipeline, not just log warnings.

**Maps to hiring priority:** Data Analytics Engineer. Building the tested
substrate so AI/ML models (3+ open roles under CTO Satya) train on clean
data. Analytics engineering is the input to every AI engineer on the team.
