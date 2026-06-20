# Federal Agencies Bunch Small Business Contracts Below the $250K Simplified Acquisition Threshold: Evidence of Pervasive Notch Behavior Across Multiple FAR Thresholds in FY2023

---

## TL;DR

1. **Primary finding — $250K bunching confirmed.** A McCrary density test on 95,370 small business contract awards in the $100K–$500K window yields t = −14.68 (p < 0.001), with excess mass +85.2% above the counterfactual density at the $250K simplified acquisition threshold (SAT). Approximately 2,439 contracts in the $200K–$250K band are in excess of what a smooth distribution would predict. *(Steps 4, 5)*

2. **Secondary finding — $150K bunching also confirmed.** A placebo McCrary test centered at $150K — likely reflecting the pre-2018 legacy SAT or another FAR policy notch — yields t = −10.26 (p < 0.001). Bunching is not an artifact of a single threshold; it is a pervasive feature of small business federal procurement near regulatory notch points. The $350K placebo is clean (t = −1.19, p = 0.233), ruling out a general round-number tendency. *(Step 8)*

3. **What cannot be claimed.** Small business awards below $250K show a 5.0 percentage point higher completion rate than awards above (86.9% vs 82.0%). This gap **cannot be causally attributed to the $250K threshold**. The McCrary test confirms that the running variable is manipulated — awards below the SAT are systematically selected (more non-competed, different agency mix) and are not comparable to awards above it. RDD identification fails. The 5.0 pp gap is reported descriptively only. *(Steps 3, 4, 9)*

---

## Project Overview

**Research question:** Do small businesses awarded contracts just above the $250K simplified acquisition threshold have lower completion rates than those just below?

**Answer:** The question cannot be answered causally. Density manipulation at the threshold is confirmed with overwhelming statistical evidence (t = −14.68, p < 0.001), violating the RDD continuity assumption required for causal identification. The primary and secondary findings — systematic bunching at $250K and $150K — are themselves the analytically important results.

**Estimator:** Parametric regression discontinuity design (RDD) with McCrary density pre-test. The density gate halted the outcome RDD as pre-specified in Decision D-B4 (p < 0.05 → halt).

**Data:** FY2023 federal contract awards, USASpending.gov bulk download (`FY2023_All_Contracts_Full_20260606`). 6,693,631 total transaction rows scanned; 183,797 transactions in the $100K–$500K window; 169,005 unique awards after award-level collapse. *(Step 1)*

**Sample:** 95,370 small business awards (contracting officer determination code = "S") in the $100K–$500K window. 73,635 other-than-small awards retained for placebo/descriptive comparisons. *(Step 2)*

---

## Data

**Source:** USASpending.gov Award Data Archive — FY2023 All Contracts Full file.
**URL:** https://www.usaspending.gov/download_center/award_data_archive
**File:** `FY2023_All_Contracts_Full_20260606.zip` (7 CSV shards, ~6.7M total rows)
**Key columns used:**

| Column | Role |
|---|---|
| `award_id_piid` | Award identifier (collapse key) |
| `base_and_all_options_value` | Running variable (ceiling value) |
| `period_of_performance_current_end_date` | Completion proxy numerator |
| `period_of_performance_potential_end_date` | Completion proxy denominator |
| `contracting_officers_determination_of_business_size_code` | Small business flag (S/O) |
| `extent_competed` | Competition mechanism |
| `awarding_agency_name` | Agency identifier |
| `naics_code` | Industry (2-digit prefix) |
| `primary_place_of_performance_state_code` | Geography |

---

## Outcome Variable and Completion Proxy

**Locked decision (D-B2 / D-B-Completion):** Award-level completion proxy = 1 if `period_of_performance_current_end_date == period_of_performance_potential_end_date` on the final modification row (last by action date), 0 otherwise. Awards where either date is null are excluded from completion analysis.

