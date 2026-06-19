"""
NHANES 2017-2018 Full Fairness Audit Pipeline
──────────────────────────────────────────────
Label Bias in Diabetes Diagnosis: M1 (Diagnosed Label) vs M2 (HbA1c Criterion)

Sections:
  A. Data loading and merging
  B. Population descriptives
  C. Undiagnosis rate by group (Taylor linearization)
  D. Model training: M1 (diagnosed label) and M2 (HbA1c ≥ 6.5%)
  E. Subgroup sensitivity and specificity tables
  F. Specificity cost (M1 → M2)
  G. AUC with full PSU bootstrap
  H. Borderline sensitivity analyses (DIQ010=3 as positive and negative)
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
np.random.seed(42)

NHANES_DIR   = os.path.dirname(os.path.abspath(__file__))  # XPT files in same directory as script
HBA1C_THRESH = 6.5
N_BOOTSTRAP  = 500

FILES = {
    "demo": os.path.join(NHANES_DIR, "DEMO_J.XPT"),
    "diq":  os.path.join(NHANES_DIR, "DIQ_J.XPT"),
    "ghb":  os.path.join(NHANES_DIR, "GHB_J.XPT"),
    "glu":  os.path.join(NHANES_DIR, "GLU_J.XPT"),
}

RACE_LABELS = {
    1: "Mexican American",
    2: "Other Hispanic",
    3: "Non-Hispanic White",
    4: "Non-Hispanic Black",
    6: "Non-Hispanic Asian",
    7: "Other/Multiracial",
}

RACE_ORDER = [
    "Non-Hispanic White",
    "Non-Hispanic Black",
    "Mexican American",
    "Other Hispanic",
    "Non-Hispanic Asian",
    "Other/Multiracial",
]

def sep(title=""):
    print()
    print("=" * 72)
    if title:
        print(f"  {title}")
        print("=" * 72)

def load_xpt(path, label):
    df, _ = pyreadstat.read_xport(path)
    df.columns = df.columns.str.upper()
    return df

# ─────────────────────────────────────────────────────────────────────────────
# A. LOAD AND MERGE
# ─────────────────────────────────────────────────────────────────────────────
sep("A. DATA LOADING AND MERGE")

demo = load_xpt(FILES["demo"], "DEMO_J")
diq  = load_xpt(FILES["diq"],  "DIQ_J")
ghb  = load_xpt(FILES["ghb"],  "GHB_J")
glu  = load_xpt(FILES["glu"],  "GLU_J")

n_demo = len(demo)
merged = (demo
    .merge(diq[["SEQN", "DIQ010"]], on="SEQN", how="left")
    .merge(ghb[["SEQN", "LBXGH"]],  on="SEQN", how="left")
    .merge(glu[["SEQN", "LBXGLU", "WTSAF2YR"]], on="SEQN", how="left"))

assert len(merged) == n_demo
print(f"  Merged rows: {len(merged):,}  (DEMO_J = {n_demo:,}) ✓")

# ─────────────────────────────────────────────────────────────────────────────
# B. VARIABLE CONSTRUCTION — MAIN ANALYSIS (borderline excluded)
# ─────────────────────────────────────────────────────────────────────────────
sep("B. MAIN ANALYSIS POPULATION (Borderline Excluded)")

def build_analysis_df(raw, borderline_action="exclude"):
    df = raw.copy()
    df["race_label"] = df["RIDRETH3"].map(RACE_LABELS)

    diq_map = {1.0: "diagnosed", 2.0: "not_diagnosed", 3.0: "borderline"}
    df["dx_cat"] = df["DIQ010"].map(diq_map)

    n_borderline = (df["dx_cat"] == "borderline").sum()

    if borderline_action == "exclude":
        df = df[df["dx_cat"] != "borderline"].copy()
    elif borderline_action == "positive":
        df.loc[df["dx_cat"] == "borderline", "dx_cat"] = "diagnosed"
    elif borderline_action == "negative":
        df.loc[df["dx_cat"] == "borderline", "dx_cat"] = "not_diagnosed"

    df["diagnosed"] = (df["dx_cat"] == "diagnosed").astype(float)
    df["hba1c_pos"] = (df["LBXGH"] >= HBA1C_THRESH).astype(float)

    mask = (
        df["diagnosed"].notna() &
        df["hba1c_pos"].notna() &
        df["LBXGH"].notna() &
        df["WTMEC2YR"].notna() &
        (df["WTMEC2YR"] > 0) &
        df["race_label"].notna() &
        df["RIDAGEYR"].notna()
    )
    return df[mask].copy(), n_borderline

df_main, n_borderline = build_analysis_df(merged, borderline_action="exclude")
print(f"  Borderline cases (DIQ010=3): {n_borderline}")
print(f"  Main analysis N: {len(df_main):,}")
print()
print(f"  {'Group':<40} {'N':>6} {'HbA1c+':>8} {'Diagnosed':>10}")
print("  " + "-"*68)
for grp in RACE_ORDER:
    sub = df_main[df_main["race_label"] == grp]
    if len(sub) == 0:
        continue
    print(f"  {grp:<40} {len(sub):>6,} {int(sub['hba1c_pos'].sum()):>8,} {int(sub['diagnosed'].sum()):>10,}")
print(f"  {'TOTAL':<40} {len(df_main):>6,}")

# ─────────────────────────────────────────────────────────────────────────────
# C. UNDIAGNOSIS RATE (Taylor linearization)
# ─────────────────────────────────────────────────────────────────────────────
sep("C. UNDIAGNOSIS RATE — Among HbA1c ≥ 6.5% (Taylor Linearization)")

def taylor_prop(y, w, psu, stratum, centered=True):
    """
    Taylor linearization for weighted proportion.
    centered=True: lonely-PSU strata use (t_h1 - grand_mean)^2 instead of zero.
    """
    y, w = np.asarray(y, float), np.asarray(w, float)
    psu, stratum = np.asarray(psu), np.asarray(stratum)
    W = w.sum()
    prop = (w * y).sum() / W
    z = w * (y - prop) / W

    df_l = pd.DataFrame({"z": z, "psu": psu, "stratum": stratum})
    pts = df_l.groupby(["stratum", "psu"])["z"].sum().reset_index()
    pts.columns = ["stratum", "psu", "t"]

    grand_mean = pts["t"].mean()
    var_total = 0.0
    total_psus = 0
    total_strata = 0

    for h, grp in pts.groupby("stratum"):
        t = grp["t"].values
        n_h = len(t)
        total_strata += 1
        if n_h == 1:
            if centered:
                var_total += (t[0] - grand_mean) ** 2
            total_psus += 1
        else:
            var_total += (n_h / (n_h - 1)) * np.sum((t - t.mean()) ** 2)
            total_psus += n_h

    se = np.sqrt(var_total)
    dof = total_psus - total_strata
    return prop, se, dof

def ci(prop, se, dof, alpha=0.05):
    t_c = stats.t.ppf(1 - alpha / 2, df=max(dof, 1))
    return max(0.0, prop - t_c * se), min(1.0, prop + t_c * se)

df_hba_pos = df_main[df_main["hba1c_pos"] == 1.0].copy()
df_hba_pos["undiagnosed"] = 1.0 - df_hba_pos["diagnosed"]
print(f"\n  HbA1c-positive N: {len(df_hba_pos):,}\n")
print(f"  {'Group':<40} {'N':>5} {'Undiag%':>9} {'95% CI':>18} {'DoF':>5}")
print("  " + "-"*82)

undiag_results = {}
for grp in RACE_ORDER:
    sub = df_hba_pos[df_hba_pos["race_label"] == grp]
    if len(sub) < 20:
        print(f"  {grp:<40} {len(sub):>5} {'<20 obs — suppressed':>30}")
        continue
    prop, se, dof = taylor_prop(sub["undiagnosed"], sub["WTMEC2YR"],
                                sub["SDMVPSU"], sub["SDMVSTRA"])
    lo, hi = ci(prop, se, dof)
    undiag_results[grp] = dict(prop=prop, se=se, dof=dof, lo=lo, hi=hi, n=len(sub))
    print(f"  {grp:<40} {len(sub):>5,} {prop*100:>8.1f}%  ({lo*100:.1f}%–{hi*100:.1f}%)  {dof:>5}")

# Black vs White test
r_b = undiag_results["Non-Hispanic Black"]
r_w = undiag_results["Non-Hispanic White"]
diff = r_b["prop"] - r_w["prop"]
se_d = np.sqrt(r_b["se"]**2 + r_w["se"]**2)
dof_d = min(r_b["dof"], r_w["dof"])
t_s = diff / se_d
p_v = 2 * stats.t.sf(abs(t_s), df=dof_d)
ci_lo = diff - stats.t.ppf(0.975, dof_d) * se_d
ci_hi = diff + stats.t.ppf(0.975, dof_d) * se_d

print(f"""
  PRIMARY COMPARISON — Non-Hispanic Black vs. Non-Hispanic White
  ─────────────────────────────────────────────────────────────
  NHBlack undiagnosis rate:  {r_b['prop']*100:.1f}%  (95% CI {r_b['lo']*100:.1f}%–{r_b['hi']*100:.1f}%)
  NHWhite undiagnosis rate:  {r_w['prop']*100:.1f}%  (95% CI {r_w['lo']*100:.1f}%–{r_w['hi']*100:.1f}%)
  Difference (B−W):          {diff*100:+.1f}pp  (95% CI {ci_lo*100:+.1f}pp to {ci_hi*100:+.1f}pp)
  Ratio:                     {r_b['prop']/r_w['prop']:.2f}×
  t-statistic:               {t_s:.3f}
  p-value (two-sided):       {p_v:.4f}
  Significant (α=0.05):      {'YES ✓' if p_v < 0.05 else 'NO'}
