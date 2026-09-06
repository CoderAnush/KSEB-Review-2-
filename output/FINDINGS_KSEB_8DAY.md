# KSEB 8-Day Field Data Reconciliation — Findings & Fix Proposal

**Data:** `data/Data_final.xlsx` — 8 days (Mon 5 May → Mon 12 May 2025), 96 × 15-min blocks/day,
768 blocks. Treated as ground truth (expert-cleaned).
**System side:** `configs/*.yaml` + `backend/app/adapters/synthetic.py`.
**Artifacts:** tidy CSVs, `reconciliation_stats.json`, and `chart_*.png` in this folder.
**Status: APPROVED & IMPLEMENTED 2026-07-19 (ADR-14) — re-validation results in §6.**

---

## 1. Data profile

| Sheet | Content | Rows | Notes |
|---|---|---|---|
| `Hydro_final` | Station-wise hydro MW, pump-storage cascade grouping | 768 + 4 header | 4 "pump-group" stations: Idukki, Kakkad (L2 of Sabarigiri), Poringal (L2 of Sholayar), Sengulam (L2 of Pallivasal) |
| `Shedule break rate` | Per-source scheduled MW + ₹/kWh rate, demand, deviations, cost | 768 + trailer | THE market/schedule sheet; trailer row holds 8-day cost total |
| `Hydel` | Same stations, flat list | 768 | duplicate of Hydro_final station columns |
| `Final_data` | Schedule sheet ⨯ hydro breakdown merged | 768 + trailer | superset; used `Shedule break rate` + `Hydro_final` |

**Units:** MW per block; rates ₹/kWh; cost per block = MW × 0.25 h × rate × 1000.
Verified: block cost columns reproduce to <0.1%.

**Anomalies (flagged, not treated as wrong):**

- Sign convention: Idukki, Idamalayar, Neriamangalam, Panniyar are metered **negative**
  (SCADA export convention); totals use absolute values. Confirmed: `Hydel total` = Σ|station|.
- `Solar total` missing for 96 blocks (12 May) — one full day gap.
- Two header rows + trailer aggregate rows per sheet; sheet name has trailing space.
- Timestamps are day-first strings; Excel parsed some as month-first. Rebuilt canonical
  15-min IST index from row order (verified 768 rows = 8 × 96).

**Headline observations:** demand 2,930–5,130 MW (mean 4,018); evening peak at **block 89
(22:00)**; PX/RTM rates hit the **₹10/kWh ceiling** in 106/58 blocks (every evening);
KSEB **net-sells on PX in 407 of 768 blocks (53%)**, max sell 402 MW; hydro delivers
**24.1–27.3 GWh/day**; the sheet's own note: *"Objective function is to minimize this cost
either weekly or daily"* — 8-day realized total **₹2.0686 bn (₹258.6 M/day)**. That is the
real-world baseline our MILP must beat.

---

## 2. Field → system mapping

| Excel field | System parameter | File |
|---|---|---|
| ISGS MW + rate | `central_*` tranches | `configs/ppa_stack.yaml` |
| LTA / MTOA MW + rate | long/medium-term tranches | `configs/ppa_stack.yaml` |
| PX / RTM MW + rate | `market.*` (cap, floor, max_buy/sell) | `configs/ppa_stack.yaml` |
| REN MW + rate (₹2.8225) | *(no tranche exists today)* | — gap |
| OTS MW + rate (₹6.20) | *(no tranche exists today)* | — gap |
| Internal RATE/UNIT (₹1.238) | *(hydro cost not modeled)* | — gap |
| Total Demand | synthetic demand generator | `backend/app/adapters/synthetic.py` |
| Hydel total / station MW | `hydro.stations`, `daily_energy_budget_mwh` | `configs/psp_synthetic.yaml` |
| Sengulam/Kakkad/Poringal (pump levels) | synthetic PSP plant (A2) | `configs/psp_synthetic.yaml` |
| Scheduled vs Actual deviation | DSM free band / penalty cap | `configs/dsm.yaml` |
| Total Cost trailer | MILP objective / baseline comparator | `optimization`, `baseline_rule.yaml` |

