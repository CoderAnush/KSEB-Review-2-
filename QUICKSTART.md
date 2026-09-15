# Quick Start — KSEB Review 2

**Repository:** https://github.com/CoderAnush/KSEB-Review-2-  
**Scope:** July–September 2026 (Forecasting, Data Reconciliation, Feature Engineering)

---

## 1-Minute Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
pip install lightgbm  # Required for forecasting model
```

---

## Run Tests (1 minute)

```bash
pytest tests/ -v
```

**Expected: 14/14 PASSED** ✅

```
test_db_sanitize.py::test_sanitize_lowercases_and_collapses_special_chars PASSED
test_db_sanitize.py::test_sanitize_strips_leading_trailing_underscores .. PASSED
test_db_sanitize.py::test_sanitize_never_returns_empty_string ........... PASSED
test_db_sanitize.py::test_dedupe_disambiguates_collisions_deterministically PASSED
test_db_sanitize.py::test_dedupe_is_a_noop_when_no_collisions ........... PASSED
test_forecasting.py::test_feature_frame_columns_and_no_nan ............. PASSED
test_forecasting.py::test_kerala_holidays_include_onam_and_fixed ....... PASSED
test_forecasting.py::test_seasonal_naive_predicts_shapes .............. PASSED
test_forecasting.py::test_lightgbm_quantile_fit_predict ............... PASSED
test_forecasting.py::test_backtest_returns_finite_metrics ............. PASSED
test_forecasting.py::test_registry_round_trip ........................ PASSED
test_forecasting.py::test_calibrated_adapter_uses_configured_base ..... PASSED
test_forecasting.py::test_backtest_folds_exact_size_and_disjoint ...... PASSED
test_reconcile_8day.py::test_reconcile_reproduces_cost_and_filedrop ... PASSED
```

---

## Regenerate Metrics (5 minutes)

```bash
# Evaluate demand/price/inflow forecasting models
python -m scripts.eval_forecasts

# Output: ../docs/metrics_forecasts.md
```

**Results:**
| Target | MAPE / MAE | Target | Status |
|--------|------------|--------|--------|
| Demand | 2.74% MAPE | ≤3.0% | ✅ PASS |
| Price | 374.5 ₹/MWh | ≤600 | ✅ PASS |
| Inflow | 17.53% MAPE | ≤25.0% | ✅ PASS |

---

## Reconcile Field Data (2 minutes)

```bash
# Regenerate reconciliation artifacts from data/Data_final.xlsx
python -m scripts.reconcile_kseb_8day --xlsx ../data/Data_final.xlsx --out-dir ../output

# Validates: Cost total = ₹2,068,610,789.09 ✅
```

---

## Files to Review

**Start with these:**

1. **README.md** — Project overview (you are here)
2. **SUBMISSION.md** — What to review and why
3. **output/FINDINGS_KSEB_8DAY.md** — Field data analysis & calibration findings

**Then code:**

4. **backend/app/forecasting/** — The forecasting pipeline
   - `features.py` — 13 engineered features
   - `models.py` — LightGBM + SeasonalNaive
   - `backtest.py` — Rolling-origin evaluation
   - `registry.py` — Model versioning

5. **backend/reports/** — Report/chart generators (produce this repo's deliverables)
   - `extract_real_model_outputs.py` — trains all 3 models, writes `real_*.json`
   - `plot_real_model_outputs.py` — turns that JSON into charts

6. **backend/tests/** — All tests with passing results
   - `test_forecasting.py` (8 tests) ✅
   - `test_reconcile_8day.py` (1 test) ✅
   - `test_db_sanitize.py` (5 tests) ✅

7. **backend/scripts/** — Reproducible evaluation
   - `eval_forecasts.py` — Auto-generate metrics
   - `reconcile_kseb_8day.py` — Validate field data
   - `generate_all_charts.py` — Regenerate all 16 charts end-to-end

**Evidence:**

8. **output/FINDINGS_KSEB_8DAY.md** — Analysis of divergences between synthetic and real data
9. **output/kseb_filedrop.csv** — Tidy demand + price data
10. **output/chart_*.png** (16 files total: 6 from real KSEB field data, 3 per forecasting
    target x 3 targets) — visualizations
11. **output/reconciliation_stats.json** — Validated cost totals
12. **docs/metrics_forecasts.md** — Backtest metrics (auto-generated)

---

## Key Numbers

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Demand MAPE** | 2.74% | ≤3.0% | ✅ Exceeds |
| **Price MAE** | 374.5 ₹/MWh | ≤600 | ✅ Pass |
| **Inflow MAPE** | 17.53% | ≤25.0% | ✅ Pass |
| **Backtest folds** | 8 | — | 400 days |
| **Tests passing** | 14/14 | — | ✅ All pass |
| **Charts regenerable** | 16/16 | — | ✅ Complete |

---

## Architecture

Design intent for a live daily pipeline (the orchestration layer below - a `run_forecasts()`
service that would call this on a schedule - is not implemented in this submission; what
actually runs is `backend/reports/extract_real_model_outputs.py`, invoked manually or via
`scripts/generate_all_charts.py`, which performs the same feature-engineering -> train ->
predict -> monotonicity steps, just without the daily-schedule/DB-persistence wrapper):

```
Forecasting Pipeline (Daily, design intent)

  History (400 days, this submission)
      ↓
  Feature Engineering (lags, temporal, weather, holidays)
      ↓
  Load Model (or train if new)
      ↓
  Predict Day (p10, p50, p90 quantiles for 96 blocks)
      ↓
  Enforce Monotonicity (p10 ≤ p50 ≤ p90)
      ↓
  Persist to DB   ← not wired in this submission (see backend/app/db/ for the separate,
      ↓             optional CSV->Postgres loader, which is unrelated to this pipeline)
  Return ForecastSet
```

---

## What's NOT Included

- MILP-based hydro scheduling & procurement optimization (October)
- Model enhancement with operational constraints (November)
- RL-based pumped storage control (December)
- Digital Twin simulation (January)
- System integration & testing (February)
- Documentation, thesis, final deployment (March)

These are in the full project and will be added in future submissions.

---

## Troubleshooting

**ImportError: No module named 'lightgbm'**
```bash
pip install lightgbm
```

**Tests fail with "ModuleNotFoundError: No module named 'app'"**
```bash
cd backend  # Make sure you're in the backend directory
pytest tests/ -v
```

**Reconciliation script fails**
```bash
pip install openpyxl  # Required for Excel parsing
python -m scripts.reconcile_kseb_8day --xlsx ../data/Data_final.xlsx --out-dir ../output
```

---

## Summary

✅ **Data prepared** from real KSEB field data (May 2025)  
✅ **Features engineered** (13 features, all tested)  
✅ **Models trained** (LightGBM for demand, price, inflow)  
✅ **Demand forecast** MAPE 2.74% (target ≤3.0%) **EXCEEDS TARGET**  
✅ **All tests passing** (14/14)  
✅ **Reproducible** (no external APIs, all scripts work standalone)  

**You're ready to present September completion!**

---

**Questions?** See SUBMISSION.md for detailed review guide.
