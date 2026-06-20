"""
USASpending FY2023 Contracts — Verification Script
Research question: do small businesses awarded contracts just above the $250K
simplified acquisition threshold have lower completion rates than those below?

Completion proxy (locked): end_date == potential_end_date → 1, else 0
RDD window: $100K–$500K

Run with:
    source ~/snap_env/bin/activate
    pip install requests pandas pyarrow
    python3 usaspending_verify.py
"""

import os
import io
import zipfile
import requests
import pandas as pd

ZIP_URL   = None   # set to None — using local file instead
CACHE_ZIP = "/Users/vijaychamakuri/Downloads/FY2023_All_Contracts_Full_20260606"  # extracted folder
CACHE_CSV = "/Users/vijaychamakuri/Downloads/FY2023_contracts_sample.parquet"

LOW, HIGH, SAT = 100_000, 500_000, 250_000

# ── Column aliases to try (USASpending field names vary by extract version) ───
COL_AMOUNT   = ["base_and_all_options_value", "base_and_exercised_options_value"]
COL_START    = ["period_of_performance_start_date"]
COL_END      = ["period_of_performance_current_end_date"]
COL_POTEND   = ["period_of_performance_potential_end_date",
                "period_of_perf_potential_end_date"]
COL_BIZ      = ["business_types", "business_types_flags",
                 "business_categories", "contracting_officers_determination_of_business_size_code",
                 "contracting_officers_deter_of_bus_size_code",
                 "small_business_competitiveness_demonstration_program"]
COL_COMPETED = ["extent_competed", "extent_competed_code"]
COL_NAICS    = ["naics_code", "naics"]
COL_PIID     = ["award_id_piid", "piid", "contract_award_unique_key"]

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
checks = []

def gate(label, result, detail=""):
    status = PASS if result else FAIL
    checks.append((label, status, detail))
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return result

def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 65)
print("USASpending FY2023 Contracts — Verification Script")
print("=" * 65)

# ── Step 1: Locate source (folder or zip) ────────────────────────────────────
print("\n[1] Locate source data")
import glob

def find_csv_files(path):
    """Return list of CSV paths whether path is a folder, zip, or csv."""
    if os.path.isdir(path):
        csvs = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
        return ("dir", csvs)
    elif path.endswith(".zip") and os.path.isfile(path):
        return ("zip", [path])
    elif path.endswith(".csv") and os.path.isfile(path):
        return ("csv", [path])
    return ("not_found", [])

src_type, src_files = find_csv_files(CACHE_ZIP)
print(f"    Source type: {src_type}")
print(f"    Files found: {src_files}")
gate("Source data found", len(src_files) > 0, f"{src_type}: {CACHE_ZIP}")

# ── Step 2: Load ──────────────────────────────────────────────────────────────
print("\n[2] Load and filter to $100K–$500K window")
df_full = None
if os.path.exists(CACHE_CSV):
    print(f"    Using cached parquet: {CACHE_CSV}")
    df_full = pd.read_parquet(CACHE_CSV)
    print(f"    Rows in window (cache): {len(df_full):,}")
else:
    chunks = []
    total_rows = 0

    def stream_csv(filepath, is_zip_member=False):
        global total_rows
        open_fn = open if not is_zip_member else None
        reader = pd.read_csv(
            filepath, dtype=str, chunksize=200_000,
            encoding="utf-8", on_bad_lines="skip", low_memory=False
        )
        for chunk in reader:
            total_rows += len(chunk)
            ac = find_col(chunk, COL_AMOUNT)
            if ac:
                chunk[ac] = pd.to_numeric(chunk[ac], errors="coerce")
                w = chunk[chunk[ac].between(LOW, HIGH)]
                if len(w) > 0:
                    chunks.append(w)
            if total_rows % 1_000_000 == 0:
                print(f"    Scanned {total_rows/1e6:.0f}M rows...", end="\r")

    if src_type == "dir":
        for csv_path in src_files:
            print(f"    Reading: {os.path.basename(csv_path)}")
            stream_csv(csv_path)
    elif src_type == "zip":
        print("    Opening ZIP and streaming CSV...")
        with zipfile.ZipFile(CACHE_ZIP) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            print(f"    CSVs in ZIP: {csv_names}")
            for csv_name in csv_names:
                with zf.open(csv_name) as f:
                    stream_csv(f)
    elif src_type == "csv":
        stream_csv(CACHE_ZIP)

    print(f"\n    Total rows scanned: {total_rows:,}")
    if chunks:
        df_full = pd.concat(chunks, ignore_index=True)
        df_full.to_parquet(CACHE_CSV, index=False)
        print(f"    Window rows: {len(df_full):,}  (saved to {CACHE_CSV})")
    else:
        print("    ERROR: No rows found in $100K–$500K window")

gate("CSV loaded", df_full is not None and len(df_full) > 0,
     f"{len(df_full):,} rows in window" if df_full is not None else "0 rows")

if df_full is None:
    print("\nCannot continue — no data loaded.")
    raise SystemExit(1)

df = df_full.copy()
print(f"\n    All columns ({len(df.columns)}):")
for i, c in enumerate(sorted(df.columns)):
    print(f"      {c}")

