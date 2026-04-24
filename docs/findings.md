# Findings from the BillGO Exchange Analytics Reference Implementation

Three findings surfaced while building this project against synthetic data.
Each maps to a current BillGO hiring priority and would translate to a real
investigation in production data.

## Finding 1 — Direct sales wastes disproportionate CAC

**Mart:** `mart_channel_unit_economics`

Direct sales has the highest per-SMB CAC ($418), the lowest activation rate
(77.8%), and the highest absolute wasted CAC on never-activated SMBs
(~$138K in synthetic data, ~80x more than organic).

**Implication:** For a company mandated to cut COGS 65% (Satya Panda's
public mandate) while tripling revenue, direct sales is a prime candidate
for channel-mix rebalancing or activation-playbook improvement.

**Maps to hiring priority:** Director of Product – Customer Acquisition,
VP Direct Marketing – Customer Acquisition, Business Analyst – Customer
Acquisition.

## Finding 2 — 3-month retention degrading as acquisition scales

**Mart:** `mart_smb_cohort_retention`

Oct 2024 cohort: 97.6% 3-month retention.
Dec 2025 cohort: 88.6% 3-month retention.
Each intervening cohort trends downward.

In real data this pattern would indicate that scaling acquisition pulls in
SMBs who activate at similar rates (77-81% across channels) but retain
differently over time. Hypothesis to investigate: channel mix shifting
toward higher-CAC paid channels, SMB size-tier mix shifting smaller, or
onboarding capacity per SMB declining as enrollment volume scales 5x.

**Maps to hiring priority:** Director of Product – Customer Management,
Business Analyst – Customer Management.

## Finding 3 — Two data quality bugs caught by automated tests

### Bug 1: Decimal-scale in interchange_fee

0.5% of captured events (499 rows) had `interchange_fee` written in basis
points instead of dollars (e.g. $134,455 instead of $1,344 on a $50K
capture). Impact: total interchange revenue overstated by roughly 2x in
aggregate, with individual bugged rows 100x too large.

This is the same bug class I caught at my previous role (100x decimal
error in loyalty-point reconciliation, pre-revenue-reporting). Planting a
known-class bug in synthetic data and catching it with a ratio-based test
demonstrates the pattern is defensible as a standard check at the
staging-to-mart boundary.

### Bug 2: Orphan virtual cards

0.2% of virtual cards (197 rows) had authorization events but no prior
vc_issued event — a logging gap where the issuance row was lost upstream.
Impact: time-to-capture analytics would silently skip these VCs,
under-reporting total volume and mis-estimating timing distributions.

Both bugs were caught by automated pytest assertions before any mart was
rebuilt. Fix cycle: detect (red tests) -> diagnose (test output localizes
row counts and example IDs) -> fix (SQL cleanup with BEGIN/COMMIT
transactions) -> rebuild downstream models -> verify (green tests).

**Process implication:** Data quality tests at the raw-to-staging boundary
are not optional in a fintech pipeline. A single decimal bug surviving
to an exec dashboard is the kind of incident that triggers board scrutiny.

**Maps to hiring priority:** Data Analytics Engineer.
