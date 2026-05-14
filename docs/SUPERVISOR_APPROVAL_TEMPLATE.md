# SUPERVISOR RECOMMENDATION & APPROVAL LETTER

## Template for Supervisor Signature

---

**BIRENDRA MULTIPLE CAMPUS**  
Department of Computer Science (CSIT)  
Bharatpur, Chitwan  

---

**TO:** Head/Program Coordinator, Department of CSIT  
**FROM:** [Supervisor Name], Project Supervisor  
**DATE:** [Date]  
**RE:** Midterm Progress Report Approval — AI-Assisted Technical Analysis and Signal Validation System for NEPSE

---

### SUPERVISOR'S RECOMMENDATION

I have reviewed the midterm progress report submitted by:

- **Sudeep Sigdel** (Roll: 79011781)
- **Sajan Bhandari** (Roll: 79011770)
- **Pratiksha Acharya** (Roll: 79011760)

for their BSc. CSIT Final Year Project (CSC 412).

#### **Assessment Summary:**

**Project Title:** *AI-Assisted Technical Analysis and Signal Validation System for NEPSE Using Machine Learning*

**Progress Status:** ✓ **ON TRACK** — All core analysis, design, and implementation phases completed successfully.

#### **Key Achievements (Midterm):**

1. **Data Pipeline:** Successfully aggregated and cleaned 80+ securities from NEPSE spanning 2018–2025 (~150,000 trading days). Implemented robust data validation, deduplication, and corporate action handling.

2. **Technical Indicators:** Implemented RSI (14), MACD (12/26/9), and Bollinger Bands (20, 2σ) per standard definitions. Indicator correctness verified against reference implementations.

3. **Feature Engineering:** Engineered 25+ features capturing momentum, volatility, volume, and contextual market states. Quality checks confirm ≥98% non-NaN values across the feature set.

4. **Machine Learning Model:** Trained XGBoost classifiers using rigorous walk-forward validation across 7 sequential folds (2018–2025). Mean out-of-sample AUC = 0.5346, demonstrating a modest but consistent edge suitable for financial prediction tasks.

5. **Backtesting with Transaction Costs:** Implemented comprehensive backtesting incorporating realistic NEPSE transaction costs (1% round-trip). ML-validated strategy achieved:
   - 22,460 trades over 7-year validation period
   - 42.18% win rate
   - 1.076 profit factor (wins exceed losses by 7.6%)
   - +6,421% cumulative net return (~26% annualized)
   - Sharpe ratio of 0.126 (positive risk-adjusted return)
   - Significantly outperformed both indicator-only and buy-and-hold baselines

6. **Production Systems:** Developed a REST API (FastAPI) and interactive React dashboard enabling real-time signal generation, indicator visualization, and user-friendly confidence scoring.

7. **Documentation:** Comprehensive report with IEEE-formatted references, algorithm specifications, code examples, and detailed methodology justifications.

#### **Technical Quality:**

- **Methodology:** Adheres to best practices in financial ML: time-ordered validation, strict temporal separation (20-day embargo), transaction cost inclusion, and out-of-sample evaluation.
- **Code Quality:** Modular architecture (8 sequential Python scripts), clear separation of concerns, proper error handling, and version control.
- **Rigor:** No data leakage, no look-ahead bias, realistic cost assumptions, and reproducible results.
- **Results:** All backtests, metrics, and visualizations are verifiable from provided outputs.

#### **Team Performance:**

The three team members have demonstrated:
- **Equal Contribution:** Each member actively participated in all phases (data, modeling, implementation, testing, documentation).
- **Technical Competence:** Strong understanding of ML fundamentals, financial data analysis, software engineering practices.
- **Professionalism:** Maintained clear documentation, followed deadlines, incorporated feedback constructively.

#### **Remaining Work (Final Submission):**

1. API optimization and stress testing (estimated 1 week)
2. Final documentation and viva preparation (estimated 1 week)
3. Live demo and presentation refinement (estimated 3 days)

These remaining tasks are within scope and timeline for final submission by [Final Submission Date].

---

### **RECOMMENDATION**

**I hereby recommend the acceptance of this midterm progress report and approval to proceed to the final submission phase.**

The project demonstrates:
- ✓ Sufficient technical depth and complexity appropriate for a final-year CS project
- ✓ Clear advancement from proposal to working prototype
- ✓ Rigorous application of learned concepts in algorithms, ML, data engineering, and software development
- ✓ Original contribution to NEPSE trading signal validation

**Expected Outcome:** The final submission will include production-ready API, comprehensive documentation, viva presentation, and live demonstration.

---

### **SUPERVISOR SIGN-OFF**

**Supervisor Name:** Devendra Chapagain  
**Title:** Project Supervisor, BSc. CSIT  
**Signature:** _____________________________  
**Date:** _____________________________  
**Contact:** [Email/Phone]

---

### **INTERNAL EXAMINER REVIEW**

**Internal Examiner Name:** _____________________________  
**Signature:** _____________________________  
**Date:** _____________________________  
**Comments:** 

---

### **HEAD/PROGRAM COORDINATOR APPROVAL**

**Head/Coordinator Name:** _____________________________  
**Signature:** _____________________________  
**Date:** _____________________________  
**Office Stamp:**

---

*This letter certifies that the students have completed satisfactory work for the midterm evaluation of CSC 412 Project Work and are eligible to continue toward final submission.*