---

## 3. Divergences (assumed vs observed)

### D1 — PPA stack is wrong in shape and price (A4) ⚠ largest impact

- **Assumed:** 3 invented tranches: ₹2.00/900 MW, ₹3.60/1600 MW, ₹4.50/1100 MW.
- **Observed:** 5 real tranches, flat rates all 8 days:
  LTA **₹3.076** (453–1175 MW) · ISGS **₹3.2732** (719–1516 MW) · MTOA **₹3.53** (0–717 MW) ·
  REN **₹2.8225** (0–479 MW) · OTS **₹6.20** (0–89 MW). No ₹2.00 central tranche exists; no
  ₹4.50 peaker exists — the peaker role is played by RTM/PX at up to ₹10.
- **Root cause:** A4 stack was invented pre-data.
- **Fix:** rewrite `ppa_stack.yaml` tranches to the observed 5, quanta from observed min/max,
  `must_run_mw` from observed minima — which also encodes Mr. Siddharthan's priority ladder
  (market committed > solar must-run > LTA/MTOA > CGS surrenderable).

### D2 — Baseline never sells; the real operator sells constantly

- **Assumed:** `baseline_rule.yaml: sell_when_surplus: false`.
- **Observed:** net PX sales in 53% of blocks (up to 402 MW), mostly off-peak/solar hours.
- **Root cause:** "conservative baseline" assumption; reality is two-way arbitrage.
- **Fix:** set `sell_when_surplus: true`. Makes the ≥5% savings comparator *harder* (honest).
- **Validated as-is:** `price_cap 10.0` (hit at peak), `max_buy_mw 1500` (max observed
  combined buy ≈ 1,397), `max_sell_mw 800` (max observed 402).

### D3 — Hydro energy budget is ~2.9× too small

- **Assumed:** `hydro.daily_energy_budget_mwh: 9000`.
- **Observed:** 24,089–27,304 MWh/day (mean **25,813**) — in the *dry* season.
- **Root cause:** A6 synthetic inflow scale invented; also synthetic inflow annual mean
  (9,000 MWh/day ≈ 3.3 TWh/yr) is ≈½ of Kerala's real ~7 TWh/yr hydro output.
- **Fix:** `daily_energy_budget_mwh: 25800` (provenance comment: May 2025 observed) and
  raise synthetic inflow `daily_mean_mwh` 9000 → 19000 (annual ≈ 6.9 TWh, matches Kerala
  actuals; May-2025 observed sits above the seasonal-mean curve — noted, not overfitted).

### D4 — Hydro fleet list & floors

- **Assumed:** 2 stations (Idukki 780 / Sabarigiri 340), `min_mw: 0`.
- **Observed:** 19 stations; the 8-day workhorses: Idukki 60.5–740.5, Sabarigiri 80.7–274.9,
  Kakkayam ≤196, Lower Periyar ≤117, Sholayar ≤54, Neriamangalam ≤59, Idamalayar ≤55, plus tail.
  Idukki never runs below **60.5 MW** when on (expert: 30 MW cavitation floor per unit).
- **Fix:** keep 2 modeled stations + add aggregated `other_hydro` (max ≈ 560 MW); set
  Idukki `min_mw: 30` (expert floor; data-consistent).

### D5 — Synthetic demand shape is structurally wrong (18.6% profile MAPE)

- **Assumed:** night base 0.80×, evening peak centred 20:30, peak/base 1.45/0.80.
- **Observed:** load at midnight ≈ 4,550 MW (≈ 0.97 of daily peak!) decaying to a
  **morning minimum at 08:30** (3,388 MW); peak at **22:00** (4,921 MW); ramp 1,533 MW.
  Synthetic under-predicts by up to **1,728 MW** around midnight (see `chart_demand_delta.png`).
