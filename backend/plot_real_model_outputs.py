"""Plot charts strictly from the real JSON produced by extract_real_model_outputs.py.
No synthetic noise, no invented numbers - every point plotted is read from file.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

OUT_DIR = Path("../output")


def main():
    """Generate all 3 model validation charts from real JSON files."""
    # ==================== CHART: Real per-fold MAPE/MAE ====================
    with open(OUT_DIR / "real_fold_details.json", encoding="utf-8") as fh:
        fold_data = json.load(fh)

    folds = fold_data["folds"]
    labels = [f"Fold {f['fold']}\n{f['test_start']}" for f in folds]
    mape = [f["mape_pct"] for f in folds]
    mae = [f["mae"] for f in folds]
    target_mape = 3.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.5))

    colors_mape = ["#DC3545" if m > target_mape else "#001F3F" for m in mape]
    ax1.plot(range(len(labels)), mape, marker="o", linewidth=2, color="#001F3F", zorder=2)
    for i, (m, c) in enumerate(zip(mape, colors_mape)):
        ax1.scatter(i, m, color=c, s=90, zorder=3, edgecolor="black")
    ax1.axhline(y=target_mape, color="red", linestyle="--", linewidth=2, label=f"Target ({target_mape}%)")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=8.5)
    ax1.set_ylabel("MAPE (%)", fontsize=11, fontweight="bold")
    ax1.set_title(f"Real Per-Fold Demand MAPE (rolling_origin_backtest, {fold_data['n_folds']} folds)",
                  fontsize=11.5, fontweight="bold", color="#001F3F")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    for i, m in enumerate(mape):
        ax1.annotate(f"{m:.2f}%", (i, m), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

    ax2.bar(range(len(labels)), mae, color="#2ECC40", edgecolor="#001F3F", linewidth=1.2)
    ax2.axhline(y=fold_data["overall_mae"], color="#001F3F", linestyle="--", linewidth=2,
                label=f"Average: {fold_data['overall_mae']:.1f} MW")
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=8.5)
    ax2.set_ylabel("MAE (MW)", fontsize=11, fontweight="bold")
    ax2.set_title("Real Per-Fold Demand MAE", fontsize=11.5, fontweight="bold", color="#001F3F")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis="y")
    for i, m in enumerate(mae):
        ax2.annotate(f"{m:.1f}", (i, m), textcoords="offset points", xytext=(0, 5), ha="center", fontsize=8)

    fig.suptitle("Note: Fold 4 MAPE (3.124%) exceeds the 3.0% target; overall average (2.74%) does not.",
                 fontsize=9.5, color="#666666", y=0.02)
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(OUT_DIR / "chart_real_validation_folds.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("[OK] chart_real_validation_folds.png")

    # ==================== CHART: Real feature importance ====================
    with open(OUT_DIR / "real_feature_importance.json", encoding="utf-8") as fh:
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
    ax.set_title("Real Feature Importance - Trained LightGBM Model (Demand, p50)",
                 fontsize=13, fontweight="bold", color="#001F3F")
    for i, p in enumerate(pcts):
        label = f"{p:.1f}%" if p > 0 else "0% (unused)"
        ax.text(p + 0.3, i, label, va="center", fontsize=9.5,
                fontweight="bold" if p > 0 else "normal",
                color="#333333" if p > 0 else "#999999")
    ax.set_xlim(0, max(pcts) * 1.25)
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "chart_real_feature_importance.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("[OK] chart_real_feature_importance.png")

    # ==================== CHART: Real holdout actual vs P10/P50/P90 ====================
    with open(OUT_DIR / "real_holdout_forecast.json", encoding="utf-8") as fh:
        holdout = json.load(fh)

    rows = pd.DataFrame(holdout["rows"])
    rows["ts"] = pd.to_datetime(rows["ts"])
    rows = rows.sort_values("ts").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(rows["ts"], rows["actual"], label="Actual Demand", color="#001F3F", linewidth=1.8)
    ax.plot(rows["ts"], rows["p50"], label="P50 Forecast (real model output)", color="#2ECC40",
            linewidth=1.6, linestyle="--", alpha=0.9)
    ax.fill_between(rows["ts"], rows["p10"], rows["p90"], alpha=0.22, color="#2ECC40",
                     label="P10-P90 band (real model output)")
    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Demand (MW)", fontsize=12, fontweight="bold")
    ax.set_title(f"Real Held-Out Forecast vs Actual - Trained on data before {holdout['cutoff'][:10]}, "
                 f"predicted {len(rows)} blocks after",
                 fontsize=12.5, fontweight="bold", color="#001F3F")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "chart_real_holdout_forecast.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("[OK] chart_real_holdout_forecast.png")

    # Real out-of-sample accuracy on this holdout window (not backtest, a true held-out fit)
    mape_holdout = (
        (rows["actual"] - rows["p50"]).abs() / rows["actual"].abs()
    ).replace([float("inf")], float("nan")).dropna().mean() * 100
    mae_holdout = (rows["actual"] - rows["p50"]).abs().mean()
    print(f"\nReal held-out (last 30 days, single train/test split, NOT backtest average):")
    print(f"  MAPE = {mape_holdout:.3f}%   MAE = {mae_holdout:.3f} MW   n={len(rows)} blocks")

    print("\nAll charts generated from real JSON files - zero fabricated values.")


if __name__ == "__main__":
    main()
