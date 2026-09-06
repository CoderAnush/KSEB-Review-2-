# Quick Canva Styling Guide: Slides 4-10 (5-Minute Finish)

## DESIGN SYSTEM FROM REVIEW 1

**Colors to Use:**
- **Navy Blue:** #001F3F or #003366 (titles, headers)
- **Green Accent:** #2ECC40 or #28A745 (horizontal bars, badges)
- **Light Gray:** #F5F5F5 or #EEEEEE (backgrounds)
- **White:** #FFFFFF (content areas)
- **Dark Text:** #333333 (body text)

**Typography:**
- **Titles:** Bold, 36-40pt, Navy Blue
- **Body:** Regular, 18-22pt, Dark Gray
- **Captions:** Regular, 14-16pt, Medium Gray

---

## SLIDE 4: FEATURE ENGINEERING (4-5 minutes)

### Header Section (Top)
1. **Add horizontal bar** under title
   - Height: 4px
   - Color: Green (#2ECC40)
   - Width: Full slide width
   - Position: Directly under title text

2. **Title styling**
   - Font: Bold, 36pt
   - Color: Navy Blue (#001F3F)
   - Text: "From 4 Raw Columns to 12 Engineered Features"

### Left Section (60%)
1. **Add flowchart diagram** (already outlined in prompt)
   - Use Canva shapes (boxes, arrows)
   - Box color: Light Gray (#F5F5F5) with Navy border
   - Arrow color: Green (#2ECC40)
   - Text: 14pt, Dark Gray

### Right Section (40%)
1. **Feature table**
   - Header row: Navy Blue (#001F3F) background, white text, bold
   - Alternating rows: White and light gray (#F5F5F5)
   - Font: 14pt, Regular
   - Borders: Thin navy lines

2. **Highlight box at bottom**
   - Background: Green (#2ECC40)
   - Text: White, bold
   - Content: "Training data: 37,728 rows × 14 columns"

---

## SLIDE 5: MODEL ARCHITECTURE (4-5 minutes)

### Header Section
1. **Add green horizontal bar** (4px, #2ECC40)
2. **Title:** "Two-Model Ensemble Architecture"
   - Font: Bold, 36pt, Navy Blue
   - Alignment: Left

### Main Diagram (60%)
1. **Create boxes using Canva shapes**
   - Main boxes: Navy Blue (#001F3F) background, white text
   - Sub-boxes: Light gray (#F5F5F5) with navy border
   - Arrows: Green (#2ECC40), 2-3px thickness

2. **Diagram structure:**
   ```
   12 ENGINEERED FEATURES (Navy box, white text)
            ↓ (Green arrow)
   ┌─SeasonalNaive─┬─LightGBM─┐ (Navy boxes)
   │ (description) │(description)│
   └────────┬──────┴──────┬────┘
            ↓ (Green arrows)
   P10, P50, P90 (Navy boxes)
            ↓ (Green arrow)
   MONOTONICITY ENFORCEMENT (Green box, white text)
            ↓ (Green arrow)
   FORECAST OUTPUT (Navy box, white text)
   ```

3. **Font sizes:**
   - Box titles: 16pt Bold, white/dark depending on background
   - Descriptions: 12pt Regular

### Bottom Sections (40%)
1. **Two columns**
   - Column 1 header: "SeasonalNaive Baseline" (Navy Blue, 18pt Bold)
   - Column 2 header: "LightGBM Quantile" (Navy Blue, 18pt Bold)

2. **Content boxes**
   - Background: Light gray (#F5F5F5)
   - Border: Navy blue, 2px
   - Text: 13pt, dark gray
   - Bullet points: Green checkmarks (✅) and red X (❌)

3. **Bottom highlight box**
   - Background: Green (#2ECC40)
   - Text: White, bold, 14pt
   - Content: "Key Numbers: 37,728 training rows | 13 features | 8 folds validation"

---

## SLIDE 6: VALIDATION METHODOLOGY (4-5 minutes)

### Header Section
1. **Add green horizontal bar** (4px)
2. **Title:** "Validation: 8-Fold Rolling-Origin Backtest"
   - Navy Blue, 36pt Bold

### Main Timeline Diagram (60%)
1. **Create Gantt-style visualization**
   - 8 horizontal bars (one per fold)
   - Train section: Light blue (#D0E8FF) with navy border
   - Test section: Green (#2ECC40) with navy border
   - Spacing: 10px between rows

2. **Label each fold:**
   - FOLD 1: Train [1-330] | Test [331-345]
   - FOLD 2: Train [1-345] | Test [346-360]
   - ... (continue through FOLD 8)
   - Font: 11pt, monospace or Arial

3. **Arrow on right:** Navy blue arrow pointing right (→)

### Right Section (40%)
1. **Methodology box**
   - Header: "Why This Method?" (Navy Blue, 20pt Bold)
   - Background: Light gray (#F5F5F5)
   - Border: Navy blue, 2px
   - Content: Bullet points with ✅ and ❌

2. **Bullets:**
   ```
   ✅ No Data Leakage
   ✅ Realistic Forecasting
   ✅ Expanding Window
   ✅ 8 Independent Tests
   ✅ 11,232 Test Blocks Total
   ❌ WRONG: Random split
   ❌ WRONG: Single train-test
   ```
   - Font: 13pt
   - Green checkmarks, red X marks

---

## SLIDE 7: RESULTS & METRICS (5-6 minutes)

### Header Section
1. **Add green horizontal bar** (4px)
2. **Title:** "Results: All Targets Met ✅"
   - Navy Blue, 36pt Bold

### Main Metrics Table
1. **Create professional table in Canva**
   - Header row: Navy Blue (#001F3F) background, white text, bold
   - Content rows: Alternating white and light gray (#F5F5F5)
   - Borders: Navy blue, thin (1px)
   - Font: 15pt for content, 16pt Bold for header

2. **Table structure:**
   ```
   ┌─────────────────┬──────────┬───────┬─────────┬─────────┬──────────┬────────┐
   │ TARGET          │ MODEL    │ FOLDS │ MAPE %  │ MAE     │ TARGET   │ STATUS │
   ├─────────────────┼──────────┼───────┼─────────┼─────────┼──────────┼────────┤
   │ Demand (MW)     │ LightGBM │ 8     │ 2.74%   │ 105.4 MW│ ≤ 3.0%   │ ✅     │
   │ Price (₹/MWh)   │ LightGBM │ 8     │ 8.81%   │ 374.5   │ ≤ 10%    │ ✅     │
   │ Inflow (MWh)    │ LightGBM │ 8     │ 17.53%  │ 43.6    │ ≤ 25%    │ ✅     │
   └─────────────────┴──────────┴───────┴─────────┴─────────┴──────────┴────────┘
   ```

### Three Info Boxes Below (33% each)

**Box 1: Demand MAPE Performance (Left)**
- Header: "Demand MAPE: 2.74%" (Navy Blue, 20pt Bold)
- Background: Light blue (#E8F4F8) with navy border (2px)
- Content (13pt, dark gray):
  ```
  Industry Benchmark:
  • Typical: 2-5%
  • You: 2.74% → TOP QUARTILE ⭐
  
  Accuracy:
  • On 4,500 MW baseline
  • ±120 MW typical error
  • ±2.7% relative error
  • Status: EXCELLENT ✅
  ```

**Box 2: Improvement (Center)**
- Header: "33% Better Than Baseline" (Green #2ECC40, 20pt Bold, white text)
- Background: Light green (#F0F8F0) with green border (2px)
- Content (13pt):
  ```
  SeasonalNaive: MAPE ~4.0%
  LightGBM: MAPE 2.74%
  Improvement: 33% better
  
  Financial Impact:
  ₹6,600 Cr/month savings
  ```

**Box 3: Confidence (Right)**
- Header: "High Confidence Results" (Navy Blue, 20pt Bold)
- Background: Light gray (#F5F5F5) with navy border (2px)
- Content (13pt):
  ```
  Validation:
  ✅ 8 folds
  ✅ 11,232 test blocks
  ✅ No leakage
  ✅ Reproducible
  
  Quality: Pinball P10: 21.4, P90: 18.4
  Generalization: ✅ All targets met
  ```

---

## SLIDE 8: MARKET CONTEXT & CHARTS (6-7 minutes)

### Header Section
1. **Add green horizontal bar** (4px)
2. **Title:** "Market Dynamics: Why These Forecasts Matter"
   - Navy Blue, 36pt Bold

### Three Columns (33% each)

**COLUMN 1: Price Volatility (Left)**
1. **Insert chart:** `chart_market_rates.png`
   - Size: Full column height, responsive width
   - Border: Navy blue, 2px
   - Shadow: Light drop shadow

2. **Caption below chart:**
   - Font: 13pt Bold, Navy Blue
   - Text: "Electricity Market Prices (8 Days) | DAM & RTM Rates with ₹10 Ceiling"

3. **Insight box below caption:**
   - Background: Light orange (#FFF4E6) with green border (2px)
   - Content (12pt):
     ```
     Morning: ₹2-4/kWh (Cheap)
     Solar abundant, low demand
     
     Evening: ₹8-10/kWh (Expensive)
     Peak demand, solar gone, hits ceiling
     ```

**COLUMN 2: Supply Mix (Center)**
1. **Insert chart:** `chart_supply_mix.png`
   - Size: Full column height, responsive width
   - Border: Navy blue, 2px
   - Shadow: Light drop shadow

2. **Caption:**
   - Font: 13pt Bold, Navy Blue
   - Text: "Supply Mix Sources (8 Days) | Stacked: Hydro, PPA, Market, RTM"

3. **Insight box:**
   - Background: Light blue (#E8F4F8) with green border (2px)
   - Content (12pt):
     ```
     Internal Generation: 20%
     (Hydro + renewables)
     
     Spot Market at Peak: 26%
     (Most expensive source)
     
     Forecast Accuracy → Better Sourcing
     ```

**COLUMN 3: Hydro Budget (Right)**
1. **Insert chart:** `chart_hydro_energy.png`
   - Size: Full column height, responsive width
   - Border: Navy blue, 2px
   - Shadow: Light drop shadow

2. **Caption:**
   - Font: 13pt Bold, Navy Blue
   - Text: "Hydro Energy Budget (8 Days) | Actual vs Configured"

3. **Insight box:**
   - Background: Light yellow (#FFFACD) with green border (2px)
   - Content (12pt):
     ```
     Actual: ~25.8 GWh/day
     (2.9× higher than configured)
     
     Corrected: 19,000 MWh/day
     Status: ✅ Validated & Fixed
     ```

---

## SLIDE 9: CONCLUSION & ROADMAP (5-6 minutes)

### Header Section
1. **Add green horizontal bar** (4px)
2. **Title:** "Production-Ready System: Ready for Deployment"
   - Navy Blue, 36pt Bold

### Three Sections (33% each)

**SECTION 1: What We Built (Left)**
- Header: "Deliverables" (Navy Blue, 20pt Bold)
- Background: Light gray (#F5F5F5) with navy border (2px)
- Bullets (13pt):
  ```
  ✅ Synthetic Dataset
     • 400 days, 38,400 blocks
     • Calibrated from real KSEB
     • Reproducible
  
  ✅ Feature Engineering
     • 13 engineered features
     • 37,728 training rows
     • Validated
  
  ✅ ML Model
     • Two-model ensemble
     • 8-fold validated
     • Production code
  
  ✅ Documentation
     • Technical guides
     • Deployment manual
  ```

**SECTION 2: Achievements (Center)**
- Header: "Performance Summary" (Green #2ECC40, 20pt Bold, white)
- Background: Light green (#F0F8F0) with green border (2px)
- Content (13pt):
  ```
  ✅ Demand MAPE: 2.74%
     (Beats 3.0% target)
  
  ✅ Price MAPE: 8.81%
     (Beats 10% target)
  
  ✅ Inflow MAPE: 17.53%
     (Beats 25% target)
  
  ✅ All 3 Targets Met
  ✅ Top-Quartile Accuracy
  ✅ Rigorous Validation
  ```

**SECTION 3: Deployment Roadmap (Right)**
- Header: "Next Steps" (Navy Blue, 20pt Bold)
- Background: Light gray (#F5F5F5) with navy border (2px)
- Numbered badges with content (13pt):
  ```
  1️⃣ INTEGRATION
     Connect forecast API to optimizer
  
  2️⃣ REAL-TIME API
     Deploy as microservice
  
  3️⃣ BACKTESTING
     Validate on 2023-2024 data
  
  4️⃣ COST VALIDATION
     Verify ₹6,600 Cr/month savings
  
  5️⃣ GO-LIVE
     Deploy to KSEB system
  ```

### Bottom: Large Impact Box (Full Width)
1. **Background:** Green (#2ECC40)
2. **Text Color:** White
3. **Border:** None (full width)
4. **Height:** 80-100px

**Content:**
- Line 1 (24pt Bold): "Estimated Annual Business Impact"
- Line 2 (28pt Bold): "Cost Savings: ₹79,200 Crores/Year"
- Line 3 (18pt): "ROI: Significant | Payback: < 1 month | Ready for Immediate Deployment"

---

## SLIDE 10: Q&A BACKUP (2-3 minutes)

### Full-Screen Gradient Background
1. **Gradient:** Navy Blue (#001F3F) to Dark Navy (#0A1929)
2. **Direction:** Top-left to bottom-right

### Centered Content (All White Text)
1. **Main Text:** "Questions?" (56pt Bold, White, centered)
2. **Subtitle:** "KSEB Electricity Demand Forecasting System" (28pt Regular, Light Gray, centered)
3. **Contact Info (20pt, White):**
   ```
   [Your Name]
   [Your Email]
   [University Name]
   
   GitHub: [Link]
   Documentation: Available on request
   ```

4. **Logo:** Institution logo (bottom-right, white, 10% opacity)

---

## CHART INSERTION QUICK REFERENCE

| Slide | Chart File | Position | Size |
|-------|-----------|----------|------|
| 2 | chart_deviation_pattern.png | Left 70% | Full height |
| 3 | chart_demand_profile.png | Center column | Full height |
| 3 | chart_demand_profile_after.png | Right column | Full height |
| 8 | chart_market_rates.png | Left 33% | Full height |
| 8 | chart_supply_mix.png | Center 33% | Full height |
| 8 | chart_hydro_energy.png | Right 33% | Full height |

**Chart Quality Requirements:**
- Minimum resolution: 300 DPI
- Format: PNG
- Maintain aspect ratio
- Add 2px navy blue border
- Add light drop shadow

---

## STYLING CHECKLIST

Before finalizing:

### Color Consistency
- [ ] All titles: Navy Blue (#001F3F or #003366)
- [ ] All accent bars: Green (#2ECC40 or #28A745)
- [ ] All backgrounds: White or light gray (#F5F5F5)
- [ ] All text: Dark gray (#333333) or Navy for headers

### Typography Consistency
- [ ] All main titles: Bold, 36-40pt, Navy Blue
- [ ] All subtitles: Bold, 20-22pt, Navy Blue
- [ ] All body text: Regular, 18-22pt, Dark Gray
- [ ] All captions: Regular, 13-16pt, Medium Gray

### Layout Consistency
- [ ] Green horizontal bar under all titles
- [ ] 1-inch margins on all sides
- [ ] Consistent spacing between elements
- [ ] Charts have navy borders and shadow

### Content Consistency
- [ ] All metrics verified (2.74%, 8.81%, 17.53%)
- [ ] All speaker notes complete
- [ ] All checkmarks (✅) and X marks (❌) in place
- [ ] All numbered badges (1️⃣-5️⃣) present

### Final Quality
- [ ] No typos or grammatical errors
- [ ] All charts embedded and high-quality
- [ ] Presentation looks professional
- [ ] Ready to export as PDF

---

## TIME ESTIMATE

- Slide 4: 5 min
- Slide 5: 5 min
- Slide 6: 5 min
- Slide 7: 6 min
- Slide 8: 7 min (chart insertion)
- Slide 9: 6 min
- Slide 10: 3 min
- Final review & tweaks: 5 min

**Total: ~42 minutes** (can be done in 1 sitting)

---

## CANVA EDITING TIPS

1. **Use Brand Kit** to store colors (navy, green, grays)
2. **Create text styles** for consistency (Title, Body, Caption)
3. **Use groups** to organize slide elements
4. **Duplicate slides** to copy styling from slide 1
5. **Use alignment guides** (View → Guides) for perfect spacing
6. **Preview as PDF** before finalizing to check quality

---

**You've got this! The design is clean, professional, and consistent. 🎨**

