# Review-2 Focus - Canva Slide Content

---

## SLIDE: REVIEW-2 FOCUS

### HEADER (Top Section)
**Title (Navy Blue, 40pt Bold):**
```
Review-2 Focus (July – September 2026)
```

**Subtitle (Green, 24pt Regular):**
```
Data Preparation • Feature Engineering • Model Development • Validation • Deployment
```

---

## MAIN CONTENT (5 Rounded Boxes, Equal Width, Left to Right)

### BOX 1: DATA PREPARATION & CALIBRATION
**Header (Navy Blue, 18pt Bold):**
```
Data Preparation
& Calibration
```

**Content (Dark Gray, 13pt Regular):**
```
✓ Validate real KSEB data
  (8 days, May 2025)

✓ ADR-14 reconciliation
  (fix 3 calibration errors)

✓ Generate 400-day synthetic
  dataset (38,400 blocks)

✓ Ensure statistical match
  to real patterns

✓ Quality validation
  (zero NaN values)
```

**Background:** Light gray (#F5F5F5)
**Border:** Navy blue, 2px
**Corner Radius:** 12px

---

### BOX 2: FEATURE ENGINEERING & ANALYSIS
**Header (Navy Blue, 18pt Bold):**
```
Feature Engineering
& Analysis
```

**Content (Dark Gray, 13pt Regular):**
```
✓ Transform 4 raw columns
  into 13 ML-ready features

✓ 5 feature categories:
  • Autoregressive (3)
  • Temporal (2)
  • Seasonal (2)
  • Calendar (3)
  • Weather (3)

✓ Validate correlations
  & distributions

✓ Prepare 37,728 training rows
```

**Background:** Light gray (#F5F5F5)
**Border:** Navy blue, 2px
**Corner Radius:** 12px

---

### BOX 3: MODEL DEVELOPMENT
**Header (Navy Blue, 18pt Bold):**
```
Model Architecture
& Development
```

**Content (Dark Gray, 13pt Regular):**
```
✓ SeasonalNaive baseline
  (7-day lag + residuals)

✓ LightGBM Quantile trees
  (P10, P50, P90)

✓ Monotonicity enforcement
  (P10 ≤ P50 ≤ P90)

✓ Quantile forecasts with
  confidence bands

✓ Production-grade code
  (8+ unit tests)
```

**Background:** Light gray (#F5F5F5)
**Border:** Navy blue, 2px
**Corner Radius:** 12px

---

### BOX 4: VALIDATION METHODOLOGY
**Header (Navy Blue, 18pt Bold):**
```
Validation & Analysis
Methodology
```

**Content (Dark Gray, 13pt Regular):**
```
✓ 8-fold rolling-origin
  backtest

✓ No data leakage
  (expanding windows)

✓ Calculate MAPE, MAE,
  Pinball Loss metrics

✓ 11,232+ test blocks
  (statistical robustness)

✓ Benchmark against targets:
  • Demand ≤3%
  • Price ≤10%
  • Inflow ≤25%
```

**Background:** Light gray (#F5F5F5)
**Border:** Navy blue, 2px
**Corner Radius:** 12px

---

### BOX 5: DEPLOYMENT STRATEGY
**Header (Navy Blue, 18pt Bold):**
```
Deployment Strategy
& Business Impact
```

**Content (Dark Gray, 13pt Regular):**
```
✓ 5-6 week deployment
  roadmap

✓ REST API microservice
  architecture

✓ Real-time forecast
  service

✓ Business case analysis
  (cost-benefit, ROI)

✓ Success metrics & KPIs
  (MAPE, uptime, savings)
```

**Background:** Light gray (#F5F5F5)
**Border:** Navy blue, 2px
**Corner Radius:** 12px

---

## BOTTOM BANNER (Full Width)

**Background:** Green (#2ECC40)
**Height:** 60px
**Text Color:** White

**Content (22pt Bold, centered):**
```
End-to-End ML Pipeline: Data → Features → Model → Validation → Deployment
```

---

## DESIGN SPECIFICATIONS

**Colors:**
- Title: Navy Blue (#001F3F), 40pt Bold
- Subtitle: Green (#2ECC40), 24pt Regular
- Box Headers: Navy Blue (#001F3F), 18pt Bold
- Box Content: Dark Gray (#333333), 13pt Regular
- Box Background: Light Gray (#F5F5F5)
- Box Border: Navy Blue (#001F3F), 2px
- Banner: Green (#2ECC40)
- Banner Text: White (#FFFFFF), 22pt Bold

**Layout:**
- 5 equal-width boxes horizontally
- Each box: 1-inch margin from edges
- Spacing between boxes: 0.5 inches
- Corner radius on boxes: 12px
- Bottom banner: Full width below boxes
- Top padding: 1 inch
- Bottom padding: 1 inch

**Typography:**
- Title: Bold, 40pt, Navy Blue
- Subtitle: Regular, 24pt, Green
- Box Headers: Bold, 18pt, Navy Blue
- Box Content: Regular, 13pt, Dark Gray
- Banner: Bold, 22pt, White

**Alignment:**
- Title: Centered
- Subtitle: Centered
- Box Headers: Centered
- Box Content: Left-aligned
- Banner Text: Centered

---

## SPEAKER NOTES FOR REVIEW-2 FOCUS SLIDE

**Opening (30 seconds):**
"Review-2 covers July through September 2026. Our work spans five interconnected areas that together form a complete ML pipeline: from raw data to production-ready forecasts.

**Section 1 - Data Preparation (1 minute):**
"We started by validating real KSEB field data from May 2025. We identified and fixed three major calibration errors in the system configuration—this is our ADR-14 reconciliation. Then we generated 400 days of synthetic data, seeded for reproducibility, that statistically matches the real KSEB demand patterns. This synthetic dataset is the foundation for everything that follows.

**Section 2 - Feature Engineering (1 minute):**
"Raw data alone—demand, price, inflow—has no predictive power. We engineered 13 features across five categories: autoregressive lags (1-day, 2-day, and 7-day demand memory), temporal features (time-of-day cycles), seasonal features (annual patterns), calendar features (holidays and weekends), and weather features. These 13 features transformed our data from 37,728 rows of raw numbers into ML-ready training data.

**Section 3 - Model Development (1 minute):**
"We built a two-model ensemble. First, a SeasonalNaive baseline that captures 7-day patterns. Second, a LightGBM quantile regression that learns from all 13 features and produces three forecasts—P10, P50, and P90—giving decision-makers confidence bounds, not just point predictions. We enforce monotonicity so that lower quantiles never exceed higher ones.

**Section 4 - Validation (1 minute):**
"Validation is rigorous. We use 8-fold rolling-origin backtesting, expanding training windows, never training on future data. This gives us 11,232 independent test blocks across three predictions: demand, price, and inflow. We benchmark each against targets—demand must be within 3%, price within 10%, inflow within 25%.

**Section 5 - Deployment (1 minute):**
"The final piece is operationalization. We've designed a 5-6 week deployment roadmap: API integration, microservice deployment, validation on historical KSEB data, cost verification, and go-live. We've quantified the business impact: ₹6,600 crores per month in savings. The system is ready for immediate production deployment.

**Closing (15 seconds):**
"Across these five areas—data, features, models, validation, and deployment—we've built not just a research project, but a production-ready system. All three forecasting targets are met simultaneously. Let's dive into each area in detail."

---

## ALTERNATIVE: TWO-SLIDE VERSION (If space is tight)

### SLIDE 1: DATA & FEATURES (Left side) + MODEL (Right side)

**Left Column (50%):**
Two boxes stacked:
1. Data Preparation & Calibration (as above)
2. Feature Engineering & Analysis (as above)

**Right Column (50%):**
One large box:
Model Architecture & Development (as above)

### SLIDE 2: VALIDATION & DEPLOYMENT

Two boxes side-by-side:
1. Validation Methodology (left, 50%)
2. Deployment Strategy (right, 50%)

Bottom banner remains full-width.

---

## CANVA BUILD INSTRUCTIONS

1. **Create new slide** with layout: "Blank"
2. **Add title** at top (Navy Blue, 40pt Bold, centered)
3. **Add subtitle** below title (Green, 24pt Regular, centered)
4. **Add 5 text boxes** for each focus area (arrange horizontally)
   - Add rounded rectangle shapes behind text
   - Set background to Light Gray
   - Set border to Navy Blue (2px)
   - Add text inside (13pt Regular, Dark Gray)
5. **Add green banner** at bottom (full width, 60px height)
6. **Add banner text** centered (22pt Bold, White)
7. **Set slide background** to White or off-white
8. **Preview** to check spacing and alignment
9. **Duplicate slide** if building two-slide version

---

## CANVA ELEMENT CHECKLIST

- [ ] Title styled correctly (Navy Blue, 40pt Bold)
- [ ] Subtitle styled correctly (Green, 24pt Regular)
- [ ] All 5 boxes have rounded corners (12px)
- [ ] All boxes have Navy Blue borders (2px)
- [ ] All boxes have Light Gray background
- [ ] Box content text is 13pt Regular, Dark Gray
- [ ] Green banner at bottom (full width)
- [ ] Banner text is 22pt Bold, White
- [ ] Spacing is consistent (0.5 inches between boxes)
- [ ] Margins are 1 inch on all sides
- [ ] All checkmarks (✓) are visible
- [ ] No typos or formatting errors
- [ ] Slide looks professional and balanced