# ── Step 3: Resolve columns ───────────────────────────────────────────────────
print("\n[3] Resolve key columns")
amt_col      = find_col(df, COL_AMOUNT)
start_col    = find_col(df, COL_START)
end_col      = find_col(df, COL_END)
potend_col   = find_col(df, COL_POTEND)
biz_col      = find_col(df, COL_BIZ)
competed_col = find_col(df, COL_COMPETED)
naics_col    = find_col(df, COL_NAICS)
piid_col     = find_col(df, COL_PIID)

resolved = {
    "amount":    amt_col,
    "start":     start_col,
    "end":       end_col,
    "potend":    potend_col,
    "biz_type":  biz_col,
    "competed":  competed_col,
    "naics":     naics_col,
    "piid":      piid_col,
}
for k, v in resolved.items():
    status = "✓" if v else "✗ MISSING"
    print(f"    {k:12s} → {v or 'NOT FOUND'} {status}")

gate("award_amount column found",    amt_col is not None,    str(amt_col))
gate("start_date column found",      start_col is not None,  str(start_col))
gate("end_date column found",        end_col is not None,    str(end_col))
gate("potential_end column found",   potend_col is not None, str(potend_col))
gate("business_type column found",   biz_col is not None,    str(biz_col))
gate("extent_competed column found", competed_col is not None, str(competed_col))
gate("naics_code column found",      naics_col is not None,  str(naics_col))
gate("piid column found",            piid_col is not None,   str(piid_col))

# ── Step 4: Numeric amount + threshold split ──────────────────────────────────
print("\n[4] Threshold split ($250K)")
df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce")
df = df[df[amt_col].between(LOW, HIGH)].copy()
n_total  = len(df)
n_above  = (df[amt_col] > SAT).sum()
n_below  = (df[amt_col] <= SAT).sum()
print(f"    Total in window:  {n_total:,}")
print(f"    Above $250K:      {n_above:,}  ({100*n_above/n_total:.1f}%)")
print(f"    At/Below $250K:   {n_below:,}  ({100*n_below/n_total:.1f}%)")
gate("N in window > 1000",    n_total > 1000,   f"N={n_total:,}")
gate("Both sides of threshold populated", n_above > 100 and n_below > 100,
     f"above={n_above:,}, below={n_below:,}")

# ── Step 5: Completion proxy ──────────────────────────────────────────────────
print("\n[5] Completion proxy (end_date == potential_end_date)")
if end_col and potend_col:
    df["end_clean"]    = pd.to_datetime(df[end_col],    errors="coerce").dt.date
    df["potend_clean"] = pd.to_datetime(df[potend_col], errors="coerce").dt.date
    both_valid         = df["end_clean"].notna() & df["potend_clean"].notna()
    df["completed"]    = (df["end_clean"] == df["potend_clean"]).astype(float)
    df.loc[~both_valid, "completed"] = float("nan")
    n_valid    = both_valid.sum()
    n_complete = (df["completed"] == 1).sum()
    pct_null   = 100 * (1 - n_valid / len(df))
    completion_rate = n_complete / n_valid * 100 if n_valid > 0 else 0
    print(f"    Valid (both dates non-null): {n_valid:,}  ({100*n_valid/len(df):.1f}%)")
    print(f"    Null rate: {pct_null:.1f}%")
    print(f"    Completed (proxy=1): {n_complete:,}  ({completion_rate:.1f}% of valid)")
    gate("Completion proxy computable",      n_valid > 0, f"valid={n_valid:,}")
    gate("Completion null rate < 50%",       pct_null < 50, f"{pct_null:.1f}% null")
    gate("Non-trivial completion variation", 5 < completion_rate < 95,
         f"{completion_rate:.1f}% completed")
else:
    gate("Completion proxy computable", False, "end_col or potend_col missing")
    print("    SKIP: Cannot compute proxy without both date columns")

# ── Step 6: Null rates ────────────────────────────────────────────────────────
print("\n[6] Null rates for key columns")
key_cols = {k: v for k, v in resolved.items() if v is not None}
for name, col in key_cols.items():
    null_rate = 100 * df[col].isna().sum() / len(df)
    status = "OK" if null_rate < 50 else "WARN"
    print(f"    {col:60s} null={null_rate:.1f}%  [{status}]")

# ── Step 7: Business type breakdown ──────────────────────────────────────────
print("\n[7] Business type value counts")
if biz_col:
    vc = df[biz_col].value_counts(dropna=False).head(20)
    print(vc.to_string())
    # Check if small business signal is present
    sb_signal = df[biz_col].astype(str).str.lower().str.contains(
        "small|sb|s", na=False
    ).sum()
    gate("Small business signal present in biz column", sb_signal > 0,
         f"{sb_signal:,} rows with 'small'/'sb' in {biz_col}")
else:
    gate("Small business signal present in biz column", False, "biz column not found")

# ── Step 8: Extent competed ───────────────────────────────────────────────────
print("\n[8] Extent competed value counts")
if competed_col:
    print(df[competed_col].value_counts(dropna=False).head(10).to_string())

# ── Verification Report ───────────────────────────────────────────────────────
print()
print("=" * 65)
print("VERIFICATION REPORT")
print("=" * 65)
all_pass = True
for label, status, detail in checks:
    all_pass = all_pass and (status == PASS)
    print(f"  [{status:4s}] {label}")
    if detail:
        print(f"         {detail}")

print()
if all_pass:
    print("OVERALL: PASS — proceed to analysis pipeline")
else:
    n_fail = sum(1 for _, s, _ in checks if s == FAIL)
    print(f"OVERALL: FAIL — {n_fail} check(s) failed — review above before proceeding")