""")

# ─────────────────────────────────────────────────────────────────────────────
# D. MODEL TRAINING
# ─────────────────────────────────────────────────────────────────────────────
sep("D. MODEL TRAINING — M1 (Diagnosed Label) and M2 (HbA1c ≥ 6.5%)")

# Features: age, sex, and race dummies (NH White = reference)
race_dummies = pd.get_dummies(df_main["race_label"].astype(str), drop_first=False)
# Drop NH White as reference
ref_col = "Non-Hispanic White"
race_cols = [c for c in race_dummies.columns if c != ref_col]
race_dummy_df = race_dummies[race_cols].astype(float)

feature_cols = ["RIDAGEYR", "RIAGENDR"] + race_cols
X = pd.concat([df_main[["RIDAGEYR", "RIAGENDR"]].reset_index(drop=True),
               race_dummy_df.reset_index(drop=True)], axis=1).values
w = df_main["WTMEC2YR"].values
y_m1 = df_main["diagnosed"].values
y_m2 = df_main["hba1c_pos"].values

# Train/test split: 70/30 stratified on HbA1c label (M2), reproducible
from sklearn.model_selection import train_test_split
idx_all = np.arange(len(df_main))
idx_train, idx_test = train_test_split(idx_all, test_size=0.30,
                                        random_state=42, stratify=y_m2)

scaler = StandardScaler()
X_train = scaler.fit_transform(X[idx_train])
X_test  = scaler.transform(X[idx_test])

def train_model(X_tr, y_tr, w_tr):
    clf = LogisticRegression(max_iter=1000, solver="lbfgs", C=1.0)
    clf.fit(X_tr, y_tr, sample_weight=w_tr)
    return clf

def youden_threshold(y_true, probs, weights):
    """Youden-optimal threshold on weighted sens+spec."""
    thresholds = np.unique(probs)
    best_t, best_j = 0.5, -np.inf
    for t in thresholds:
        pred = (probs >= t).astype(float)
        tp = (weights * (pred == 1) * (y_true == 1)).sum()
        fn = (weights * (pred == 0) * (y_true == 1)).sum()
        tn = (weights * (pred == 0) * (y_true == 0)).sum()
        fp = (weights * (pred == 1) * (y_true == 0)).sum()
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0
        j = sens + spec - 1
        if j > best_j:
            best_j, best_t = j, t
    return best_t

clf_m1 = train_model(X_train, y_m1[idx_train], w[idx_train])
clf_m2 = train_model(X_train, y_m2[idx_train], w[idx_train])

prob_m1_train = clf_m1.predict_proba(X_train)[:, 1]
prob_m2_train = clf_m2.predict_proba(X_train)[:, 1]

thresh_m1 = youden_threshold(y_m1[idx_train], prob_m1_train, w[idx_train])
thresh_m2 = youden_threshold(y_m2[idx_train], prob_m2_train, w[idx_train])

prob_m1_test = clf_m1.predict_proba(X_test)[:, 1]
prob_m2_test = clf_m2.predict_proba(X_test)[:, 1]

pred_m1 = (prob_m1_test >= thresh_m1).astype(float)
pred_m2 = (prob_m2_test >= thresh_m2).astype(float)

print(f"  M1 (Diagnosed Label): Youden threshold = {thresh_m1:.4f}")
print(f"  M2 (HbA1c ≥ 6.5%):   Youden threshold = {thresh_m2:.4f}")

def weighted_auc(y_true, probs, weights):
    # Sample from weighted distribution for AUC
    return roc_auc_score(y_true, probs, sample_weight=weights)

auc_m1 = weighted_auc(y_m1[idx_test], prob_m1_test, w[idx_test])
auc_m2 = weighted_auc(y_m2[idx_test], prob_m2_test, w[idx_test])
print(f"\n  Overall weighted AUC:")
print(f"    M1: {auc_m1:.3f}")
print(f"    M2: {auc_m2:.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# E. SUBGROUP SENSITIVITY AND SPECIFICITY
# ─────────────────────────────────────────────────────────────────────────────
sep("E. SUBGROUP SENSITIVITY AND SPECIFICITY (Cross-Evaluation on HbA1c Truth)")

print("""
  EVALUATION DESIGN — Both models evaluated against HbA1c ≥ 6.5% as ground truth.
  This is the key cross-evaluation that reveals label bias:
    M1 trained on "diagnosed" label → evaluated on HbA1c truth
    M2 trained on HbA1c label      → evaluated on HbA1c truth
  If M1 has lower sensitivity for non-White groups against HbA1c truth, it means
  the model learned the biased diagnostic process and misses actual diabetics who
  were never diagnosed.