- **Root cause:** generic "night valley" shape; Kerala's real valley is mid-morning
  (solar + commercial onset), and the evening peak is later and fatter than assumed.
- **Fix:** recalibrate `demand_shape()` in `backend/app/adapters/synthetic.py` to the observed
  96-block normalized profile (late fat peak at 22:00, midnight shoulder, 08:30 trough);
  re-validate by recomputing profile MAPE vs the 8 days (target: ≤5% from 18.6%).

### D6 — Internal hydro cost is not modeled

- **Observed:** KSEB books internal generation at **₹1.238/kWh**; it is the cheapest resource
  and the data's cost stack depends on it.
- **Fix:** add `hydro.cost_inr_per_kwh: 1.238` key (new assumption axis per CLAUDE.md ⇒ new
  config key + register entry) so MILP/twin cost accounting matches KSEB's books.

### D7 — PSP reality vs invented plant (A2) — evidence, no change proposed

- Data confirms three operating pumped/cascade pairs (Sengulam 33 MW, Kakkad ~37 MW,
  Poringal ≤67 MW) — combined ≈ 150 MW class, vs our invented 2×60 MW plant. Sengulam
  generation peaks at block 90 (22:15) exactly as the transcript describes (fill off-peak,
  generate at evening peak). η_rt config 0.77 vs expert "~80%" — within band, keep.
- **Action:** keep the synthetic plant (it is the *proposed* asset being valued) but record
  this evidence in the A2 comment block; A2/A4 sign-off evidence now exists.

### D8 — DSM calibration evidence — no change proposed

- Observed |deviation|: mean 1.8%, p95 8.0%, max 20.7% of schedule; 63% of blocks exceed the
  ±1% free band; 20 blocks exceed the 10% planned-deviation cap. The `daily_penalty_cap_inr`
  calibration story ("~2% one-sided miss passes") is consistent with observed means; keep,
  but note the p95 tail in the config comment.

---

## 4. Proposed change list (awaiting "Approved")

1. `configs/ppa_stack.yaml` — real 5-tranche stack + provenance comments (D1).
2. `configs/baseline_rule.yaml` — `sell_when_surplus: true` (D2).
3. `configs/psp_synthetic.yaml` — hydro budget 25,800 MWh/day, `other_hydro` aggregate,
   Idukki `min_mw: 30`, `cost_inr_per_kwh: 1.238`, A2 evidence note (D3/D4/D6/D7).
4. `backend/app/adapters/synthetic.py` — recalibrated `demand_shape()` (+ inflow
   `daily_mean_mwh` 19,000) with the 8-day profile as the fit target (D3/D5).
5. `output/kseb_filedrop.csv` — the 8 days converted to the `file_drop` adapter contract
   (`ts,series_id,value`) so a **real KSEB source** can be ingested (Phase-2 gate evidence).
6. `configs/baseline_rule.yaml` — solar pump window shifted to 10:00–14:00 (blocks 41–56),
   per chief-engineer guidance (E1 below).
7. `configs/forecasting.yaml` — add `precipitation` to demand `weather_features` (E2 below).
8. Re-validation: rerun the reconciliation script; report new demand-profile MAPE and
   confirm configs now bracket observed ranges.

All changes are additive/versioned via git; raw data untouched.

---

## 5. Expert validation — discussion with retired Chief Engineer (Mr. Siddharthan)

Source: `data/discussion-with-chief-engineer.txt`. Cross-checked against the 8-day data
and the system configs.

**Confirmed by both expert and data (no further change needed):**

- CGS base share 1,200–1,500 MW ↔ observed ISGS 719–1,516 MW (median 1,447) ↔ D1 tranche.
- ₹10/kWh market ceiling with buy-below-else-shed logic ↔ 164 blocks pinned at 10.0 ↔
  `price_cap_inr_per_kwh: 10.0`.
