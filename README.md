# Diagnostic Label Bias in Diabetes: A Racial Equity Audit Using NHANES 2017–2018

## What This Project Does

Clinical machine learning models trained on Electronic Health Record (EHR) labels learn the diagnostic process, not the underlying disease. If that process is inequitably applied across racial/ethnic groups, the model inherits and potentially amplifies that inequity. This project provides a direct, quantified demonstration of that mechanism using nationally representative survey data.

Two logistic regression models are trained on the same features (age, sex, race/ethnicity) but with different labels:

- **M1**: Label = whether a respondent was ever told by a doctor they have diabetes (`DIQ010=1`)
- **M2**: Label = whether the respondent meets the ADA criterion for diabetes by HbA1c ≥ 6.5% (`LBXGH ≥ 6.5`)

Both models are evaluated against the HbA1c criterion as ground truth. The gap between M1 and M2 performance, and the unequal distribution of that gap across racial groups, is the measure of label bias.

---

## Data

**Source**: [NHANES 2017–2018](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017), National Center for Health Statistics, CDC.

Four XPT files are required (place in the same directory as `analysis.py`):

| File | Contents |
|------|----------|
| `DEMO_J.XPT` | Demographics, survey weights (`WTMEC2YR`), design variables (`SDMVPSU`, `SDMVSTRA`) |
| `DIQ_J.XPT` | Diabetes questionnaire (`DIQ010`) |
| `GHB_J.XPT` | Glycohemoglobin / HbA1c (`LBXGH`) |
| `GLU_J.XPT` | Fasting glucose (`LBXGLU`) — included for completeness; not used in primary analysis |

**Download**: Files are publicly available at `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/`

**Survey design**: NHANES uses stratified multi-stage probability sampling with deliberate oversampling of Non-Hispanic Black (≈1.85×), Non-Hispanic Asian (≈2.22×), and Mexican American respondents relative to their population share. All estimates use `WTMEC2YR` weights with Taylor linearization variance estimation (`SDMVPSU`, `SDMVSTRA`) to produce nationally representative results.

---

## Analysis Population

| Criterion | N |
|-----------|---|
| NHANES 2017–2018 total | 9,254 |
| Exclude: no MEC exam weight (WTMEC2YR = 0 or missing) | — |
| Exclude: missing HbA1c (LBXGH) | — |
| Exclude: Borderline diabetes response (DIQ010 = 3, N=184) | — |
| **Main analysis sample** | **5,877** |

HbA1c-positive (≥ 6.5%) subpopulation: 711

| Group | N | HbA1c+ | Diagnosed |
|-------|---|--------|-----------|
| Non-Hispanic White | 2,023 | 203 | 285 |
| Non-Hispanic Black | 1,312 | 181 | 182 |
| Mexican American | 858 | 112 | 123 |
| Other Hispanic | 547 | 74 | 71 |
| Non-Hispanic Asian | 796 | 102 | 106 |
| Other/Multiracial | 341 | 39 | 46 |
| **Total** | **5,877** | **711** | — |

---

## Key Findings

### Finding 1 — Undiagnosis Rate Gap

Among respondents meeting the HbA1c criterion (≥ 6.5%), the fraction who report never being told they have diabetes:

| Group | Undiagnosed | 95% CI |
|-------|-------------|--------|
| Non-Hispanic White | 12.8% | 6.2%–19.5% |
| Non-Hispanic Black | **32.2%** | 22.1%–42.4% |
| Mexican American | 22.7% | 10.8%–34.6% |
| Other Hispanic | 31.5% | 8.7%–54.2% |
| Non-Hispanic Asian | 27.7% | 17.1%–38.4% |

**Non-Hispanic Black vs. Non-Hispanic White**: +19.4 percentage points (95% CI: +7.1 to +31.6), ratio 2.51×, p = 0.0055.

Weights: `WTMEC2YR`. Variance: Taylor linearization with centered lonely-PSU correction.

*Language note: "meeting the HbA1c criterion" is used throughout, not "objectively diabetic." The HbA1c criterion is one of three ADA diagnostic criteria; its reliability may vary for individuals with sickle cell trait (see Limitations).*

---

### Finding 2 — Model Performance: AUC