""")

def subgroup_perf(y_true, y_pred, weights, race_labels_arr):
    """Weighted sensitivity and specificity by racial/ethnic group."""
    rows = []
    for grp in RACE_ORDER:
        mask = race_labels_arr == grp
        if mask.sum() < 10:
            continue
        yt = y_true[mask]
        yp = y_pred[mask]
        wt = weights[mask]
        tp = (wt * (yp == 1) * (yt == 1)).sum()
        fn = (wt * (yp == 0) * (yt == 1)).sum()
        tn = (wt * (yp == 0) * (yt == 0)).sum()
        fp = (wt * (yp == 1) * (yt == 0)).sum()
        sens = tp / (tp + fn) if (tp + fn) > 0 else np.nan
        spec = tn / (tn + fp) if (tn + fp) > 0 else np.nan
        rows.append({"group": grp, "n": mask.sum(), "sens": sens, "spec": spec})
    return pd.DataFrame(rows)

test_race = df_main["race_label"].values[idx_test]
test_w    = w[idx_test]
y_hba1c_test = y_m2[idx_test]  # HbA1c ground truth for test set

# Both models evaluated against HbA1c truth
perf_m1 = subgroup_perf(y_hba1c_test, pred_m1, test_w, test_race)
perf_m2 = subgroup_perf(y_hba1c_test, pred_m2, test_w, test_race)

print("  M1 — Model trained on Diagnosed Label, evaluated on HbA1c ≥ 6.5% truth")
print(f"  {'Group':<40} {'N':>5} {'Sensitivity':>12} {'Specificity':>12}")
print("  " + "-"*72)
for _, row in perf_m1.iterrows():
    print(f"  {row['group']:<40} {int(row['n']):>5} {row['sens']*100:>11.1f}% {row['spec']*100:>11.1f}%")

print("\n  M2 — Model trained on HbA1c ≥ 6.5%, evaluated on HbA1c ≥ 6.5% truth")
print(f"  {'Group':<40} {'N':>5} {'Sensitivity':>12} {'Specificity':>12}")
print("  " + "-"*72)
for _, row in perf_m2.iterrows():
    print(f"  {row['group']:<40} {int(row['n']):>5} {row['sens']*100:>11.1f}% {row['spec']*100:>11.1f}%")

# Sensitivity gap vs NHWhite
print("\n  SENSITIVITY GAP TABLE — Gap vs. Non-Hispanic White (pp)")
print("  Positive gap = lower sensitivity than NHWhite (model misses more actual diabetics)")
print(f"\n  {'Group':<40} {'M1 Gap':>9} {'M2 Gap':>9} {'Gap closes by':>14}")
print("  " + "-"*75)

ref_m1 = perf_m1.loc[perf_m1["group"] == "Non-Hispanic White", "sens"].values[0]
ref_m2 = perf_m2.loc[perf_m2["group"] == "Non-Hispanic White", "sens"].values[0]

merged_perf = perf_m1.merge(perf_m2, on="group", suffixes=("_m1", "_m2"))
for _, row in merged_perf.iterrows():
    if row["group"] == "Non-Hispanic White":
        print(f"  {row['group']:<40} {'(ref)':>9} {'(ref)':>9} {'—':>14}")
        continue
    gap_m1 = (ref_m1 - row["sens_m1"]) * 100   # positive = NHW better
    gap_m2 = (ref_m2 - row["sens_m2"]) * 100
    closes = gap_m1 - gap_m2                    # positive = gap narrows
    print(f"  {row['group']:<40} {gap_m1:>+8.1f}pp {gap_m2:>+8.1f}pp {closes:>+13.1f}pp")

# ─────────────────────────────────────────────────────────────────────────────
# F. SPECIFICITY COST (M1 → M2)
# ─────────────────────────────────────────────────────────────────────────────
sep("F. SPECIFICITY COST — Switching from Diagnosed Label to HbA1c Criterion")

print()
print("  Specificity DROPS when switching M1 → M2 = false-positive burden increases.")
print()
print(f"  {'Group':<40} {'M1 Spec':>9} {'M2 Spec':>9} {'Cost (pp)':>10}")
print("  " + "-"*71)

for _, row in merged_perf.iterrows():
    spec_cost = (row["spec_m1"] - row["spec_m2"]) * 100
    print(f"  {row['group']:<40} {row['spec_m1']*100:>8.1f}% {row['spec_m2']*100:>8.1f}% {spec_cost:>+9.1f}pp")

# ─────────────────────────────────────────────────────────────────────────────
# G. AUC — FULL PSU BOOTSTRAP
# ─────────────────────────────────────────────────────────────────────────────
sep(f"G. AUC — Full PSU Bootstrap (B={N_BOOTSTRAP} replicates)")

print(f"\n  Method: resample PSUs with replacement within strata; for each replicate,")
print(f"  re-train + re-test (entire dataset varies). This is the correct method.")
print(f"  Running {N_BOOTSTRAP} replicates…\n")

psus_df = df_main[["SDMVPSU", "SDMVSTRA"]].reset_index(drop=True)
X_all = X
y_m1_all = y_m1
y_m2_all = y_m2
w_all = w

def psu_bootstrap_auc(X_all, y_m1_all, y_m2_all, w_all, psus_df, n_boot, seed=42):
    rng = np.random.default_rng(seed)
    aucs_m1, aucs_m2 = [], []

    unique_strata = psus_df["SDMVSTRA"].unique()

    for _ in range(n_boot):
        # Resample PSUs within strata
        boot_idx = []
        for stratum in unique_strata:
            s_mask = (psus_df["SDMVSTRA"] == stratum).values
            s_idx = np.where(s_mask)[0]
            psu_ids = psus_df.loc[s_idx, "SDMVPSU"].unique()
            n_psu = len(psu_ids)
            sampled_psus = rng.choice(psu_ids, size=n_psu, replace=True)
            for psu in sampled_psus:
                psu_mask = (psus_df["SDMVPSU"] == psu).values & s_mask
                boot_idx.extend(np.where(psu_mask)[0].tolist())

        boot_idx = np.array(boot_idx)
        if len(boot_idx) < 50:
            continue

        Xb, y1b, y2b, wb = X_all[boot_idx], y_m1_all[boot_idx], y_m2_all[boot_idx], w_all[boot_idx]

        n_b = len(Xb)
        tr_idx = rng.choice(n_b, size=int(0.7 * n_b), replace=False)
        te_mask = np.ones(n_b, dtype=bool)
        te_mask[tr_idx] = False

        if y1b[te_mask].sum() < 3 or y2b[te_mask].sum() < 3:
            continue
        if y1b[tr_idx].sum() < 3 or y2b[tr_idx].sum() < 3:
            continue
        if len(np.unique(y1b[te_mask])) < 2 or len(np.unique(y2b[te_mask])) < 2:
            continue

        try:
            sc = StandardScaler().fit(Xb[tr_idx])
            Xtr = sc.transform(Xb[tr_idx])
            Xte = sc.transform(Xb[te_mask])

            c1 = LogisticRegression(max_iter=500, solver="lbfgs", C=1.0)
            c1.fit(Xtr, y1b[tr_idx], sample_weight=wb[tr_idx])

            c2 = LogisticRegression(max_iter=500, solver="lbfgs", C=1.0)
            c2.fit(Xtr, y2b[tr_idx], sample_weight=wb[tr_idx])

            a1 = roc_auc_score(y1b[te_mask], c1.predict_proba(Xte)[:, 1],
                               sample_weight=wb[te_mask])
            a2 = roc_auc_score(y2b[te_mask], c2.predict_proba(Xte)[:, 1],
                               sample_weight=wb[te_mask])
            aucs_m1.append(a1)
            aucs_m2.append(a2)
        except Exception:
            continue

    return np.array(aucs_m1), np.array(aucs_m2)

aucs1, aucs2 = psu_bootstrap_auc(X_all, y_m1_all, y_m2_all, w_all, psus_df,
                                   n_boot=N_BOOTSTRAP)

def pct_ci(arr, lo=2.5, hi=97.5):
    return np.percentile(arr, lo), np.percentile(arr, hi)

ci1_lo, ci1_hi = pct_ci(aucs1)
ci2_lo, ci2_hi = pct_ci(aucs2)

print(f"  Successful replicates: M1={len(aucs1)}, M2={len(aucs2)}")
print(f"\n  Point estimates (main analysis):")
print(f"    M1 AUC: {auc_m1:.3f}")
print(f"    M2 AUC: {auc_m2:.3f}")
print(f"\n  95% CI (full PSU bootstrap, percentile):")
print(f"    M1: {ci1_lo:.3f} – {ci1_hi:.3f}  (width: {ci1_hi-ci1_lo:.3f})")
print(f"    M2: {ci2_lo:.3f} – {ci2_hi:.3f}  (width: {ci2_hi-ci2_lo:.3f})")
print(f"\n  CIs overlap: {'YES — models not statistically distinguishable' if ci1_lo < ci2_hi and ci2_lo < ci1_hi else 'NO'}")

# ─────────────────────────────────────────────────────────────────────────────
# H. BORDERLINE SENSITIVITY ANALYSES
# ─────────────────────────────────────────────────────────────────────────────
sep("H. BORDERLINE SENSITIVITY ANALYSES")
print(f"\n  Main analysis: Borderline (DIQ010=3, N={n_borderline}) EXCLUDED")
print(f"  Run 1: Borderline coded as POSITIVE (diagnosed=1)")
print(f"  Run 2: Borderline coded as NEGATIVE (diagnosed=0)")
print()

def run_borderline_sensitivity(merged_raw, action, label):
    df_s, _ = build_analysis_df(merged_raw, borderline_action=action)

    df_hba_s = df_s[df_s["hba1c_pos"] == 1.0].copy()
    df_hba_s["undiagnosed"] = 1.0 - df_hba_s["diagnosed"]

    undiag_s = {}
    for grp in ["Non-Hispanic Black", "Non-Hispanic White"]:
        sub = df_hba_s[df_hba_s["race_label"] == grp]
        if len(sub) < 20:
            continue
        prop, se, dof = taylor_prop(sub["undiagnosed"], sub["WTMEC2YR"],
                                    sub["SDMVPSU"], sub["SDMVSTRA"])
        lo, hi = ci(prop, se, dof)
        undiag_s[grp] = dict(prop=prop, se=se, dof=dof, lo=lo, hi=hi, n=len(sub))

    r_b_s = undiag_s["Non-Hispanic Black"]
    r_w_s = undiag_s["Non-Hispanic White"]
    diff_s = r_b_s["prop"] - r_w_s["prop"]
    se_d_s = np.sqrt(r_b_s["se"]**2 + r_w_s["se"]**2)
    dof_d_s = min(r_b_s["dof"], r_w_s["dof"])
    t_s_s = diff_s / se_d_s
    p_v_s = 2 * stats.t.sf(abs(t_s_s), df=dof_d_s)
    ratio_s = r_b_s["prop"] / r_w_s["prop"]

    print(f"  ── {label} ──────────────────────────────────────")
    print(f"  Analysis N: {len(df_s):,}")
    print(f"  NHBlack undiagnosis rate: {r_b_s['prop']*100:.1f}%  "
          f"(95% CI {r_b_s['lo']*100:.1f}%–{r_b_s['hi']*100:.1f}%)")
    print(f"  NHWhite undiagnosis rate: {r_w_s['prop']*100:.1f}%  "
          f"(95% CI {r_w_s['lo']*100:.1f}%–{r_w_s['hi']*100:.1f}%)")
    print(f"  Difference (B−W):         {diff_s*100:+.1f}pp")
    print(f"  Ratio (B/W):              {ratio_s:.2f}×")
    print(f"  p-value (two-sided):      {p_v_s:.4f}")
    print()
    return {
        "label": label,
        "N": len(df_s),
        "black_pct": r_b_s["prop"] * 100,
        "white_pct": r_w_s["prop"] * 100,
        "diff_pp": diff_s * 100,
        "ratio": ratio_s,
        "p_val": p_v_s,
    }

res_pos = run_borderline_sensitivity(merged, "positive", "Run 1 — Borderline as POSITIVE")
res_neg = run_borderline_sensitivity(merged, "negative", "Run 2 — Borderline as NEGATIVE")

print()
print("  ── SENSITIVITY COMPARISON TABLE ───────────────────────────────────")
print(f"  {'Analysis':<32} {'N':>6} {'Black':>8} {'White':>8} {'Diff':>8} {'Ratio':>7} {'p-val':>8}")
print("  " + "-"*80)

# Main result
print(f"  {'Main (Borderline excluded)':<32} {len(df_main):>6,} "
      f"{r_b['prop']*100:>7.1f}% {r_w['prop']*100:>7.1f}% "
      f"{diff*100:>+7.1f}pp {r_b['prop']/r_w['prop']:>6.2f}×  {p_v:>7.4f}")

print(f"  {res_pos['label'].split('—')[1].strip():<32} {res_pos['N']:>6,} "
      f"{res_pos['black_pct']:>7.1f}% {res_pos['white_pct']:>7.1f}% "
      f"{res_pos['diff_pp']:>+7.1f}pp {res_pos['ratio']:>6.2f}×  {res_pos['p_val']:>7.4f}")

print(f"  {res_neg['label'].split('—')[1].strip():<32} {res_neg['N']:>6,} "
      f"{res_neg['black_pct']:>7.1f}% {res_neg['white_pct']:>7.1f}% "
      f"{res_neg['diff_pp']:>+7.1f}pp {res_neg['ratio']:>6.2f}×  {res_neg['p_val']:>7.4f}")

print()
print("  Interpretation aid:")
print(f"    Main (excl.):  {r_b['prop']*100:.1f}% − {r_w['prop']*100:.1f}% = {diff*100:+.1f}pp, p={p_v:.4f}")
print(f"    Borderline+:   {res_pos['diff_pp']:+.1f}pp vs main {diff*100:+.1f}pp  "
      f"({'attenuates' if abs(res_pos['diff_pp']) < abs(diff*100) else 'amplifies'} gap)")
print(f"    Borderline−:   {res_neg['diff_pp']:+.1f}pp vs main {diff*100:+.1f}pp  "
      f"({'attenuates' if abs(res_neg['diff_pp']) < abs(diff*100) else 'amplifies'} gap)")

sep("COMPLETE — All sections done")
