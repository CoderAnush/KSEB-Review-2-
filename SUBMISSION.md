# Review 2 Submission — July–September 2026

**Project:** KSEB Agentic Decision Support System  
**Timeline:** July 2026 – September 2026  
**Status:** ✅ **ALL MILESTONES COMPLETED AND VERIFIED**

---

## What to Review

### 1. **Data Reconciliation (July 2026)**
Start here to understand the real-world baseline:

- **Field data:** `data/Data_final.xlsx` (8 days, May 5–12, 2025, 768 blocks)
- **Reconciliation findings:** `output/FINDINGS_KSEB_8DAY.md` (7 divergence analyses)
- **Reconciliation test:** `backend/tests/test_reconcile_8day.py` (validates cost totals)
- **Script:** `backend/scripts/reconcile_kseb_8day.py` (reproducible reconciliation)
- **Output artifacts:**
  - `output/reconciliation_stats.json` — validated cost total (₹2068610789.09)
  - `output/kseb_filedrop.csv` — ingestion-ready demand + price data
  - `output/kseb_8day_*.csv` — tidy schedules and hydro breakdown
  - `output/chart_demand_profile.png`, `chart_demand_delta.png`, `chart_deviation_pattern.png`,
    `chart_hydro_energy.png`, `chart_market_rates.png`, `chart_supply_mix.png` (6 charts from
    this real field data; 16 charts total across the full repo, see Section 3)

**Key Finding:** Real-world baseline is ₹2,068.6 Cr (₹258.6 M/day). The system must beat this.

---

### 2. **Forecasting Framework (August 2026)**
Understand how forecasts are built:

- **Feature engineering:** `backend/app/forecasting/features.py`
  - 13 features: lags (1/2/7-day), cyclical encoding, weather, holidays
  - Tests: `test_feature_frame_columns_and_no_nan`, `test_kerala_holidays_include_onam_and_fixed`

- **Models:** `backend/app/forecasting/models.py`
  - LightGBM quantile regression (p10/p50/p90)
  - SeasonalNaive fallback
  - Monotonicity enforcement (p10 ≤ p50 ≤ p90)
  - Tests: `test_lightgbm_quantile_fit_predict`, `test_seasonal_naive_predicts_shapes`

- **Backtesting:** `backend/app/forecasting/backtest.py`
  - Rolling-origin CV with 8 folds over 14-day windows
  - MAPE, MAE, pinball loss metrics
  - Test: `test_backtest_returns_finite_metrics`, `test_backtest_folds_exact_size_and_disjoint`

- **Model registry:** `backend/app/forecasting/registry.py`
  - Versioned save/load (v0001, v0002, ...)
  - Test: `test_registry_round_trip`

---

### 3. **Demand Forecasting Results (September 2026)**
This is what to showcase:

All three forecasting targets are complete, each with its own trained model, per-fold backtest
JSON, feature-importance chart, and holdout-forecast chart (16 charts total in `output/`):

- **Demand:**
  - MAPE: **2.74%** (target ≤3.0%) ✅ **EXCEEDS TARGET**
  - MAE: 105.4 MW
  - `output/real_fold_details.json`, `real_feature_importance.json`, `real_holdout_forecast.json`
  - `output/chart_real_validation_folds.png`, `chart_real_feature_importance.png`, `chart_real_holdout_forecast.png`

- **Price:**
  - MAE: **374.5 ₹/MWh** (target ≤600) ✅
  - `output/real_fold_details_price.json`, `real_feature_importance_price.json`, `real_holdout_forecast_price.json`
  - `output/chart_price_validation_folds.png`, `chart_price_feature_importance.png`, `chart_price_holdout_forecast.png`

- **Inflow:**
  - MAPE: **17.53%** (target ≤25.0%) ✅
  - `output/real_fold_details_inflow.json`, `real_feature_importance_inflow.json`, `real_holdout_forecast_inflow.json`
  - `output/chart_inflow_validation_folds.png`, `chart_inflow_feature_importance.png`, `chart_inflow_holdout_forecast.png`

All three: 8-fold rolling-origin backtest, pinball loss (p10/p90) computed, 0 NaNs and 0
P10≤P50≤P90 monotonicity violations across 2,881 holdout blocks each.

- **Evidence:**
  - `docs/metrics_forecasts.md` — auto-generated metrics table (all 3 targets)
  - `backend/scripts/eval_forecasts.py` — reproducible evaluation script
  - `backend/reports/extract_real_model_outputs.py` — produces the JSON above
  - `backend/scripts/generate_all_charts.py` — regenerates all 16 charts end-to-end
  - Run: `python -m scripts.eval_forecasts` or `python -m backend.scripts.generate_all_charts` to regenerate

---

## Test Execution

All 14 tests pass:

```bash
cd backend
pip install -e ".[dev]"
pip install lightgbm  # if not included in dev extras
pytest tests/ -v
```