Both models evaluated against HbA1c ≥ 6.5% as ground truth. 95% CIs from full PSU bootstrap (B=500; entire dataset resampled at PSU level per replicate — both training and test vary).

| Model | AUC | 95% CI (PSU bootstrap) |
|-------|-----|------------------------|
| M1 (Diagnosed label) | 0.742 | 0.743–0.816 |
| M2 (HbA1c criterion) | 0.760 | 0.722–0.812 |

The CIs overlap substantially. The models are **not statistically distinguishable** on overall discriminative performance. AUC is reported as context only; the primary finding is subgroup sensitivity and specificity.

---

### Finding 3 — Subgroup Sensitivity (Cross-Evaluation on HbA1c Truth)

Both models evaluated against HbA1c ≥ 6.5% as ground truth. Gap column: positive = lower sensitivity than Non-Hispanic White (model misses more actual diabetics in that group).

**M1 — Trained on Diagnosed Label, evaluated on HbA1c truth**

| Group | N (test) | Sensitivity | Gap vs. NHWhite |
|-------|----------|-------------|-----------------|
| Non-Hispanic White | 601 | 84.7% | (ref) |
| Non-Hispanic Black | 398 | 82.8% | +1.8pp |
| Mexican American | 254 | 88.0% | −3.3pp |
| Other Hispanic | 158 | 82.1% | +2.6pp |
| Non-Hispanic Asian | 237 | 94.7% | −10.0pp |

**M2 — Trained on HbA1c Criterion, evaluated on HbA1c truth**

| Group | N (test) | Sensitivity | Gap vs. NHWhite |
|-------|----------|-------------|-----------------|
| Non-Hispanic White | 601 | 88.5% | (ref) |
| Non-Hispanic Black | 398 | 85.7% | +2.9pp |
| Mexican American | 254 | 88.0% | +0.6pp |
| Other Hispanic | 158 | 100.0% | −11.5pp |
| Non-Hispanic Asian | 237 | 96.4% | −7.9pp |

---

### Finding 4 — Specificity Cost

When switching from M1 to M2, specificity drops for all groups. This specificity cost represents the increase in false-positive burden — people without diabetes who would be flagged by the model.

| Group | M1 Specificity | M2 Specificity | Cost (pp) |
|-------|---------------|----------------|-----------|
| Non-Hispanic White | 61.3% | 57.1% | **+4.2pp** |
| Non-Hispanic Black | 60.2% | 43.8% | **+16.4pp** |
| Mexican American | 59.1% | 53.3% | +5.8pp |
| Other Hispanic | 72.7% | 56.0% | +16.8pp |
| Non-Hispanic Asian | 55.4% | 50.2% | +5.2pp |

The false-positive burden of adopting the "fairer" label criterion falls almost entirely on Non-Hispanic Black and Other Hispanic respondents (+16–17pp), versus +4–6pp for all other groups.

---

## Borderline Sensitivity Analysis

Respondents reporting "borderline" diabetes (DIQ010=3, N=184) are excluded from the main analysis. Sensitivity analyses test robustness to this decision.

| Analysis | N | Black undiag. | White undiag. | Gap | Ratio | p-value |
|----------|---|--------------|--------------|-----|-------|---------|
| Main (Borderline excluded) | 5,877 | 32.2% | 12.8% | +19.4pp | 2.51× | 0.0055 |
| Borderline as POSITIVE | 6,045 | 30.2% | 12.1% | +18.0pp | 2.49× | 0.0065 |
| Borderline as NEGATIVE | 6,045 | 36.5% | 17.6% | +18.9pp | 2.07× | 0.0071 |

Direction is invariant. All three analyses are statistically significant. The main result is robust to any assumption about borderline cases.

---

## What This Project Demonstrates

**(a)** Among individuals meeting the HbA1c criterion for diabetes, Non-Hispanic Black respondents are undiagnosed at 2.51× the rate of Non-Hispanic White respondents (32.2% vs. 12.8%, p = 0.0055).

**(b)** A model trained on the diagnosed label shows modest sensitivity gaps versus the HbA1c-criterion model when both are evaluated on HbA1c truth. The primary modeling difference is in specificity, not sensitivity.