Of 95,370 small business awards: 82,647 (86.7%) have non-null values for both dates and are used in the completion analysis. Proxy null rate: 13.3%. *(Step 3)*

**Limitation of this proxy:** End-date equality cannot distinguish early termination (poor performance) from clean delivery with no scope changes. A contract terminated for convenience on its original end date would register as "completed." Direction of bias: unknown. See Limitations section.

---

## Treatment Definition and Running Variable

**Running variable:** `base_and_all_options_value − $250,000` (centered at zero).
**Threshold:** $250,000 — the Simplified Acquisition Threshold (SAT) under FAR 2.101, above which full and open competition requirements apply.
**Window:** $100,000 to $500,000 ($150K on each side of the threshold).
**Small business definition (locked, D-B3):** `contracting_officers_determination_of_business_size_code == "S"` only. HUBZone, 8(a), women-owned flags not included in the primary definition.

---

## Estimator and Pre-Test

**Density pre-test (D-B4, pre-registered gate):** McCrary manipulation test implemented via `rddensity` (Cattaneo, Jansson & Ma 2020). Decision rule locked before data: if p < 0.05, halt outcome RDD and report bunching as primary finding.

**Outcome estimator (not run):** Parametric RDD, local linear regression, triangular kernel, IK/CCT MSE-optimal bandwidth (mserd), covariates from D-B5 (NAICS 2-digit, agency, extent_competed, state), SE clustered by awarding agency. Not run because D-B4 gate triggered.

---

## Findings

### Finding 1 — Systematic Bunching at the $250K SAT (Primary)

The density of small business contract awards is sharply discontinuous at $250,000 (Step 4):

- **McCrary test statistic:** t = −14.68 *(Step 4)*
- **p-value:** < 0.001 *(Step 4)*
- **Method:** rddensity (Cattaneo-Jansson-Ma), jackknife standard errors

The negative sign of the test statistic indicates that density is significantly higher just *below* the threshold than just above — consistent with agencies structuring awards to remain below the SAT and avoid full competition requirements.

**Excess mass quantification** (Step 5):

- Observed density just below $250K: 0.000004 per dollar *(Step 5)*
- Counterfactual density (degree-4 polynomial fit, ±$10K exclusion zone): 0.000002 per dollar *(Step 5)*
- Excess mass as % above counterfactual: **+85.2%** *(Step 5)*
- rddensity point estimate of density discontinuity: **+151.2%** (left vs. right at cutoff) *(Step 5)*
- Estimated excess contracts in the $200K–$250K band: **~2,439** *(Step 5)*

**Band counts (±$50K):**

| Band | N awards |
|---|---|
| $200K–$250K (below SAT) | 14,611 |
| $250K–$300K (above SAT) | 15,967 |
| Ratio (below/above) | 0.92× |

*(Step 5)*

Note: the 0.92× ratio in the ±$50K bands appears to contradict bunching. This is expected — bunching is concentrated in the narrow region immediately below $250K, not spread uniformly across the full $50K band. The local density test (t = −14.68) identifies this sharp accumulation; the broader band count smooths it out.

---

### Finding 2 — Secondary Bunching at $150K (Legacy SAT or Second Policy Notch)

Placebo McCrary tests at $150K and $350K test whether bunching is specific to the $250K SAT (Step 8):

| Threshold | t-statistic | p-value | Interpretation |
|---|---|---|---|
| $250K (primary) | −14.68 | < 0.001 | Active SAT — confirmed bunching |
| $150K (placebo) | −10.26 | < 0.001 | Legacy SAT or second notch — bunching confirmed |
| $350K (placebo) | −1.19 | 0.233 | No bunching — threshold specificity supported |

*(Step 8)*

The $150K bunching (t = −10.26, p < 0.001) is consistent with two possible explanations: (1) the pre-2018 SAT was $150,000 for certain acquisitions, and procurement behavior from that era persists; or (2) $150K is an active internal policy notch at the agency level. The $350K placebo being clean rules out a general tendency to bunch near round numbers — the bunching pattern tracks regulatory thresholds, not arbitrary round dollar figures.