**Expected output:**
```
test_db_sanitize.py::test_sanitize_lowercases_and_collapses_special_chars PASSED ✅
test_db_sanitize.py::test_sanitize_strips_leading_trailing_underscores .. PASSED ✅
test_db_sanitize.py::test_sanitize_never_returns_empty_string ........... PASSED ✅
test_db_sanitize.py::test_dedupe_disambiguates_collisions_deterministically PASSED ✅
test_db_sanitize.py::test_dedupe_is_a_noop_when_no_collisions ........... PASSED ✅
test_forecasting.py::test_feature_frame_columns_and_no_nan ............. PASSED ✅
test_forecasting.py::test_kerala_holidays_include_onam_and_fixed ....... PASSED ✅
test_forecasting.py::test_seasonal_naive_predicts_shapes .............. PASSED ✅
test_forecasting.py::test_lightgbm_quantile_fit_predict ............... PASSED ✅
test_forecasting.py::test_backtest_returns_finite_metrics ............. PASSED ✅
test_forecasting.py::test_registry_round_trip ........................ PASSED ✅
test_forecasting.py::test_calibrated_adapter_uses_configured_base ..... PASSED ✅
test_forecasting.py::test_backtest_folds_exact_size_and_disjoint ...... PASSED ✅
test_reconcile_8day.py::test_reconcile_reproduces_cost_and_filedrop ... PASSED ✅

Total: 14 passed
```

---

## Configuration Files

### `configs/forecasting.yaml`
Defines all forecasting targets (demand, price, inflow) with:
- Model choice (LightGBM)
- Lag configuration (1/2/7-day auto-regression)
- Weather features (temp, cloud, precipitation)
- Target metrics (MAPE ≤3% for demand, MAE ≤600 for price, etc.)
- Backtesting parameters (8 folds, 14-day windows, 180-day min train)

### `configs/adapters.yaml`
Data source configuration (for future use when expanding to live data)

---

## Code Organization

```
backend/app/
├── domain/
│   ├── entities.py          # Pydantic models (ForecastSet, etc.)
│   ├── enums.py             # ForecastTarget, etc.
│   ├── timeblocks.py        # IST 96-block calendar (the time authority)
│   └── configspecs.py       # Config dataclasses
├── adapters/
│   ├── base.py              # Adapter interface (AdapterHealth)
│   └── synthetic.py         # Synthetic data generator, calibrated from real KSEB data
├── forecasting/
│   ├── features.py          # Feature engineering (lags, temporal, weather)
│   ├── models.py            # LightGBM + SeasonalNaive
│   ├── backtest.py          # Rolling-origin backtesting
│   ├── registry.py          # Model save/load
│   └── __init__.py
├── db/                      # Optional Postgres layer for output/*.csv (needs [db] extra)
│   ├── connection.py
│   ├── load_csvs.py
│   ├── export_csvs.py
│   └── verify_roundtrip.py
├── config.py                # Configuration loader
└── logging_setup.py         # Logging setup

backend/reports/              # Report/chart generators (not imported by app/)
├── extract_real_model_outputs.py       # Trains models, writes real_*.json (all 3 targets)
├── plot_real_model_outputs.py          # real_*.json -> chart_{target}_*.png
├── generate_demand_calibration_chart.py
└── plot_kseb_reconciliation_charts.py

backend/tests/
├── test_forecasting.py      # 8 tests covering all forecasting components
├── test_reconcile_8day.py   # 1 test for data reconciliation
└── test_db_sanitize.py      # 5 tests for app/db column-name sanitization

backend/scripts/
├── eval_forecasts.py           # Auto-generate metrics report
├── reconcile_kseb_8day.py      # Reconcile field data to tidy CSVs
└── generate_all_charts.py      # Regenerate all 16 charts end-to-end

output/
└── FINDINGS_KSEB_8DAY.md    # Detailed reconciliation findings
```

---

## Key Assumptions

| ID | Assumption | July | August | Sept |
|----|------------|------|--------|------|
| A3 | 96 blocks per day (15 min each) | ✅ | ✅ | ✅ |
| A11 | CPU-sized models (LightGBM, no GPU) | | ✅ | ✅ |
| A13 | Time zone: IST (Asia/Kolkata) | ✅ | ✅ | ✅ |

---

## Reproducibility

Every result is reproducible:

1. **Test suite:** `pytest tests/` (no external APIs, all fixtures included)
2. **Metrics:** `python -m scripts.eval_forecasts` (regenerates `docs/metrics_forecasts.md`)
3. **Reconciliation:** `python -m scripts.reconcile_kseb_8day` (regenerates CSVs from `data/Data_final.xlsx`)

No manual steps. No external dependencies beyond the requirements in `pyproject.toml`.

---

## What's Next (October onwards)

This submission covers **data preparation & forecasting for all three targets** (demand, price,
inflow — Milestones 1–3, including forecasting work originally scoped as a later milestone but
completed within this submission).

The full project continues with:
- October: MILP-based hydro scheduling & procurement optimization
- November: Model enhancement with operational constraints
- December: RL-based pumped storage control policy
- January: Digital Twin simulation environment
- February: System integration & testing
- March: Documentation, thesis writing, final deployment

Those modules are held separately and will be included in future submissions.

---

## Summary

✅ **Data reconciled** from real KSEB field data (May 2025)  
✅ **Features engineered** (13 features, tested)  
✅ **Models trained** (LightGBM for 3 targets)  
✅ **Demand forecast validated** (2.74% MAPE, target ≤3%)  
✅ **All tests passing** (14/14)  
✅ **Reproducible** (scripts, fixtures, no external APIs)  

**Status:** Ready for review and deployment of forecasting module.

---

**Contact:** [Project maintainer]  
**Repository:** https://github.com/CoderAnush/KSEB-Review-2-
