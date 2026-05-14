# MIDTERM REPORT SUBMISSION CHECKLIST

## Submission Requirements per Syllabus

### ✓ **Report Content Requirements**

**Front Matter:**
- ☑ Title Page (Birendra Multiple Campus header, project title, group members, supervisor, date)
- ☑ Acknowledgement (thanking supervisor, institution, open-source communities)
- ☑ Abstract (250-300 words summarizing key findings and midterm progress)
- ☑ Table of Contents (with page numbers)
- ☑ List of Abbreviations (if used)
- ☑ List of Figures (with page numbers)
- ☑ List of Tables (with page numbers)

**Main Report Chapters:**
- ☑ **Chapter 1: Introduction** (1.1 Intro, 1.2 Problem, 1.3 Objectives, 1.4 Scope/Limitations, 1.5 Methodology, 1.6 Organization)
- ☑ **Chapter 2: Background Study and Literature Review** (2.1 Background, 2.2 Literature Review)
- ☑ **Chapter 3: System Analysis** (3.1 Requirements, 3.1.2 Feasibility, 3.1.3 Analysis Models)
- ☑ **Chapter 4: System Design** (4.1 Architecture, 4.2 Algorithm Details)
- ☑ **Chapter 5: Implementation and Testing** (5.1 Implementation, 5.1.1 Tools, 5.1.2 Module Details, 5.2 Testing, 5.3 Results)
- ☑ **Chapter 6: Conclusion and Future Recommendations** (6.1 Conclusion, 6.2 Recommendations)

**Back Matter:**
- ☑ References (IEEE format, 15+ entries)
- ☑ Bibliography (if applicable)
- ☑ Appendices (Code snippets, Gantt chart, Visualization outputs, Screenshots)

---

### ✓ **Formatting Requirements (Per Syllabus)**

**Page Setup:**
- ☑ **Page Size:** A4 (210 × 297 mm)
- ☑ **Top Margin:** 1.0 inch (2.54 cm)
- ☑ **Bottom Margin:** 1.0 inch (2.54 cm)
- ☑ **Left Margin:** 1.25 inches (3.17 cm)
- ☑ **Right Margin:** 1.0 inch (2.54 cm)
- ☑ **Page Numbers:** 
  - Front matter (Acknowledge to TOC): Roman numerals (i, ii, iii, ...), centered at bottom
  - Main chapters onwards: Arabic numerals (1, 2, 3, ...), centered at bottom

**Text Formatting:**
- ☑ **Font:** Times New Roman, entire document
- ☑ **Font Size (Paragraphs):** 12 pt
- ☑ **Line Spacing:** 1.5 throughout
- ☑ **Paragraph Alignment:** Justified

**Headings:**
- ☑ **Chapter Headings:** 16 pt, Bold (e.g., "1. INTRODUCTION")
- ☑ **Section Headings:** 14 pt, Bold (e.g., "1.1. Introduction")
- ☑ **Subsection Headings:** 12 pt, Bold (e.g., "1.1.1. Background")

**Tables & Figures:**
- ☑ **Alignment:** Centered on page
- ☑ **Table Captions:** Centered above table, Bold, 12 pt (e.g., "Table 1. Model Performance")
- ☑ **Figure Captions:** Centered below figure, Bold, 12 pt (e.g., "Figure 1. Gantt Chart")
- ☑ **Numbering:** Sequential per chapter (Table 1.1, Table 1.2, ... Figure 2.1, Figure 2.2, ...)

---

### ✓ **Content Specifics**

**Chapter 1 (Introduction):**
- ☑ Context about NEPSE and emerging markets
- ☑ Clear problem statement (gap in signal validation)
- ☑ 9 numbered objectives
- ☑ Scope (data range, symbols, techniques) and limitations (liquidity, non-stationarity, corporate actions)
- ☑ Development methodology (6 phases)
- ☑ Report organization

**Chapter 2 (Literature Review):**
- ☑ Technical indicators background (RSI, MACD, Bollinger Bands)
- ☑ ML in finance literature (with citations to Chen & Guestrin [9], López de Prado [4])
- ☑ Emerging market characteristics
- ☑ Walk-forward validation importance
- ☑ Transaction cost integration
- ☑ References to at least 6 academic sources