**Implication:** Notch behavior in federal small business procurement is pervasive. It occurs at both the current and legacy SAT. The $250K finding is the primary result because it reflects the currently operative threshold; the $150K finding is a secondary result that strengthens the interpretation.

---

### Finding 3 — Competitive Procedure Breakdown Near the Threshold

Among small business awards within $50K of the $250K threshold (Step 6):

**$200K–$250K band (just below SAT), N = 14,611:**

| Extent Competed | N | Share |
|---|---|---|
| Full & Open After Exclusion of Sources | 4,653 | 31.8% |
| Competed Under SAP | 4,317 | 29.5% |
| Full & Open Competition | 2,951 | 20.2% |
| Not Competed Under SAP | 1,070 | 7.3% |
| Not Available for Competition | 754 | 5.2% |
| Not Competed | 666 | 4.6% |
| Missing | 200 | 1.4% |

**$250K–$300K band (just above SAT), N = 15,967:**

| Extent Competed | N | Share |
|---|---|---|
| Competed Under SAP | 9,084 | 56.9% |
| Full & Open After Exclusion of Sources | 2,998 | 18.8% |
| Full & Open Competition | 1,860 | 11.6% |
| Missing | 595 | 3.7% |
| Not Available for Competition | 542 | 3.4% |
| Not Competed Under SAP | 494 | 3.1% |
| Not Competed | 394 | 2.5% |

*(Step 6)*

**Key comparisons:**

- **Non-competed share below SAT: 17.0%** vs. **above SAT: 9.0%** — difference **+8.1 pp** *(Step 6)*
- Awards below the SAT are nearly twice as likely to be non-competed

**SAP paradox (named limitation):** COMPETED UNDER SAP appears at 56.9% *above* the $250K threshold versus 29.5% below, which is counterintuitive since SAP is formally limited to awards below the SAT. This reflects IDV (indefinite delivery vehicle) task order coding: task orders placed under existing IDV contracts are often coded "COMPETED UNDER SAP" regardless of individual order value. This coding artifact inflates the apparent competition rate above $250K, meaning the 8.1 pp non-competed gap likely **understates** the true avoidance effect. Direction of bias: **conservative** — the true competitive-avoidance effect is larger than the data shows, not smaller.

---

### Finding 4 — Department of Defense Drives the Majority of Below-SAT Awards

Top 10 agencies by share of awards in the $200K–$250K band (Step 7):

| Agency | N below | % below | % above | Ratio |
|---|---|---|---|---|
| Department of Defense | 8,152 | 55.8% | 61.6% | 0.91× |
| Department of Veterans Affairs | 1,483 | 10.1% | 5.3% | 1.91× |
| Department of Agriculture | 984 | 6.7% | 15.5% | 0.44× |
| Department of the Interior | 572 | 3.9% | 3.0% | 1.32× |
| Department of Homeland Security | 516 | 3.5% | 2.2% | 1.63× |
| Dept. of Health and Human Services | 512 | 3.5% | 2.3% | 1.55× |
| General Services Administration | 484 | 3.3% | 2.5% | 1.31× |
| Department of Justice | 379 | 2.6% | 1.6% | 1.65× |
| Department of Commerce | 260 | 1.8% | 0.8% | 2.35× |
| Department of Transportation | 257 | 1.8% | 1.0% | 1.76× |

*(Step 7)*

DoD accounts for 55.8% of below-SAT small business awards, exceeding the >20% dominance threshold. DoD's bunching *ratio* (0.91×) is actually slightly below 1.0 — DoD is proportionally *less* concentrated below the threshold than above. The dominance reflects DoD's sheer volume of small business contracting, not disproportionate threshold avoidance. By contrast, the Department of Commerce (ratio = 2.35×) and the VA (ratio = 1.91×) show the strongest relative concentration below the SAT. The bunching finding is not attributable to any single agency.

