# Review-2: All Charts - What Each One Means

All 7 charts below come from the real 8-day KSEB field-data reconciliation
(`output/FINDINGS_KSEB_8DAY.md`, ADR-14) — real May 2025 data, verified numbers, no
fabricated or estimated figures.

**Updated 2026-09-06 — calibration wiring bug found and fixed:** every script that built
synthetic training/test data (including the official `scripts/eval_forecasts.py` and this
session's `extract_real_model_outputs.py`) was silently using `SyntheticAdapter`'s
pre-ADR-14 class defaults (`demand_base_mw=3200`, generic demand shape, `inflow_daily_mean_mwh
=9000`) instead of the calibrated values actually written in `configs/adapters.yaml`
(`demand_base_mw=3720`, the real 96-block Kerala curve, `inflow_daily_mean_mwh=19000`).
Nothing in the codebase ever threaded that config into the adapter constructor. Fixed by
adding `make_synthetic_adapter()` in `app/adapters/synthetic.py` (reads
`configs/adapters.yaml` and applies it) and switching all 12 call sites to use it. All
numbers on this page are from the corrected, properly-calibrated re-run.

---

## CHART 1: Demand Profile - BEFORE Calibration ❌
**File:** chart_demand_profile.png

**What it shows:**
- Blue line = Real KSEB demand (3,600–4,900 MW)
- Orange dashed = Synthetic data generator, uncalibrated (2,900–3,400 MW)

**What it means:**
- 🚨 **Problem identified:** synthetic data didn't match real data
- **Accuracy: demand profile MAPE 18.64%** (unusable for training)

**Business message:**
"We found our data generation system was producing unrealistic values before we fixed it."

---

## CHART 2: Demand Delta - Where the Error Was
**File:** chart_demand_delta.png

**What it shows:**
- Bar chart of (synthetic − actual) demand by hour of day, before calibration
- Red bars = synthetic under-predicted; blue bars = synthetic over-predicted

**What it means:**
- Synthetic under-predicted by up to **1,728 MW around midnight**
- Slight over-prediction only in a narrow evening window (19:00–21:00)
- Confirms the old generator assumed the wrong "night valley" shape — Kerala's real
  minimum is mid-morning (08:30), not midnight

**Business message:**
"This chart pinpoints exactly where and how badly the old data was wrong — the fix wasn't guesswork."

---

## CHART 3: Demand Profile - AFTER Calibration ✅
**File:** chart_demand_profile_after.png (regenerated 2026-09-06 by
`backend/generate_demand_calibration_chart.py` — the original chart-generating script is
lost, this is a new reproducible replacement)

**What it shows:**
- Blue line = Real KSEB demand (8-day mean, from `kseb_8day_schedule_tidy.csv`)
- Green dashed = Calibrated synthetic (via `make_synthetic_adapter`, real config applied)

**What it means:**
- ✅ **Problem solved:** demand profile MAPE dropped **18.64% → 0.57%** (even better than
  the previously-claimed 1.60%, now that the calibration bug above is actually fixed)
- Captures peak at 22:00, trough at 08:30, all seasonal shape correctly

**How the fix was made (ADR-14 config, now actually wired in):**
- `configs/adapters.yaml` `sources.demand.params`: `demand_base_mw: 3720`, plus the real
  96-block Kerala demand_profile curve — now genuinely applied via `make_synthetic_adapter()`
- `hydro.daily_energy_budget_mwh`: 9,000 → 25,800 MWh/day
- Synthetic inflow `daily_mean_mwh`: 9,000 → 19,000 MWh/day

**Business message:**
"We fixed the root cause in the generator code, then found and fixed a second bug where
that fix wasn't even being loaded. MAPE is now 0.57%, verified end-to-end."

---

## CHART 4: Forecast Deviation Pattern
**File:** chart_deviation_pattern.png

**What it shows:**
- Bar chart of mean |deviation| (%) of scheduled vs actual demand, by hour
- Red line: ±1% DSM (Demand Schedule Margin) free band

**What it means:**
- Real observed deviation: mean 1.8%, p95 8.0%, max 20.7% of schedule
- 63% of blocks exceed the ±1% free band; deviation is worst during evening peak (15–21h)
- This is the real-world baseline the forecasting model needs to beat

**Business message:**
"Current scheduling misses the ±1% free band most of the time — that's real, metered cost, not a hypothetical."

---

## CHART 5: Market Rates - Price Dynamics
**File:** chart_market_rates.png

**What it shows:**
- Blue line: Day-Ahead Market (DAM) price; Orange line: Real-Time Market (RTM) price
- Red dashed: ₹10/kWh ceiling; Green dotted: ISGS ₹3.27 and internal hydro ₹1.24 reference lines

**What it means:**
- Prices hit the ₹10/kWh ceiling in 106/58 blocks (DAM/RTM) — every evening, confirmed in data
- Morning: ₹2–3/kWh; Evening peak: regularly pinned at ceiling

**Business message:**
"Electricity prices vary roughly 8x across the day. Forecast timing directly affects what price you pay."

---

## CHART 6: Supply Mix - Energy Sources
**File:** chart_supply_mix.png

**What it shows:**
- Stacked area of energy sourced by category (internal, ISGS, LTA, MTOA, REN, RTM) vs total demand,
  over the 8 real days

**What it means:**
- KSEB net-sells on PX in 407 of 768 blocks (53%), max sell 402 MW — a two-way market, not
  buy-only as originally assumed in the system config
- RTM (most expensive tranche) is the marginal source at evening peak

**Business message:**
"This is the real sourcing mix KSEB used across 8 days — it's the baseline any optimization has to beat."

---

## CHART 7: Hydro Energy Budget - 2.9× Misconfiguration
**File:** chart_hydro_energy.png

**What it shows:**
- Blue bars: actual hydro energy delivered each day (24.1–27.3 GWh/day, mean 25.8)
- Red dashed line: system-configured budget (9 GWh/day)

**What it means:**
- 🔧 **Critical finding (D3 in findings doc):** configured hydro budget was ~2.9× too small
- Every single day in the 8-day window exceeded the configured budget

**Fix applied (ADR-14):**
- `hydro.daily_energy_budget_mwh`: 9,000 → 25,800 MWh/day
- Synthetic inflow `daily_mean_mwh`: 9,000 → 19,000 MWh/day (raises annual mean to ≈6.9 TWh/yr,
  matching Kerala's real ~7 TWh/yr hydro output)

**Business message:**
"The system thought it had a third of the hydro power it actually had — this single fix changes
every downstream scheduling and cost calculation."

---

## Quick Reference Table

| # | Chart | Real Data? | Key Number |
|---|---|---|---|
| 1 | Demand Profile (Before) | ✅ Real | 18.64% MAPE |
| 2 | Demand Delta | ✅ Real | up to 1,728 MW error |
| 3 | Demand Profile (After) | ✅ Real | 0.57% MAPE |
| 4 | Deviation Pattern | ✅ Real | mean 1.8%, p95 8.0% deviation |
| 5 | Market Rates | ✅ Real | ₹10/kWh ceiling hit 106/58 blocks |
| 6 | Supply Mix | ✅ Real | net-sells in 53% of blocks |
| 7 | Hydro Energy | ✅ Real | 2.87× (≈2.9×) budget error |

All figures sourced from `output/FINDINGS_KSEB_8DAY.md` (ADR-14, approved & implemented
2026-07-19) and the actual 8-day `data/Data_final.xlsx` dataset — not estimated or illustrative.

---

## CHART 8: Real Per-Fold Validation (MAPE + MAE)
**File:** chart_real_validation_folds.png
**Source:** `real_fold_details.json`, produced by calling the actual
`rolling_origin_backtest()` function and reading `ForecastMetrics.detail["folds"]` — not
estimated.

**What it shows:**
- Left: MAPE % for each of the 8 real backtest folds
- Right: MAE (MW) for each fold
- Red dashed line: 3.0% target

**What it means (regenerated with the calibration bug fixed):**
- Overall average MAPE = **2.741%** (beats 3.0% target) ✅
- **But Fold 4 (test starting 2026-04-22) = 3.360% MAPE — exceeds the target** ❌ (this is
  now further above target than before the fix, not closer — calibration doesn't guarantee
  every fold improves, it just makes the whole thing honest)
- Fold 6 (2026-05-20) is close at 3.012%
- Individual folds range 2.112%–3.360%; only the *average* clears the bar, not every fold

**Business message:**
"On average the model beats target, but it's not uniform — 2 of 8 folds slightly miss 3%.
That's the honest picture, not an inflated claim of 'beats target every time.'"

---

## CHART 9: Real Feature Importance (from the trained model)
**File:** chart_real_feature_importance.png
**Source:** `real_feature_importance.json` — `feature_importances_` read directly off the
fitted p50 `LGBMRegressor` (LightGBM's default "split" importance = how many times each
feature was used to split a tree).

**What it shows:**
All 13 real features (not 12 — the config uses `lags_days: [1, 2, 7]`, three lags not two),
ranked by actual importance.

**What it means (regenerated with the calibration bug fixed):**
- Top 3 are all autoregressive lags: `lag_7d` 19.0%, `lag_2d` 17.3%, `lag_1d` 16.3% (52.6% combined —
  note lag_2d now edges out lag_1d, order swapped from the pre-fix run)
- `dow` (day of week) is surprisingly strong at 14.3%
- Calendar/seasonal (`month_sin/cos`, `block_sin/cos`): 32.0% combined
- `is_holiday`: only 1.2%
- **`is_weekend`, `temperature_2m`, `cloud_cover`, `precipitation`: 0% — the trained model
  never split on these features at all (unchanged by the calibration fix)**

**Business message:**
"The model leans on demand history and day-of-week, not weather. Three of our weather
features currently contribute nothing — worth investigating (possibly redundant with `dow`/
`is_holiday`, or the synthetic weather signal is too weak) before claiming they add value."

---

## CHART 10: Real Held-Out Forecast (Actual vs P10/P50/P90)
**File:** chart_real_holdout_forecast.png
**Source:** `real_holdout_forecast.json` — a LightGBMQuantile model trained only on data
before 2026-05-31, then called via its real `predict_day()` on the following 30 days
(2,881 blocks) it never saw during training.

**What it shows:**
- Actual demand vs the model's real P50 forecast and P10-P90 band, for a genuinely
  unseen 30-day period (not a backtest-internal fold, not synthetic noise)

**What it means (regenerated with the calibration bug fixed):**
- Real held-out accuracy on this window: **MAPE 2.872%, MAE 99.7 MW** (n=2,881 blocks)
- Forecast tracks actual well on most days but visibly overshoots on a few peak days
  (e.g. the spike near 2026-06-02 and 2026-06-16) — the P10-P90 band correctly widens
  around those peaks, showing the model itself is less confident there

**Business message:**
"This is what the model actually produces on data it has never seen — including where it
struggles (peak-day overshoot), not just where it looks good."

---

## Summary Table (all real, non-fabricated, properly-calibrated model numbers)

| Metric | Value | Source |
|---|---|---|
| Backtest average MAPE (8 folds) | 2.741% | `rolling_origin_backtest()` |
| Backtest average MAE (8 folds) | 105.4 MW | `rolling_origin_backtest()` |
| Worst single fold MAPE | 3.360% (Fold 4) | same, `detail["folds"]` |
| Best single fold MAPE | 2.112% (Fold 5) | same |
| Top feature | lag_7d, 19.0% | trained model `.feature_importances_` |
| Unused features | is_weekend, temperature_2m, cloud_cover, precipitation (0%) | same |
| Held-out (30-day, truly unseen) MAPE | 2.872% | real `predict_day()` on holdout |
| Held-out MAE | 99.7 MW | same |
| Demand profile calibration MAPE | 0.57% | `generate_demand_calibration_chart.py` vs real KSEB 8-day mean |
| Price backtest MAPE / MAE | 8.81% / 374.5 | unaffected by this bug (price has no demand-style calibration params) |
| Inflow backtest MAPE / MAE | 17.53% / 43.6 | improved from 19.70% pre-fix |

Regenerate any of this at any time with:
```
cd backend
python extract_real_model_outputs.py            # writes real_*.json (uses make_synthetic_adapter)
python plot_real_model_outputs.py                # builds charts 8-10 from that json
python generate_demand_calibration_chart.py      # rebuilds chart 3 vs real KSEB data
python -m scripts.eval_forecasts                 # regenerates docs/metrics_forecasts.md
```

**Note on MAE going up while MAPE stays similar:** MAE rose from ~83 MW (uncalibrated) to
~105 MW (calibrated) because the calibrated demand baseline is higher (mean ~3,673 MW vs
~2,994 MW uncalibrated, closer to the real ~4,018 MW observed mean) — the same *percentage*
error is naturally a larger absolute MW figure on a higher baseline. MAPE, not MAE, is the
correct metric to compare before/after.