**Chapter 3 (Analysis):**
- ☑ Functional & non-functional requirements (8+ functional, 5+ non-functional)
- ☑ Feasibility: Technical (✓), Operational (✓), Economic (✓), Schedule (✓)
- ☑ Data Flow Diagram (DFD Level 0 & Level 1)
- ☑ Entity-Relationship schema

**Chapter 4 (Design):**
- ☑ 6-stage modular pipeline architecture
- ☑ Component design for each stage
- ☑ Data schema (column names, row counts, Parquet format)
- ☑ Algorithm specifications: RSI, MACD, Bollinger Bands (with formulas)
- ☑ Feature engineering list (25 features)
- ☑ XGBoost hyperparameters table
- ☑ Walk-forward fold configuration table
- ☑ Backtesting assumptions (cost model, entry/exit, position sizing)

**Chapter 5 (Implementation & Testing):**
- ☑ Tools table (17+ tools listed with versions and purpose)
- ☑ Module-by-module implementation details with code snippets
- ☑ Unit testing table (6+ test cases, all PASS)
- ☑ System testing table (8+ scenarios)
- ☑ Model performance results (7-fold AUC table, mean 0.5346)
- ☑ Backtest results comparison (ML vs. Signal-only vs. Buy-and-hold)
- ☑ Feature importance table (top 10 features)
- ☑ Real signal examples with interpretations

**Chapter 6 (Conclusion):**
- ☑ Summary of achievements (7 bullet points)
- ☑ Key findings with specific metrics
- ☑ Methodological rigor highlights
- ☑ Remaining work for final submission
- ☑ Future recommendations (5+ categories)