- Hydro availability ~1,300 MW of ~2,200–2,300 installed ↔ observed mean 1,076 / max 1,674.
- Idukki 30 MW/unit cavitation floor ↔ observed min 60.5 MW when running ↔ D4 `min_mw: 30`.
- PSP round-trip ~80% ↔ config η_rt 0.77 — keep.
- Sengulam (1973, Pallivasal tailrace) pumps off-peak / generates at peak ↔ observed gen
  peak at block 90; Kakkad fed by the Sabarigiri cascade ↔ sheet header "Level 2 of
  Sabrigiri". Direct A2 evidence.
- Priority ladder (market must-take > solar > LTA/MTOA > CGS surrenderable) ↔ ISGS observed
  dipping to ~50% of max while solar is never curtailed ↔ encoded as D1 `must_run_mw` floors.
- 96 × 15-min block universe; forecast = last-week pattern + holiday + weather ↔ A13 +
  `forecasting.yaml` lags [1,2,7] — design validated.

**Expert vs data disagreements (data wins; expert values kept as context):**

- Contract rates recalled as RE ₹3.25–3.45 / central ₹2.85 vs booked REN ₹2.8225 /
  ISGS ₹3.2732 / LTA ₹3.076 — D1 uses the booked rates.
- Demand 2,500→6,000 MW with 3,500 MW ramp is the annual worst-case envelope; this week
  shows 2,930→5,130 (ramp ≤ ~2,200). D5 follows the data; the expert envelope is kept as a
  twin stress-scenario bound. His "flat afternoon" is contradicted by ~4,200 MW afternoons.
- DAM/RTM "50-50, sometimes 60-40" is a planning heuristic; this week was RTM-heavy on buys
  with PX net-selling — documented, not hard-coded.

**⚠ Flagged conflict (needs KSEB clarification, not auto-resolved):** expert cites a ±200 MW
overdraw/injection limit; the data's `Actual Deviation` reaches 531 MW. Possibly a soft SLDC
discipline target vs a differently-defined column. Do not encode as a DSM constraint yet.

**New expert-only inputs adopted into the proposal:**

- **E1** — pump window during the solar surplus is 10:00–14:00 (we had 12:00–15:00) →
  change list item 6.
- **E2** — rain suppresses demand (cooling load) → add `precipitation` to demand
  `weather_features` → change list item 7.
- **E3 (noted, no change)** — corridor/advance-payment mechanics confirm A10 (bid-CSV
  export, never transact); Panniari water-hammer history supports a future conventional-hydro
  ramp constraint in the twin; KSEB's own PSP evaluation method ("readings from existing
  stations → add PSP → measure cost delta") is precisely this DSS's purpose — cite in the
  A2 sign-off narrative.

---

## 6. Re-validation results (post-implementation, same 8 days)

All changes implemented as ADR-14 (`docs/adr/README.md`); unit suite **406 passed / 0 failed**,
ruff clean. Re-run of this reconciliation against the identical dataset:

| Metric | Before | After |
|---|---|---|
| Demand profile MAPE (96-block mean shape) | 18.64% | **0.57%** |
| Demand block-by-block MAPE (all 768 blocks) | — | **4.51%** |
| PPA tranches bracket observed MW ranges | 0/5 tranches existed | **5/5 OK** |
| Hydro daily budget vs observed max 27.3 GWh | 9 GWh (exceeded every day) | **25.8 GWh OK** |
| Hydro fleet max vs observed max 1,674 MW | 1,120 MW (exceeded) | **1,680 MW OK** |
| Internal hydro cost in cost stack | absent | **₹1.238/kWh in MILP + twin** |

See `chart_demand_profile_after.png` for the before/after demand curve.

**Follow-ups (not blockers):**
- `docs/metrics_forecasts.md` (Gate-3 evidence) was produced by the OLD synthetic generator and
  must be deliberately re-promoted (change-control class D) — recorded in ADR-14.
- The ±200 MW overdraw claim remains flagged for KSEB clarification (§5).
- `output/kseb_filedrop.csv` is ready for `data/inbox/` ingestion via the file_drop adapter
  (first real source, Phase-2 gate).
