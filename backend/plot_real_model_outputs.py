"""Plot charts strictly from the real JSON produced by extract_real_model_outputs.py.
No synthetic noise, no invented numbers - every point plotted is read from file.

Covers all three forecasting targets: demand, price, inflow.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

OUT_DIR = Path(__file__).parent.parent / "output"

# demand keeps its original (unsuffixed) filenames; price/inflow use a suffix
TARGETS = {
    "demand": {
        "suffix": "",
        "label": "Demand",
        "unit": "MW",
        "target_line": 3.0,
        "target_metric": "MAPE",
    },
    "price": {
        "suffix": "_price",
        "label": "Price",
        "unit": "INR/MWh",
        "target_line": None,
        "target_metric": None,
    },
    "inflow": {
        "suffix": "_inflow",
        "label": "Inflow",
        "unit": "MWh",
        "target_line": 25.0,
        "target_metric": "MAPE",
    },
}


def plot_validation_folds(target_key: str, cfg: dict) -> None:
    suffix = cfg["suffix"]
    label = cfg["label"]

    with open(OUT_DIR / f"real_fold_details{suffix}.json", encoding="utf-8") as fh:
        fold_data = json.load(fh)

    folds = fold_data["folds"]
    labels = [f"Fold {f['fold']}\n{f['test_start']}" for f in folds]
    mape = [f["mape_pct"] for f in folds]
    mae = [f["mae"] for f in folds]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.5))

    target_line = cfg["target_line"]
    colors_mape = ["#DC3545" if (target_line and m > target_line) else "#001F3F" for m in mape]
    ax1.plot(range(len(labels)), mape, marker="o", linewidth=2, color="#001F3F", zorder=2)
    for i, (m, c) in enumerate(zip(mape, colors_mape)):
        ax1.scatter(i, m, color=c, s=90, zorder=3, edgecolor="black")
    if target_line:
        ax1.axhline(y=target_line, color="red", linestyle="--", linewidth=2, label=f"Target ({target_line}%)")
        ax1.legend(fontsize=9)
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=8.5)
    ax1.set_ylabel("MAPE (%)", fontsize=11, fontweight="bold")
    ax1.set_title(f"Real Per-Fold {label} MAPE (rolling_origin_backtest, {fold_data['n_folds']} folds)",
                  fontsize=11.5, fontweight="bold", color="#001F3F")
    ax1.grid(True, alpha=0.3)
    for i, m in enumerate(mape):
        ax1.annotate(f"{m:.2f}%", (i, m), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

    ax2.bar(range(len(labels)), mae, color="#2ECC40", edgecolor="#001F3F", linewidth=1.2)
    ax2.axhline(y=fold_data["overall_mae"], color="#001F3F", linestyle="--", linewidth=2,
                label=f"Average: {fold_data['overall_mae']:.1f} {cfg['unit']}")
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=8.5)
    ax2.set_ylabel(f"MAE ({cfg['unit']})", fontsize=11, fontweight="bold")
    ax2.set_title(f"Real Per-Fold {label} MAE", fontsize=11.5, fontweight="bold", color="#001F3F")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis="y")
    for i, m in enumerate(mae):
        ax2.annotate(f"{m:.1f}", (i, m), textcoords="offset points", xytext=(0, 5), ha="center", fontsize=8)

    plt.tight_layout()
    out_name = f"chart_{target_key}_validation_folds.png" if suffix else "chart_real_validation_folds.png"
    plt.savefig(OUT_DIR / out_name, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] {out_name}  (overall MAPE={fold_data['overall_mape_pct']:.2f}%, MAE={fold_data['overall_mae']:.1f})")


def plot_feature_importance(target_key: str, cfg: dict) -> None:
    suffix = cfg["suffix"]
    label = cfg["label"]

    with open(OUT_DIR / f"real_feature_importance{suffix}.json", encoding="utf-8") as fh:
        feat_data = json.load(fh)

    feats = feat_data["features"]
    names = [f["name"] for f in feats]
    pcts = [f["pct"] for f in feats]

    fig, ax = plt.subplots(figsize=(11, 6))
    colors = ["#2ECC40" if p > 0 else "#CCCCCC" for p in pcts]
    ax.barh(range(len(names)), pcts, color=colors, edgecolor="#001F3F", linewidth=0.8)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel(f"Feature Importance (%, LightGBM '{feat_data['importance_type']}' count, p50 model)",
                  fontsize=11, fontweight="bold")
    ax.set_title(f"Real Feature Importance - Trained LightGBM Model ({label}, p50)",
                 fontsize=13, fontweight="bold", color="#001F3F")
    for i, p in enumerate(pcts):
        text_label = f"{p:.1f}%" if p > 0 else "0% (unused)"
        ax.text(p + 0.3, i, text_label, va="center", fontsize=9.5,
                fontweight="bold" if p > 0 else "normal",
                color="#333333" if p > 0 else "#999999")
    ax.set_xlim(0, max(pcts) * 1.25)
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    out_name = f"chart_{target_key}_feature_importance.png" if suffix else "chart_real_feature_importance.png"
    plt.savefig(OUT_DIR / out_name, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] {out_name}")


def plot_holdout_forecast(target_key: str, cfg: dict) -> tuple[float, float, int]:
    suffix = cfg["suffix"]
    label = cfg["label"]
    unit = cfg["unit"]

    with open(OUT_DIR / f"real_holdout_forecast{suffix}.json", encoding="utf-8") as fh:
        holdout = json.load(fh)

    rows = pd.DataFrame(holdout["rows"])
    rows["ts"] = pd.to_datetime(rows["ts"])
    rows = rows.sort_values("ts").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(rows["ts"], rows["actual"], label=f"Actual {label}", color="#001F3F", linewidth=1.8)
    ax.plot(rows["ts"], rows["p50"], label="P50 Forecast (real model output)", color="#2ECC40",
            linewidth=1.6, linestyle="--", alpha=0.9)
    ax.fill_between(rows["ts"], rows["p10"], rows["p90"], alpha=0.22, color="#2ECC40",
                     label="P10-P90 band (real model output)")
    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel(f"{label} ({unit})", fontsize=12, fontweight="bold")
    ax.set_title(f"Real Held-Out Forecast vs Actual - Trained on data before {holdout['cutoff'][:10]}, "
                 f"predicted {len(rows)} blocks after",
                 fontsize=12.5, fontweight="bold", color="#001F3F")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    out_name = f"chart_{target_key}_holdout_forecast.png" if suffix else "chart_real_holdout_forecast.png"
    plt.savefig(OUT_DIR / out_name, dpi=300, bbox_inches="tight")
    plt.close()

    mape_holdout = (
        (rows["actual"] - rows["p50"]).abs() / rows["actual"].abs()
    ).replace([float("inf")], float("nan")).dropna().mean() * 100
    mae_holdout = (rows["actual"] - rows["p50"]).abs().mean()
    print(f"[OK] {out_name}  (held-out MAPE={mape_holdout:.3f}%, MAE={mae_holdout:.3f} {unit}, n={len(rows)})")
    return mape_holdout, mae_holdout, len(rows)


def main():
    """Generate all validation/importance/holdout charts for demand, price, and inflow."""
    for target_key, cfg in TARGETS.items():
        print(f"\n=== {cfg['label']} ===")
        plot_validation_folds(target_key, cfg)
        plot_feature_importance(target_key, cfg)
        plot_holdout_forecast(target_key, cfg)

    print("\nAll charts generated from real JSON files - zero fabricated values.")


if __name__ == "__main__":
    main()
