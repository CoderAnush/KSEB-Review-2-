#!/usr/bin/env python3
"""Forensic audit harness - Phase 1 Part C: seed/config sensitivity (dead-config detector)."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from datetime import date
from app.adapters.synthetic import SyntheticAdapter, make_synthetic_adapter

def section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

section("4. SEED / CONFIG SENSITIVITY TEST (dead-config detector)")

d = date(2026, 5, 15)

# --- Reproducibility: same seed twice ---
a1 = make_synthetic_adapter("demand", "demand_mw")
a2 = make_synthetic_adapter("demand", "demand_mw")
p1 = a1.generate_day(d)
p2 = a2.generate_day(d)
same = all(x.value == y.value for x, y in zip(p1, p2))
print(f"Same seed (42) twice, demand day {d}: identical output = {same}  (must be True)")

# --- Different seed changes output ---
a3 = SyntheticAdapter("demand", "demand_mw", seed=999, demand_base_mw=3720)
p3 = a3.generate_day(d)
diff = any(x.value != y.value for x, y in zip(p1, p3))
print(f"Different seed (999) vs (42): output differs = {diff}  (must be True)")

# --- Parameter sensitivity: 5 params, baseline vs changed ---
print("\n--- Parameter change sensitivity (5 params) ---")
baseline = make_synthetic_adapter("demand", "demand_mw")
base_vals = [p.value for p in baseline.generate_day(d)]
base_mean = sum(base_vals) / len(base_vals)
print(f"Baseline (demand_base_mw=3720): mean={base_mean:.2f} MW")

for new_base in [2000.0, 5000.0]:
    changed = SyntheticAdapter("demand", "demand_mw", seed=42, demand_base_mw=new_base,
                                demand_profile=baseline.demand_profile)
    vals = [p.value for p in changed.generate_day(d)]
    mean = sum(vals) / len(vals)
    direction = "increased" if mean > base_mean else "decreased" if mean < base_mean else "UNCHANGED (dead!)"
    print(f"  demand_base_mw={new_base}: mean={mean:.2f} MW  ({direction} vs baseline)")

baseline_inflow = make_synthetic_adapter("inflow", "inflow_mwh")
base_inflow_vals = [p.value for p in baseline_inflow.generate_day(d)]
base_inflow_mean = sum(base_inflow_vals) / len(base_inflow_vals)
print(f"\nBaseline inflow (inflow_daily_mean_mwh=19000): mean={base_inflow_mean:.3f} MWh/block")
for new_inflow in [5000.0, 40000.0]:
    changed = SyntheticAdapter("inflow", "inflow_mwh", seed=44, inflow_daily_mean_mwh=new_inflow)
    vals = [p.value for p in changed.generate_day(d)]
    mean = sum(vals) / len(vals)
    direction = "increased" if mean > base_inflow_mean else "decreased" if mean < base_inflow_mean else "UNCHANGED (dead!)"
    print(f"  inflow_daily_mean_mwh={new_inflow}: mean={mean:.3f}  ({direction} vs baseline)")

# demand_profile param: change one value drastically, see if that specific block changes
print(f"\nBaseline demand_profile[0] (block 1, midnight) = {baseline.demand_profile[0]}")
modified_profile = list(baseline.demand_profile)
modified_profile[0] = modified_profile[0] * 3.0  # triple the midnight block shape factor
changed = SyntheticAdapter("demand", "demand_mw", seed=42, demand_base_mw=3720, demand_profile=modified_profile)
block1_base = baseline.generate_day(d)[0].value
block1_changed = changed.generate_day(d)[0].value
print(f"  block 1 value: baseline={block1_base:.2f} MW  after tripling profile[0]={block1_changed:.2f} MW  "
      f"(changed: {block1_base != block1_changed})")

# seed as 5th param (already tested above via a1 vs a3), summarize
print(f"\nSeed parameter: already shown above to change output (42 vs 999).")

print("\nDONE PHASE 1 PART C")
