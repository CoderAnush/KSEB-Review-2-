from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from app.domain import timeblocks as tb
from app.domain.enums import ForecastTarget
from app.forecasting.features import feature_columns
from app.logging_setup import get_logger

log = get_logger(__name__)


def quantile_label(q: float) -> str:
    return f"p{round(q * 100)}"


@runtime_checkable
class QuantileForecaster(Protocol):
    name: str

    def fit(self, frame: pd.DataFrame) -> None: ...

    def predict_day(self, frame_future: pd.DataFrame) -> dict[str, list[float]]: ...


def _monotone(quantiles: list[float], preds: dict[str, np.ndarray]) -> dict[str, list[float]]:
    """Sort per-row so p10 <= p50 <= p90 regardless of independent model noise."""
    labels = [quantile_label(q) for q in sorted(quantiles)]
    matrix = np.vstack([preds[lab] for lab in labels])
    matrix.sort(axis=0)
    return {lab: matrix[i].tolist() for i, lab in enumerate(labels)}


class SeasonalNaive:
    """p50 = value 7 days earlier; band from historical residual quantiles.

    Zero-dependency fallback used when LightGBM is unavailable and as the
    benchmark floor every learned model must beat.
    """

    name = "seasonal_naive"

    def __init__(self, quantiles: list[float]) -> None:
        self.quantiles = quantiles
        self._offsets: dict[str, float] = {quantile_label(q): 0.0 for q in quantiles}

    def fit(self, frame: pd.DataFrame) -> None:
        if "lag_7d" not in frame.columns:
            raise ValueError("SeasonalNaive needs lag_7d in the feature frame")
        residuals = (frame["value"] - frame["lag_7d"]).dropna().to_numpy()
        for q in self.quantiles:
            self._offsets[quantile_label(q)] = float(np.quantile(residuals, q)) if len(residuals) else 0.0

    def predict_day(self, frame_future: pd.DataFrame) -> dict[str, list[float]]:
        base = frame_future["lag_7d"].to_numpy(dtype=float)
        preds = {lab: base + off for lab, off in self._offsets.items()}
        return _monotone(self.quantiles, preds)


class LightGBMQuantile:
    """One LGBMRegressor per quantile (objective='quantile'). CPU-sized (A11)."""

    name = "lightgbm"

    def __init__(self, quantiles: list[float], params: dict[str, Any] | None = None) -> None:
        self.quantiles = quantiles
        self.params = {
            "n_estimators": 300,
            "learning_rate": 0.05,
            "num_leaves": 63,
            "min_child_samples": 40,
            "random_state": 42,
            "verbosity": -1,
            **(params or {}),
        }
        self._models: dict[str, Any] = {}
        self._features: list[str] = []

    def fit(self, frame: pd.DataFrame) -> None:
        from lightgbm import LGBMRegressor  # lazy heavy import

        self._features = feature_columns(frame)
        x = frame[self._features]
        y = frame["value"]
        for q in self.quantiles:
            model = LGBMRegressor(objective="quantile", alpha=q, **self.params)
            model.fit(x, y)
            self._models[quantile_label(q)] = model

    def predict_day(self, frame_future: pd.DataFrame) -> dict[str, list[float]]:
        x = frame_future[self._features]
        preds = {lab: np.asarray(m.predict(x), dtype=float) for lab, m in self._models.items()}
        return _monotone(self.quantiles, preds)


def make_model(target: ForecastTarget, cfg: dict[str, Any]) -> QuantileForecaster:
    """Model per configs/forecasting.yaml; degrades to SeasonalNaive if deps missing."""
    quantiles = [float(q) for q in cfg.get("quantiles", [0.1, 0.5, 0.9])]
    choice = cfg.get("targets", {}).get(target.value, {}).get("model", "lightgbm")
    if choice == "lightgbm":
        try:
            import lightgbm  # noqa: F401  (lazy availability probe)

            return LightGBMQuantile(quantiles)
        except ImportError:
            log.warning("lightgbm unavailable; degrading to seasonal_naive", target=target.value)
            return SeasonalNaive(quantiles)
    if choice == "seasonal_naive":
        return SeasonalNaive(quantiles)
    raise ValueError(f"unknown model {choice!r} for target {target.value} (A11: keep CPU-sized)")


def future_frame_for_day(
    history: pd.DataFrame,
    weather: pd.DataFrame | None,
    target_cfg: dict[str, Any],
    day: Any,
) -> pd.DataFrame:
    """Append 96 NaN rows for `day`, rebuild features, return just that day's rows."""
    from app.forecasting.features import build_feature_frame

    future_idx = pd.DatetimeIndex([tb.block_start(day, b) for b in range(1, tb.BLOCKS_PER_DAY + 1)])
    extended = pd.concat([history, pd.DataFrame({"value": np.nan}, index=future_idx)])
    extended = extended[~extended.index.duplicated(keep="first")].sort_index()
    frame = build_feature_frame(extended, weather, target_cfg)
    return frame.loc[frame.index.isin(future_idx)]
