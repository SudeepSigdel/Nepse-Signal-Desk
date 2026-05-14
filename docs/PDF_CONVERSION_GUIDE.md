# PDF CONVERSION & FORMATTING GUIDE

## Converting Markdown Report to Formatted PDF

Your midterm report has been created as a comprehensive Markdown file: `MIDTERM_PROGRESS_REPORT.md`

This guide explains how to convert it to a **professionally formatted PDF** that meets the syllabus requirements.

---

## Option 1: Using Microsoft Word (RECOMMENDED - Easiest)

### Step 1: Convert Markdown to Word Document

**Using Pandoc (Command Line):**

```bash
# Install Pandoc if not already installed
# Download from: https://pandoc.org/installing.html

# Convert Markdown to Word (.docx)
pandoc "MIDTERM_PROGRESS_REPORT.md" -o "MIDTERM_PROGRESS_REPORT.docx" --from markdown --to docx

# Or with enhanced formatting:
pandoc "MIDTERM_PROGRESS_REPORT.md" -o "MIDTERM_PROGRESS_REPORT.docx" \
  --from markdown \
  --to docx \
  --toc \
  --number-sections \
  --highlight-style=tango
```

**Using Online Tools (No Installation Needed):**
1. Visit: https://pandoc.org/try/
2. Paste Markdown content from MIDTERM_PROGRESS_REPORT.md
3. Select Format: Markdown → Docx (MS Word)
4. Download converted file

### Step 2: Format in Microsoft Word

Open the converted `.docx` file and apply syllabus formatting:

#### **Margins:**
1. Go to **Layout** tab → **Margins** → **Custom Margins**
2. Set:
   - Top: 1"
   - Bottom: 1"
   - Left: 1.25"
   - Right: 1"

#### **Font & Paragraph:**
1. Select all text (Ctrl+A)
2. Change font to **Times New Roman, 12 pt**
3. Go to **Home** → **Paragraph** → Set line spacing to **1.5**
4. Alignment: **Justified**

#### **Headings:**
1. Chapter headings (e.g., "1. INTRODUCTION"): **16 pt, Bold**
   - Home → Styles → Modify "Heading 1" → 16 pt Bold
2. Section headings (e.g., "1.1. Introduction"): **14 pt, Bold**
   - Home → Styles → Modify "Heading 2" → 14 pt Bold
3. Subsection headings (e.g., "1.1.1. Background"): **12 pt, Bold**
   - Home → Styles → Modify "Heading 3" → 12 pt Bold

#### **Page Numbers:**
1. Insert → **Page Numbers** → Position: Bottom Center
2. For Roman numerals (front matter):
   - First, section off the front matter (before Chapter 1)
   - Different first page is enabled automatically
   - Format page numbers as: **i, ii, iii, ...**
   - From Chapter 1 onwards: **1, 2, 3, ...**

**How to Set Roman for Front Matter:**
- Click in front matter section
- Insert → Page Number → Format → Choose i, ii, iii style
- In Chapter 1 section: Insert → Page Number → Format → Choose 1, 2, 3 style

#### **Tables & Figures:**
1. All tables/figures: Center on page (Ctrl+E or Center button)
2. Table captions: 
   - Insert → **Table Name** → "Table 1. Model Performance"
   - Bold, centered above table, 12 pt
3. Figure captions:
   - Insert → **Image Caption** → "Figure 1. Gantt Chart"
   - Bold, centered below figure, 12 pt

#### **Embeds & Visualizations:**
1. For images (from `/outputs/`):
   - Insert → Pictures → Select PNG files
   - Resize to fit page (maintain aspect ratio)
   - Center, add caption below
2. For code snippets (Appendix A–E):
   - Use monospace font (Courier New, 10 pt) for code blocks
   - Use gray background for code (optional)

#### **Table of Contents:**
1. After creating all sections, go to **References** tab
2. Click **Table of Contents** → Choose a style
3. Word will auto-generate from your headings
4. Set to **Update Automatically** for page numbers

#### **References:**
1. Keep IEEE format as-is in the Markdown
2. Ensure all citations [1]–[16] are present and match references section
3. Use **References** tab → **Manage Sources** for optional bibliography management

### Step 3: Generate PDF

1. File → **Save As**
2. Choose format: **PDF**
3. Name: `MIDTERM_PROGRESS_REPORT.pdf`
4. Options:
   - ☑ Include non-printing information: False
   - ☑ PDF/A compliant: False (can limit formatting)
5. Click **Save**

---

## Option 2: Using Google Docs (FREE, Cloud-Based)

### Step 1: Create Document