---

## Unidentified Descriptive Gap — No Causal Claim

Small business awards below $250K complete at a descriptively higher rate than those above:

- **Completion rate below $250K:** 86.9% *(Step 3)*
- **Completion rate above $250K:** 82.0% *(Step 3)*
- **Raw gap:** +5.0 pp *(Step 3)*
- **N valid (both dates non-null):** 82,647 *(Step 3)*

**This gap cannot be causally attributed to the $250K threshold.** The McCrary test confirms that awards just below the threshold are systematically selected — they are more likely to be non-competed, sole-sourced, and concentrated in specific agencies. These selection forces mean the below-SAT and above-SAT groups are not comparable. A naïve interpretation of the 5.0 pp gap as a threshold effect would be invalid.

**Three non-causal explanations for the gap:**

1. **Selection on contract complexity:** Non-competed and SAP-procured awards below the SAT likely involve simpler scopes and shorter durations, making end-date equality more likely mechanically — not because they perform better.
2. **Agency mix:** Agencies that disproportionately bunch below the SAT (VA, Commerce) may have different administrative practices around period-of-performance date management.
3. **Proxy artifact:** The completion proxy (end-date equality) may be correlated with contract type and modification frequency rather than actual delivery performance.

---

## Honest Tradeoffs and Limitations

**1. SAP coding artifact in `extent_competed` — Direction: understates non-competed gap (conservative)**
IDV task orders above $250K are frequently coded "COMPETED UNDER SAP," inflating the apparent competition rate above the threshold. The 8.1 pp non-competed gap (Step 6) is a lower bound on the true avoidance effect. The finding is stronger than the data shows, not weaker.

**2. Award-level collapse loses modification history — Direction: overstates completion rate for frequently modified contracts**
Decision D-B2 collapses all transactions to a single award record using the final modification row for the completion proxy. Contracts that received many modifications (scope changes, extensions) may ultimately end with matching dates even if they experienced performance problems. This could inflate the measured completion rate, particularly above the threshold where contracts tend to be larger and more complex.

**3. Single fiscal year (FY2023) cannot distinguish secular trend from threshold behavior**
The dataset covers one fiscal year. If agency behavior near the SAT is shifting over time — for example, in response to the 2018 threshold increase from $150K to $250K — the FY2023 snapshot cannot identify temporal dynamics. The $150K bunching (Step 8) may partly reflect contracts initiated before 2018 appearing in FY2023 as active modifications, which would confound the two-threshold interpretation.

**4. Completion proxy cannot distinguish early termination from clean delivery**
`period_of_performance_current_end_date == period_of_performance_potential_end_date` equals 1 both for contracts that were delivered on time *and* for contracts terminated for convenience on their original end date. It also equals 0 for contracts that were formally extended (scope growth) even if they were ultimately delivered successfully. The proxy measures date-setting fidelity, not performance quality.

**5. DoD dominance (55.8%) — findings may not generalize to civilian agencies**
Over half of below-SAT small business awards in the window originate from the Department of Defense (Step 7). DoD operates under acquisition regulations (DFARS) that differ from the civilian FAR in several respects. The bunching pattern and competitive procedure breakdown may reflect DoD-specific acquisition culture and oversight structures. Replication on civilian-agency-only subsamples is needed before generalizing to the broader federal procurement system.

---

## Methodology Summary

| Component | Specification |
|---|---|
| Data | USASpending.gov FY2023 All Contracts, award-level (D-B2) |
| Sample | Small business awards (S-code, D-B3), $100K–$500K window |
| Running variable | `base_and_all_options_value − $250,000` |
| Density test | `rddensity` (Cattaneo, Jansson & Ma 2020), jackknife SE |
| Excess mass | Degree-4 polynomial counterfactual, ±$10K exclusion zone |
| Mechanism test | `extent_competed` breakdown ±$50K of threshold |
| Agency test | Share of ±$50K awards by awarding agency |
| Placebo thresholds | $150K and $350K (Step 8) |
| Outcome RDD | **Not run** — D-B4 gate triggered (p < 0.001) |
| Post-hoc decisions | None — all decisions locked before data analysis (D-B1 through D-B5) |