**References:**
- ☑ IEEE format: [#] Author, "Title," *Publication*, year, pages.
- ☑ 15+ references (mix of books, journals, conference proceedings)
- ☑ All in-text citations matched to reference list

---

### ✓ **Appendices (Minimum)**

- ☑ **Appendix A:** Data Processing Code (01_data_audit.py script)
- ☑ **Appendix B:** Feature Engineering Examples (code snippet)
- ☑ **Appendix C:** Walk-Forward Configuration (JSON)
- ☑ **Appendix D:** Backtesting Results (CSV excerpt)
- ☑ **Appendix E:** API Request/Response Examples (JSON)
- ☑ **Appendix F:** Repository Structure (tree format)
- ☑ **Appendix G:** Key Metrics Summary Table
- ☑ **Appendix H:** Gantt Chart (timeline visualization)
- ☑ Screenshots: [Output visualizations from outputs/ folder]
  - `label_distribution.png`
  - `feature_importance.png`
  - `walk_forward_folds.png`
  - `backtest_results.png`
  - `data_coverage.png`

---

### ✓ **Documentation Package**

**Files to Include in Submission:**

1. **Report Document:**
   - `MIDTERM_PROGRESS_REPORT.pdf` (primary) or `.docx` (editable)
   - `MIDTERM_PROGRESS_REPORT.md` (source)

2. **Supervisor Materials:**
   - `SUPERVISOR_APPROVAL_TEMPLATE.md` (filled and signed)
   - `INTERNAL_EXAMINER_APPROVAL.md` (filled and signed)

3. **Supporting Materials:**
   - `GANTT_CHART.md` (timeline and effort tracking)
   - `SUBMISSION_CHECKLIST.md` (this file)
   - `README.md` (project overview and setup instructions)

4. **Code & Data (on CD/USB or cloud link):**
   - Entire repository (`/src`, `/app`, `/data/processed`, `/outputs`)
   - Model artifacts (`/data/processed/models/`)
   - Generated visualizations (`/outputs/*.png`)
   - `requirements.txt` (for reproducibility)

---

### ✓ **Submission Format**

**Number of Copies:** 3 (as per syllabus)
- 1 copy → College Library
- 1 copy → Personal/Student records
- 1 copy → Dean Office, Exam Section, IST

**Binding & Presentation:**
- ☑ **Binding:** Golden Embracing with Black Binding (per syllabus)
- ☑ **Cover:** Typed on cover sheet with all required information
- ☑ **Print Quality:** Black & white, laser printed (color acceptable for figures)
- ☑ **Paper:** A4, white, 80 gsm minimum

**Digital Submission (if required):**
- ☑ PDF format (embedded fonts, all images at 300 DPI)
- ☑ File name: `CSC412_NEPSE_ML_Midterm_Report_[GroupName]_May2026.pdf`
- ☑ File size: < 50 MB (compress images if needed)

---

### ✓ **Pre-Submission Checklist**

**Content Verification:**
- ☑ All 6 chapters present and complete
- ☑ Abstract is 250-300 words
- ☑ All acronyms defined on first use (IEEE style)
- ☑ All tables and figures referenced in text
- ☑ All references cited in IEEE format [#]
- ☑ No plagiarism (use plagiarism checker tool)

**Formatting Verification:**
- ☑ Margins: 1.0" top/bottom, 1.25" left, 1.0" right
- ☑ Font: Times New Roman, 12 pt body, 1.5 line spacing
- ☑ Headings: 16 pt (Ch), 14 pt (Sec), 12 pt (Subsec), all bold
- ☑ Page numbers: Roman (i-vii) for front matter, Arabic (1+) for main
- ☑ Tables & figures: Centered, captions bold, proper numbering
- ☑ No orphans/widows (single lines at top/bottom of pages)

**Proof Reading:**
- ☑ Spell check (entire document)
- ☑ Grammar check (Grammarly or similar)
- ☑ Consistency: Terms, abbreviations, formatting
- ☑ Cross-references: All chapter/section/page references accurate
- ☑ ToC: Page numbers match actual pages

**Technical Verification:**
- ☑ PDF: Links work, fonts embedded, images clear
- ☑ Reproducibility: All code runnable, paths valid, requirements.txt complete
- ☑ Data: All outputs match code (backtest metrics, AUC scores, etc.)

---

### ✓ **Deliverables Summary**

| Deliverable | Format | Status |
|---|---|---|
| Midterm Report | PDF (primary), DOCX/MD (editable) | ✓ Complete |
| Supervisor Approval | Signed PDF | ⃞ Pending Signature |
| Internal Examiner Approval | Signed PDF | ⃞ Pending Signature |
| Gantt Chart | PNG/PDF | ✓ Complete |
| Code Repository | Git (on CD/GitHub) | ✓ Complete |
| Model Artifacts | Pickle files | ✓ Complete |
| Output Visualizations | PNG files | ✓ Complete |
| Appendices | PDF (embedded in report) | ✓ Complete |
| Setup Guide (README) | Markdown | ✓ Complete |

---

### ✓ **Submission Timeline**

| Milestone | Target Date | Status |
|---|---|---|
| Report Draft Complete | May 13, 2026 | ✓ Complete |
| Supervisor Review & Approval | May 17, 2026 | ⃞ Pending |
| Internal Examiner Review | May 20, 2026 | ⃞ Pending |
| Final Edits & Corrections | May 24, 2026 | ⃞ Pending |
| Binding & Copies Prepared | May 25, 2026 | ⃞ Pending |
| **SUBMISSION DEADLINE** | **May 27, 2026** | ⃞ Ready |
| Final Defense Date (Tentative) | June 3–10, 2026 | 📅 Scheduled |

---

### ✓ **Contact & Support**

**Supervisor:** Devendra Chapagain  
**Email:** [supervisor email]  
**Office:** CSIT Department, Birendra Multiple Campus

**Department Head:** [Name]  
**Office:** CSIT Department  

**Questions?** Refer to:
- Syllabus documentation (provided)
- Project notes: [docs/project-notes.md](../docs/project-notes.md)
- README: [docs/README.md](../docs/README.md)
- Implementation guide: [Getting Started](../docs/getting-started.md)

---

## **READY FOR SUBMISSION**

✓ All required content and formatting complete as of **May 13, 2026**

Next Steps:
1. **Print & Bind:** 3 copies (golden binding with black edges)
2. **Obtain Signatures:** Supervisor, Internal Examiner, Head/Coordinator
3. **Submit:** Give to Dean Office (or College Library as per institution protocol)
4. **Prepare Viva:** Finalize presentation slides and demo scripts for final defense

**Good luck with your midterm submission and final defense!**