1. Go to **Google Docs** (https://docs.google.com)
2. New blank document
3. Paste Markdown content (formatted)

### Step 2: Format in Google Docs

#### **Margins:**
1. File → **Page setup**
2. Set:
   - Top: 1"
   - Bottom: 1"
   - Left: 1.25"
   - Right: 1"

#### **Font & Paragraph:**
1. Select all (Ctrl+A)
2. Font: Times New Roman, 12 pt
3. Line spacing: 1.5
4. Alignment: Justified

#### **Headings:**
1. Use Format → Paragraph styles
2. Heading 1 (16 pt bold): Chapter titles
3. Heading 2 (14 pt bold): Section titles
4. Heading 3 (12 pt bold): Subsection titles

#### **Insert Visualizations:**
1. Insert → Image → Upload PNG files from `/outputs/`
2. Center images, add captions below (italic, 10 pt)

### Step 3: Download as PDF

1. File → **Download** → **PDF Document (.pdf)**
2. Automatically saves to your device

---

## Option 3: Using Pandoc + LaTeX (Advanced - Best Quality)

### Prerequisites:
- Pandoc installed
- LaTeX installed (MiKTeX or TeX Live)

### Step 1: Create LaTeX Template

Create a file `preamble.tex`:

```latex
\documentclass[12pt,a4paper]{article}
\usepackage[top=1in, bottom=1in, left=1.25in, right=1in]{geometry}
\usepackage{setspace}
\doublespacing  % 1.5 line spacing approximation
\usepackage{times}  % Times New Roman
\usepackage{graphicx}
\usepackage{float}
\usepackage{fancyhdr}

% Page numbers
\pagestyle{fancy}
\cfoot{\thepage}

% Headings
\usepackage{titlesec}
\titleformat{\section}{\fontsize{16}{16}\bfseries}{\thesection.}{1em}{}
\titleformat{\subsection}{\fontsize{14}{14}\bfseries}{\thesubsection.}{1em}{}
\titleformat{\subsubsection}{\fontsize{12}{12}\bfseries}{\thesubsubsection.}{1em}{}

\begin{document}
```

### Step 2: Convert with Pandoc

```bash
pandoc MIDTERM_PROGRESS_REPORT.md \
  -o MIDTERM_PROGRESS_REPORT.pdf \
  --from markdown \
  --to pdf \
  --include-in-header=preamble.tex \
  --toc \
  --number-sections
```

**Note:** This requires LaTeX to be installed. Install via:
- **Windows:** MiKTeX (https://miktex.org)
- **Mac:** MacTeX (https://tug.org/mactex)
- **Linux:** `sudo apt install texlive-full`

---

## Option 4: Using Markdown PDF Extension (VS Code)

### Step 1: Install Extension

1. Open VS Code
2. Extensions → Search: `Markdown PDF`
3. Install by **yzane** (most popular)

### Step 2: Convert

1. Open `MIDTERM_PROGRESS_REPORT.md` in VS Code
2. Right-click → **Markdown PDF: Export (PDF)**
3. Saves to same directory as `.pdf`

### Step 3: Manual Formatting Adjustments

The auto-generated PDF may need tweaks:
- Use Option 1 (Word) to refine margins, fonts, page numbers if needed

---

## Formatting Verification Checklist

After converting to PDF, verify:

- ☑ Page margins: 1.0" (T/B), 1.25" (L), 1.0" (R)
- ☑ Font: Times New Roman, 12 pt (body text)
- ☑ Line spacing: 1.5 throughout
- ☑ Chapter headings: 16 pt, bold
- ☑ Section headings: 14 pt, bold
- ☑ Page numbers: Roman (i-vii) for front matter, Arabic (1+) for main
- ☑ Tables/Figures: Centered, captions bold, 12 pt
- ☑ All figures visible (check PDF pages)
- ☑ References: All citations [1]–[16] present
- ☑ No orphan/widow lines
- ☑ File size < 50 MB
- ☑ PDF is selectable text (not image scan)

---

## Recommended Workflow

**For Best Results:**

1. **Convert to Word** (Option 1) using Pandoc
   - Most control over formatting
   - Easiest to adjust margins, fonts, spacing
   - Native support for table of contents

2. **Fine-tune in Word**
   - Apply exact margins and fonts per syllabus
   - Verify page numbers (Roman + Arabic)
   - Adjust table/figure captions if needed

3. **Export as PDF**
   - File → Save As → PDF
   - Verify formatting is preserved

4. **Verify Final PDF**
   - Open in Adobe Reader
   - Check all pages, fonts, images
   - Test that text is selectable (not scanned)

---

## Troubleshooting

**Problem: Page numbers not showing**
- Solution: Word may have different section for front matter. Ensure "Link to Previous" is unchecked between sections.

**Problem: Margins look wrong**
- Solution: Check Layout → Margins. Some default templates override custom margins. Use Custom Margins explicitly.

**Problem: Figure images are blurry**
- Solution: Ensure images are at least 1200 × 800 pixels. Resize in Word if needed (Image → Format → Picture).

**Problem: Fonts changed to default**
- Solution: Select all text again, manually change to Times New Roman 12 pt. Some versions don't preserve fonts during Pandoc conversion.

**Problem: PDF file is too large (> 50 MB)**
- Solution: Compress images using Tools online (https://tinypng.com). Replace in Word, re-export PDF.

---

## File Naming Convention

```
MIDTERM_PROGRESS_REPORT.pdf
├─ For submission (rename if needed):
│  CSC412_NEPSE_ML_Signal_Validation_Midterm_Report_May2026.pdf
│  └─ Keep date included for archive purposes

├─ Backup versions:
│  MIDTERM_PROGRESS_REPORT_v1.pdf
│  MIDTERM_PROGRESS_REPORT_v1_FINAL.pdf
```

---

## Final Checklist for Submission

```
Before Printing 3 Physical Copies:
☑ PDF opens without errors
☑ All pages present (should be ~40 pages including appendices)
☑ Formatting matches syllabus requirements
☑ Spell check complete (Grammarly or Word)
☑ All links and references work
☑ File size < 50 MB
☑ Ready for binding (golden + black)

Before Submitting Hard Copies:
☑ Print on A4 white paper (80 gsm minimum)
☑ Black & white printing (or color for figures if available)
☑ Binding: Golden with black edges (3 copies)
☑ Supervisor, Internal Examiner, Head signatures obtained
☑ All appendices included (code, Gantt chart, visualizations)
```

---

**Questions?** Refer to your supervisor or the department office.

**Deadline:** May 27, 2026 ✓

---

