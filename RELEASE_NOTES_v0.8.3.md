# Release Notes - v0.8.3

Midgley **v0.8.3** is a dashboard modernization and accessibility release, eliminating residual hardcoded presentation figures, enforcing strict zero-synthetic-fallback guarantees, and delivering comprehensive WCAG 2.1 AA ARIA accessibility compliance across all 15 public HTML dashboard views.

---

## 🎯 Highlights & Improvements

### 1. Zero Hardcoded Figures & Strict Data Provenance (Issue #569)
- **Eliminated Synthetic Fallbacks**: Removed hardcoded fallback mock points from `generate_telemetry_page()`, rendering honest empty states (`map_points = []`) when geographic telemetry is unpopulated.
- **Fixed Template Currency Formatting**: Corrected double-dollar prefix formatting bugs in regional dashboard templates (`${{TULSA_MAE}}`, `${{NEWARK_MAE}}` -> `{{TULSA_MAE}}`, `{{NEWARK_MAE}}`), eliminating corrupted string rendering (`$$0.1100` -> `$0.1100`).

### 2. Comprehensive WCAG 2.1 AA ARIA Accessibility Compliance
- **Standardized Landmark Roles**: Structured all 15 dashboard HTML pages with semantic HTML5/ARIA landmarks:
  - Top navigation banner: `<header role="banner">`
  - Accessible navigation: `<nav aria-label="Main Navigation">`
  - Primary content container: `<main id="main-content" role="main">`
  - Keyboard skip links: `<a href="#main-content" class="sr-only focus:not-sr-only ...">Skip to main content</a>`
- **Accessible Interactive Controls & Dropdowns**:
  - Main Metro Areas selector button: `id="metro-menu-btn"`, `aria-haspopup="true"`, `aria-expanded="false"`, `aria-controls="metro-dropdown-menu"`, `aria-label="Metro Areas Selection Menu"`
  - Dropdown container: `role="menu"` with child menu items `role="menuitem"`
  - Category filter buttons (`docs/sources.html`): `type="button"`, `aria-label="..."`, and `aria-pressed="true|false"`
  - Decorative icons tagged with `aria-hidden="true"`
- **Accessible Data Visualizations & Heatmaps**:
  - All Chart.js canvas elements equipped with `role="img"` and descriptive `aria-label` text summarizing the chart trends and metrics.
  - Interactive Leaflet ZIP heatmap container equipped with `role="region"` and `aria-label="Geographic Out-of-Metro ZIP Code Demand Heatmap"`.
- **Accessible Tabular Data**:
  - Integrated `<caption class="sr-only">` summarizing table purposes and `<th scope="col">` on all column headers across scoreboard tables, connector audit tables, token usage tables, model iteration timeline tables, and sub-locale forecast tables.
- **Accessible Form Controls**:
  - Associated explicit `<label for="...">` elements and `aria-label` attributes with all input fields, dropdown presets, and sliders on the Fill-Up Timing & Estimated Savings Advisor (`docs/savings.html`).

### 3. Automated Accessibility Test Suite
- Added `test_dashboard_aria_accessibility_and_landmarks()` to `tests/test_dashboard_generator.py` to continuously validate landmark roles, skip-link targets, chart canvas roles, table captions, and lack of double-dollar formatting artefacts across all generated dashboard pages.

---

## 📦 Commits & Attribution
* **Tag**: `v0.8.3`
* **Resolved Issues**: #569