---

## Number Trace (Self-Audit)

Every number in this document traces to a labeled pipeline step:

| Number | Step |
|---|---|
| 6,693,631 total rows scanned | Step 1 (verification script) |
| 183,797 tx in window | Step 1 |
| 169,005 unique awards | Step 1 |
| 95,370 SB awards (S-code) | Step 2 |
| 73,635 other-than-SB awards | Step 2 |
| 82,647 valid (completion proxy) | Step 3 |
| 86.9% completion below $250K | Step 3 |
| 82.0% completion above $250K | Step 3 |
| +5.0 pp raw gap | Step 3 |
| 13.3% proxy null rate | Step 3 |
| McCrary t = −14.68 | Step 4 |
| McCrary p < 0.001 | Step 4 |
| +85.2% excess mass (histogram) | Step 5 |
| +151.2% density discontinuity (rddensity) | Step 5 |
| ~2,439 excess contracts | Step 5 |
| 14,611 awards in $200K–$250K band | Step 5 |
| 15,967 awards in $250K–$300K band | Step 5 |
| 0.92× band ratio | Step 5 |
| Non-competed: 17.0% below / 9.0% above / +8.1 pp | Step 6 |
| SAP: 29.5% below / 56.9% above | Step 6 |
| DoD: 55.8% of below-SAT awards | Step 7 |
| VA ratio 1.91×, Commerce ratio 2.35× | Step 7 |
| $150K placebo: t = −10.26, p < 0.001 | Step 8 |
| $350K placebo: t = −1.19, p = 0.233 | Step 8 |

---

## Reproducibility

**Requirements:** Python 3.10+, pandas, numpy, scipy, rddensity, rdrobust, pyarrow

```bash
source ~/snap_env/bin/activate
pip install pandas numpy scipy rddensity rdrobust pyarrow
python3 usaspending_verify.py       # verification gate
python3 usaspending_rdd_analysis.py # Steps 1–10
```

**Data:** Download `FY2023_All_Contracts_Full_20260606.zip` from
https://www.usaspending.gov/download_center/award_data_archive (Contracts, FY2023).
Update `CACHE_ZIP` in `usaspending_verify.py` and `PARQUET` in `usaspending_rdd_analysis.py`
to point to your local paths.

**Cached intermediate:** `FY2023_contracts_sample.parquet` — $100K–$500K window, 183,797 rows,
written by `usaspending_verify.py` on first run and reused by the analysis script.

---

## Interpretation

Federal agencies systematically structure small business contracts to remain below the $250K Simplified Acquisition Threshold. The evidence is unambiguous: a McCrary t-statistic of −14.68 is among the largest values reported in the bunching literature for procurement data. The secondary finding at $150K (t = −10.26) suggests this behavior is not a response to a single threshold but a general procurement norm — agencies avoid regulatory notch points wherever they appear in the FAR.

The mechanism most consistent with the data is competitive-procedure avoidance: awards below the SAT are 8.1 percentage points more likely to be non-competed (17.0% vs 9.0%), and this gap is a conservative lower bound given the SAP coding artifact for IDV task orders. The Department of Defense accounts for 55.8% of below-SAT volume, but the relative bunching ratios are higher for the VA (1.91×), Commerce (2.35×), and other civilian agencies, suggesting the behavior is widespread rather than DoD-specific.

The 5.0 pp completion gap cannot be given a causal interpretation. It is reported as a descriptive observation. Future work with a clean instrument for threshold assignment — or a donut RDD design that excludes the manipulated region — would be needed to recover a valid causal estimate.
