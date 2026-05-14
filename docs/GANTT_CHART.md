# PROJECT GANTT CHART
## AI-Assisted Technical Analysis and Signal Validation System for NEPSE Using Machine Learning

### Timeline: February 2026 – May 2026 (Midterm) → June 2026 (Final Submission)

```
TASK NAME                          Feb   Mar   Apr   May   Jun
================================================================

PHASE 1: PLANNING & SETUP
├─ Project Kickoff                [■■]
├─ Literature Review & Analysis   [■■■]
├─ Architecture Design            [■■■]
└─ Environment Setup              [■■■]

PHASE 2: DATA ENGINEERING
├─ Data Collection & Audit        [    ■■■]
├─ Data Cleaning (OHLCV)          [    ■■■]
├─ Corporate Action Adjustments   [       ■■■]
└─ Parquet Export                 [       ■■]

PHASE 3: FEATURE ENGINEERING
├─ RSI Implementation             [          ■■]
├─ MACD Implementation            [          ■■]
├─ Bollinger Bands Implementation [          ■■]
└─ 25+ Feature Engineering        [          ■■■]

PHASE 4: LABELING & SETUP
├─ Forward Return Calculation     [             ■■]
├─ Label Construction (1% threshold) [             ■■]
└─ Walk-Forward Fold Configuration  [             ■■]

PHASE 5: MODEL DEVELOPMENT
├─ XGBoost Hyperparameter Tuning  [                ■■]
├─ Model Training (7 Folds)       [                ■■■]
├─ Feature Importance Analysis    [                ■■]
└─ Model Serialization & Artifacts [                ■]

PHASE 6: BACKTESTING & EVALUATION
├─ Transaction Cost Integration   [                   ■■]
├─ Strategy Simulation            [                   ■■]
├─ Risk Metrics Calculation       [                   ■■]
├─ Performance Visualization      [                   ■■]
└─ Results Documentation          [                   ■]

PHASE 7: API & DASHBOARD
├─ FastAPI Backend Development    [                   ■■]
├─ React Dashboard Frontend       [                   ■■]
├─ Endpoint Testing               [                   ■■]
└─ Docker Containerization        [                   ■]

PHASE 8: REPORTING & SUBMISSION (MIDTERM)
├─ Midterm Report Writing         [                      ■■■]
├─ Appendices (Code, Visualizations) [                      ■■■]
├─ Internal Review & Revision     [                         ■]
└─ MIDTERM SUBMISSION             [                         ■]

PHASE 9: FINAL POLISH (Final Submission)
├─ Performance Optimization       [                            ■]
├─ Final Documentation            [                            ■■]
├─ Viva Preparation               [                            ■■]
├─ Live Demo Walkthrough          [                            ■]
└─ FINAL SUBMISSION + VIVA        [                            ■]

================================================================

LEGEND:
■ = Completed (as of May 13, 2026)
□ = In Progress
░ = Planned

KEY MILESTONES:
✓ May 13, 2026: MIDTERM STATUS (Phases 1-8 Complete)
  - All core analysis, design, implementation complete
  - Backtesting & evaluation complete
  - API & dashboard functional
  - Report ready for submission

→ May 27, 2026: Final Report Submission Deadline
→ June 3-10, 2026: Final Defense & Viva

CRITICAL PATH:
Shortest dependency chain from start to final delivery.
Most phases can execute in parallel except:
- Backtesting requires training completion
- API requires feature pipeline completion
- Report requires all experimental results
```

### Effort Allocation (Person-Months)

| Phase | Sudeep | Sajan | Pratiksha | Total |
|-------|--------|-------|-----------|-------|
| Planning & Setup | 0.3 | 0.3 | 0.3 | 0.9 |
| Data Engineering | 0.8 | 0.8 | 0.8 | 2.4 |
| Feature Engineering | 0.8 | 0.8 | 0.8 | 2.4 |
| Labeling & Setup | 0.4 | 0.4 | 0.4 | 1.2 |
| Model Development | 1.0 | 1.0 | 1.0 | 3.0 |
| Backtesting | 0.8 | 0.8 | 0.8 | 2.4 |
| API & Dashboard | 1.0 | 1.0 | 1.0 | 3.0 |
| Reporting (Midterm) | 0.5 | 0.5 | 0.5 | 1.5 |
| **TOTAL (Midterm)** | **5.6** | **5.6** | **5.6** | **16.8 PM** |
| Reporting (Final) | 0.3 | 0.3 | 0.3 | 0.9 |
| **TOTAL (Final)** | **5.9** | **5.9** | **5.9** | **17.7 PM** |

### Status Summary (May 13, 2026 - Midterm Checkpoint)

**Completed:**
- ✓ Data collection, cleaning, and feature engineering (100%)
- ✓ Model training with walk-forward validation (100%)
- ✓ Backtesting and performance evaluation (100%)
- ✓ API & dashboard prototype (95%)
- ✓ Midterm report (100%)

**In Progress:**
- API optimization and stress testing
- Dashboard UX refinement

**Remaining (Final Phase):**
- Production deployment (Docker, cloud hosting)
- Final documentation
- Viva preparation and demo

