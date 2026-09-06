# How 4 Raw Columns Became 13 Engineered Features

## The Transformation

### START: Raw Data (4 Columns)
```
raw_combined_400days.csv
├─ ts (timestamp)
├─ demand_mw           ◄─ We extract THIS
├─ price_inr_mwh       (dropped for demand model)
└─ inflow_mwh          (dropped for demand model)
```

### MIDDLE: Demand Only (1 Column)
```
Just the demand values:
└─ value = demand_mw
```

### END: Engineered Features (13 Columns)
```
engineered_features_demand_400days.csv
├─ value               (the original 1)
├─ lag_1d              (feature 1 of 13)
├─ lag_2d              (feature 2 of 13)
├─ lag_7d              (feature 3 of 13)
├─ block_sin           (feature 4 of 13)
├─ block_cos           (feature 5 of 13)
├─ dow                 (feature 6 of 13)
├─ is_weekend          (feature 7 of 13)
├─ is_holiday          (feature 8 of 13)
├─ month_sin           (feature 9 of 13)
├─ month_cos           (feature 10 of 13)
├─ temperature_2m      (feature 11 of 13)
├─ precipitation       (feature 12 of 13)
└─ cloud_cover         (feature 13 of 13)
```

---

## Where Each Feature Comes From

### Category 1: AUTOREGRESSIVE (3 features)
**Source:** Demand history

| Feature | What It Is | How It's Made |
|---------|-----------|---------------|
| **lag_1d** | Demand from 24 hours ago | Shift demand by 96 blocks (1 day = 96 × 15-min blocks) |
| **lag_2d** | Demand from 48 hours ago | Shift demand by 192 blocks (2 days = 192 blocks) |
| **lag_7d** | Demand from 7 days ago | Shift demand by 672 blocks (7 days = 672 blocks) |

**Example:**
```
If today's demand at 10:00 = 3000 MW
Then:
  lag_1d at 10:00 = demand yesterday at 10:00
  lag_2d at 10:00 = demand 2 days ago at 10:00
  lag_7d at 10:00 = demand last week at 10:00
```

---

### Category 2: TEMPORAL (2 features)
**Source:** Timestamp (hour:minute)

| Feature | What It Is | How It's Made |
|---------|-----------|---------------|
| **block_sin** | Sine wave of time-of-day | sin(2π × block / 96) where block = 1-96 |
| **block_cos** | Cosine wave of time-of-day | cos(2π × block / 96) where block = 1-96 |

**Why sine/cosine?** Circular encoding - treats midnight (block 1) same as midnight 2 days later
- At 00:00: sin=0.07, cos=0.99
- At 06:00: sin=0.71, cos=0.71
- At 12:00: sin=-0.07, cos=-0.99
- At 23:45: sin≈0, cos=1.00 (wraps back to midnight)

---

### Category 3: CALENDAR (3 features)
**Source:** Timestamp date + Kerala holiday calendar

| Feature | What It Is | How It's Made |
|---------|-----------|---------------|
| **dow** | Day of week | 0=Monday, 1=Tuesday, ..., 6=Sunday |
| **is_weekend** | Saturday/Sunday flag | 1 if Sat/Sun, else 0 |
| **is_holiday** | Holiday flag | 1 if Onam/Vishu/Independence Day/etc, else 0 |

**Example:**
```
If timestamp = Tuesday, June 3, 2025 (not a holiday)
Then:
  dow = 1 (Tuesday)
  is_weekend = 0 (not Sat/Sun)
  is_holiday = 0 (regular day)
```

---

### Category 4: SEASONAL (2 features)
**Source:** Timestamp (month)

| Feature | What It Is | How It's Made |
|---------|-----------|---------------|
| **month_sin** | Sine wave of month | sin(2π × month / 12) where month = 1-12 |
| **month_cos** | Cosine wave of month | cos(2π × month / 12) where month = 1-12 |

**Why?** Summer demand ≠ monsoon demand ≠ winter demand (circular, Jan=Dec)
- January: sin=0, cos=-1
- April: sin=1, cos=0 (summer peak)
- July: sin=0, cos=-1 (monsoon)
- October: sin=-1, cos=0

---

### Category 5: WEATHER (3 features)
**Source:** OpenMeteo API (or synthetic = 0)

| Feature | What It Is | Unit | Notes |
|---------|-----------|------|-------|
| **temperature_2m** | Air temperature | °C | Higher temp → Higher AC load |
| **precipitation** | Rainfall | mm | Rain → Less solar → Higher grid demand |
| **cloud_cover** | Cloud percentage | % | More clouds → Less solar generation |

**For synthetic data:** All are 0 (no weather variation in synthetic generator)
**For real data:** Would fetch from OpenMeteo API

---

## The Math Behind It

```
Raw data (4 columns) for 400 days:
  38,400 rows × 4 columns = 153,600 data points

Extract demand only:
  38,400 rows × 1 column = 38,400 data points

Engineer features:
  For each row, CALCULATE from:
    1. History (lags) → 3 new columns
    2. Timestamp → 6 new columns (sin/cos temporal, calendar, seasonal)
    3. Holiday calendar → 1 new column
    4. Weather API → 3 new columns
    ────────────────────────────
    Total: 13 new features

  Result: 38,400 rows × (1 original + 13 engineered) = 38,400 × 14

After dropping NaN (lag needs history):
  37,728 rows × 14 columns (7 days of history lost)
```

---

## Why Not Use Price & Inflow Features?

Because they're **separate models**:

| Model | Input | Output | Lags | Weather | Total Features |
|-------|-------|--------|------|---------|-----------------|
| **Demand** | Raw demand | Predict demand | 1d, 2d, 7d | temperature_2m, cloud_cover, precipitation | 13 |
| **Price** | Raw price | Predict price | 1d, 2d, 7d | *(none)* | 10 |
| **Inflow** | Raw inflow | Predict inflow | 1d, 7d, 14d | precipitation | 11 |

(Per `configs/forecasting.yaml` — each target has its own `lags_days` and
`weather_features`, so the feature count genuinely differs per model; it isn't the same
13 features reused three times.)

Each series has its own patterns:
- **Demand:** Follows daily/weekly cycles, temperature-dependent
- **Price:** Follows demand (scarcity driven), seasonal
- **Inflow:** Follows monsoon/hydro patterns, highly uncertain

---

## For Your PPT Slide

### Show This Pipeline:

```
RAW INPUT (4 columns)
  demand_mw, price_inr_mwh, inflow_mwh
         │
         ├─ Select DEMAND only
         │
         ├─ Extract TIME patterns
         │  (block_sin/cos, month_sin/cos, dow)
         │
         ├─ Extract DEMAND patterns
         │  (lag_1d, lag_2d, lag_7d)
         │
         ├─ Extract CALENDAR patterns
         │  (is_weekend, is_holiday)
         │
         └─ Add WEATHER data
            (temperature_2m, precipitation, cloud_cover)
                   │
                   ▼
ENGINEERED OUTPUT (14 columns)
  1 original + 13 features for MODEL TRAINING
```

---

## Key Numbers to Remember

- **Raw data:** 4 columns (demand, price, inflow, timestamp)
- **Engineered:** 14 columns (1 target + 13 features)
- **Feature categories:** 5 (autoregressive, temporal, calendar, seasonal, weather)
- **Rows after engineering:** 37,728 (7 days of history dropped for lags)
- **Correlation with demand:** lag_1d (0.9464), lag_2d (0.8920), lag_7d (0.9393)