**(c)** Switching from the diagnosed label to the HbA1c criterion as a training target produces a specificity cost that falls almost entirely on Non-Hispanic Black and Other Hispanic respondents (+16–17pp versus +4–6pp for other groups).

**(d)** The mechanism producing the undiagnosis rate gap — whether clinician diagnostic behavior, differential access to screening, differential screening frequency, or some combination — **cannot be determined from this data**. No causal or behavioral claim is made.

---

## Methods

**Features**: Age (`RIDAGEYR`), sex (`RIAGENDR`), race/ethnicity dummies (`RIDRETH3`; Non-Hispanic White = reference). BMI (`BMXBMI`) was excluded pending verification of the BMX_J.XPT file.

**Model**: Survey-weighted logistic regression (`sklearn.linear_model.LogisticRegression`, `C=1.0`, `lbfgs` solver), `sample_weight=WTMEC2YR`.

**Threshold**: Youden-optimal threshold selected on weighted training predictions.

**Train/test split**: 70/30, stratified on HbA1c label, random seed 42.

**AUC confidence intervals**: Full PSU bootstrap (B=500). Each replicate resamples PSUs with replacement within strata, then re-splits, re-trains, and re-tests. Both training and test sets vary per replicate. This is the correct method for complex survey data; bootstrap on the test set only (ignoring survey design) underestimates CI width by approximately 22%.

**Variance estimation**: Taylor linearization for proportions, using `SDMVPSU` (masked pseudo-PSU) and `SDMVSTRA` (masked pseudo-stratum). Lonely-PSU strata (single PSU per stratum) use the centered correction: variance contribution = (t_h1 − grand_mean)², preventing both zero-contribution and degenerate width. This matches the default behavior of R's `survey` package with `centered` option.

**Survey weights**: `WTMEC2YR` throughout. `WTSAF2YR` (fasting subsample weight) was not used; fasting glucose is secondary and its use would reduce N substantially.

---

## Limitations

1. **HbA1c and sickle cell trait**: Sickle cell trait can artificially elevate HbA1c in some Non-Hispanic Black individuals, potentially overstating the undiagnosis rate in that group. No sickle cell variable is available in the four files used. Direction of bias is conservative — if sickle cell inflation is present, the true gap may be *smaller* than reported.

2. **Single criterion**: HbA1c ≥ 6.5% is one of three ADA diagnostic criteria (alongside fasting plasma glucose ≥ 126 mg/dL and 2-hour plasma glucose ≥ 200 mg/dL on OGTT). Fasting glucose cross-validation requires the FASTQX_J file (for fasting hours) and is not included in this analysis.

3. **Features**: Race/ethnicity, age, and sex only. BMI was excluded. A richer feature set would likely change point estimates but not the direction of the undiagnosis rate finding, which is descriptive rather than model-dependent.

4. **Borderline cases**: N=184 excluded. Sensitivity analyses (Section above) show the main result is invariant to this decision.

5. **Mechanism unknown**: The project measures *that* a gap exists, not *why*. Differential access, differential screening frequency, clinician decision patterns, and patient-side factors are all candidate explanations. Distinguishing between them requires data not present in NHANES.

---

## Reproducing the Results

```bash
pip install -r requirements.txt

# Place DEMO_J.XPT, DIQ_J.XPT, GHB_J.XPT, GLU_J.XPT in this directory, then:
python analysis.py
```

Expected runtime: approximately 3–5 minutes (dominated by 500-replicate PSU bootstrap).

All random seeds are fixed (`numpy.random.seed(42)`, train/test split `random_state=42`). Results are fully reproducible.

---

## Project Context

This project was motivated by a documented pattern in clinical ML: models trained on clinical labels inherit and amplify the biases embedded in those labels. The NHANES dataset is particularly well-suited to quantify this because it contains both doctor-reported diagnosis (the biased label) and a biochemical criterion (HbA1c) that is independent of whether a clinician ever acted on it.

The design effect for HbA1c prevalence in this dataset is approximately 1.66, meaning confidence intervals that ignore the complex survey design are approximately 22% too narrow. The variance estimation in this analysis accounts for this.

---

## Citation

National Center for Health Statistics. National Health and Nutrition Examination Survey Data. Hyattsville, MD: U.S. Department of Health and Human Services, Centers for Disease Control and Prevention, 2017–2018. https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017
