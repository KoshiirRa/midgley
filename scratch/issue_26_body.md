### Summary
The educational math guide page ([`docs/math.html`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/math.html)) contains broken KaTeX LaTeX rendering in Sections 07, 08, and 09 (Step 7 onwards).

### Root Cause
In [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py), standard non-raw Python string literals were used for Sections 7–9. At Python runtime, backslash escape sequences in LaTeX macros were evaluated as Python string escapes:
- `\text` -> Tab (`\t`) + `ext` (`	ext`)
- `\frac` -> Form feed (`\f`) + `rac` (`rac`)
- `\right` -> Carriage return (`\r`) + `ight` (` ight`)
- `\alpha` -> ASCII bell (`\a`) + `lpha` (` lpha`)
- `\beta` -> Backspace (`\b`) + `eta` (` eta`)
- `\boldsymbol` -> Backspace (`\b`) + `oldsymbol` (` oldsymbol`)
- `\times` -> Tab (`\t`) + `imes` (`	imes`)

When `src/dashboard_generator.py` generates `docs/math.html`, these unescaped control characters produce invalid KaTeX syntax, causing math formulas to display broken raw text in the browser.

### Affected Equations
- **Step 7 (Equation 7.1):** Live News Vector Ingestion & Batch Factor Scoring (`\text` & `\right` corrupted)
- **Step 8 (Equation 8.1):** Continuous Memory Decay Accumulator (`\frac`, `\right`, & `\text` corrupted)
- **Step 9 (Equation 9.1):** Regularized Ridge Objective Function & Calibration (`\boldsymbol`, `\beta`, `\alpha`, `\times`, `\text`, & `\right` corrupted)

### Expected Behavior
Equations in Step 7, 8, and 9 should render formatted KaTeX math identically to Steps 1–6.

### Steps to Reproduce
1. Open `docs/math.html` in any web browser.
2. Scroll down to Section 07 ("Real-Time Financial Media Feed"), Section 08 ("Exponential Memory Decay"), and Section 09 ("Standardized Ridge Estimator").
3. Observe KaTeX parse errors and corrupted LaTeX backslash characters.

### Suggested Fix
1. Update `src/dashboard_generator.py` to use raw string literals (`r"""..."""`) or double-escaped backslashes in multi-line HTML templates for Sections 7–9.
2. Execute `python src/dashboard_generator.py` to regenerate clean KaTeX markup in `docs/math.html`.
