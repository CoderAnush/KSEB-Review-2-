#!/usr/bin/env python3
"""Forensic audit harness - Phase 1 automated evidence gathering.
Read-only against output/ and configs/; writes only to ../audit_regenerated/.
Run from backend/:  python audit_forensic.py > ../audit_regenerated/phase1_output.txt 2>&1
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

import importlib
import json
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import numpy as np

ROOT = Path("..").resolve()
OUT = ROOT / "output"
AUDIT_OUT = ROOT / "audit_regenerated"
AUDIT_OUT.mkdir(exist_ok=True)

def section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

# ============================================================ 1. REPO INVENTORY
section("1. REPO INVENTORY")
exts = [".py", ".yaml", ".yml", ".json", ".csv", ".xlsx", ".md", ".png", ".jpg", ".svg"]
counts = {e: 0 for e in exts}
by_dir = {}
for p in ROOT.rglob("*"):
    if p.is_file() and ".venv" not in p.parts and "__pycache__" not in p.parts and "node_modules" not in p.parts:
        if p.suffix in counts:
            counts[p.suffix] += 1
            top = p.relative_to(ROOT).parts[0]
            by_dir.setdefault(top, {}).setdefault(p.suffix, 0)
            by_dir[top][p.suffix] += 1
print("Totals by extension:", counts)
print("\nBy top-level dir:")
for d, c in sorted(by_dir.items()):
    print(f"  {d}: {c}")

# ============================================================ 2. IMPORT HEALTH
section("2. IMPORT HEALTH (every .py under app/, scripts/, tests/, loose backend/*.py)")
backend = Path(".")
py_files = []
for sub in ["app", "scripts", "tests"]:
    py_files += list((backend / sub).rglob("*.py"))
py_files += list(backend.glob("*.py"))
py_files = [p for p in py_files if "__pycache__" not in p.parts and p.name != "audit_forensic.py"]

broken = []
for p in sorted(set(py_files)):
    rel = p.relative_to(backend)
    mod = str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
    if mod.startswith("."):
        continue
    try:
        importlib.import_module(mod)
    except Exception as e:
        broken.append((str(rel), f"{type(e).__name__}: {e}"))

print(f"Checked {len(set(py_files))} modules.")
if broken:
    print(f"BROKEN ({len(broken)}):")
    for f, e in broken:
        print(f"  ⚠️ {f}: {e}")
else:
    print("✅ All modules import cleanly.")

# ============================================================ 3. CONFIG WIRING CROSS-REFERENCE
section("3. CONFIG WIRING CROSS-REFERENCE")
import yaml
for cfgfile in ["adapters", "forecasting"]:
    path = ROOT / "configs" / f"{cfgfile}.yaml"
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    def flatten_keys(d, prefix=""):
        keys = []
        if isinstance(d, dict):
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                keys.append(full)
                keys += flatten_keys(v, full)
        return keys

    keys = flatten_keys(data)
    print(f"\n--- {cfgfile}.yaml: {len(keys)} keys ---")
    import subprocess
    for k in keys:
        leaf = k.split(".")[-1]
        try:
            result = subprocess.run(
                ["grep", "-rl", leaf, "app", "scripts"],
                cwd=str(backend), capture_output=True, text=True, timeout=10
            )
            hit_files = [f for f in result.stdout.splitlines() if f]
            status = "USED" if hit_files else "⚠️ NOT REFERENCED"
        except Exception as e:
            status = f"grep error: {e}"
        print(f"  {k:55s} -> {status}")

print("\n--- Checking for any remaining direct SyntheticAdapter( construction ---")
import subprocess
result = subprocess.run(
    ["grep", "-rn", "SyntheticAdapter(", "app", "scripts", "tests", "--include=*.py"],
    cwd=str(backend), capture_output=True, text=True
)
result2 = subprocess.run(
    ["grep", "-rln", "SyntheticAdapter(", ".", "--include=*.py"],
    cwd=str(backend), capture_output=True, text=True
)
print("Matches in app/scripts/tests:")
print(result.stdout or "(none)")
print("Matches repo-wide (backend/*.py loose scripts too):")
for line in result2.stdout.splitlines():
    print(" ", line)

print("\nDONE PHASE 1 PART A")
