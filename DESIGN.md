# Midgley Vintage Fuel Intelligence Design System (`DESIGN.md`)

> **Namesake & Heritage**: Named in honor of **Thomas Midgley Jr.** (1889–1944), pioneering chemical engineer at Dayton Engineering Laboratories (DELCO) and General Motors, who invented tetraethyllead unleaded additives and early hydrocarbon combustion diagnostics. The **Midgley Design System** captures the aesthetic of a 1920s–1930s petroleum research laboratory and vintage roadside filling station—blending antique brass pressure gauges, deep mahogany wood, dark coking charcoal, sepia warm amber glows, typewriter typography, and mechanical rolling gas pump counters with modern quantitative fuel forecasting.

---

## 1. Visual Theme & Atmosphere

* **Theme Name**: *1920s Vintage Petroleum Laboratory & Antique Brass Gas Pump Terminal*
* **Atmosphere**: Warm dark industrial, aged brass, distressed copper, sepia amber, deep mahogany wood, and dark coking charcoal.
* **Core Philosophy**: Merges early-20th-century industrial mechanical elegance (brass rivet borders, analogue dials, typewriter typography, mechanical gas pump rolling counters) with 5-day out-of-time price prediction algorithms.
* **Aesthetic Anchors**: DELCO laboratory equipment, vintage Ethyl Corp gasoline signs, mechanical counter dials, and sepia research logs.

---

## 2. Color Palette & Vintage Tokens

| Category | Token / Color Name | Hex Code | Tailwind Equivalent | Usage & Role |
| :--- | :--- | :--- | :--- | :--- |
| **Page Canvas** | `Mahogany Charcoal` | `#0D0907` | `bg-[#0D0907]` | Main vintage background (dark aged timber & soot) |
| **Primary Container** | `Weathered Slate & Iron` | `#17120F` | `bg-[#17120F]` / `bg-stone-900` | Cards, gauge containers, research lab panels |
| **Sub-Surface** | `Coking Iron` | `#241C17` | `bg-[#241C17]` | Sub-panels, table headers, dropdown menus |
| **Border & Rivets** | `Antique Brass Border` | `#785327` | `border-[#785327]/60` | Aged brass frame lines, 1px rivet borders |
| **Primary Accent** | `Midgley Vintage Amber` | `#F59E0B` | `text-amber-400` / `bg-amber-600` | Core brand highlight, fuel pump display, octane numbers |
| **Copper Accent** | `Refinery Copper` | `#D97706` | `text-amber-600` | Cushing WTI crude, pipeline pressure dials |
| **Sepia Text** | `Laboratory Sepia` | `#FEF3C7` | `text-amber-100` | Main text values, antique paper labels |
| **Kerosene Red** | `Kerosene Flame Red` | `#DC2626` | `text-red-500` / `bg-red-950` | Outages (HF Sinclair, Catlettsburg), tornado shocks, pressure relief valves |
| **Vintage Emerald** | `Petroleum Emerald` | `#059669` | `text-emerald-400` / `bg-emerald-950` | Target hits, price drops, rack margin expansion |
| **Secondary Text** | `Aged Typewriter Gray` | `#A8A29E` | `text-stone-400` | Metric subheadings, target dates, table headers |
| **Muted Footnotes** | `Engine Oil Brown` | `#78716C` | `text-stone-500` | Lab footnotes, timestamps, patent metadata |

---

## 3. Typography & Vintage Readout Formatting

### Font Families
* **Headings & Badges**: `Courier Prime`, `Courier New`, `Courier`, `serif` / `monospace` (1920s Industrial Typewriter style).
* **Interface Text**: `Georgia`, `Garamond`, `Cambria`, `Times New Roman`, `serif` (Vintage publication typography).
* **Prices & Dials**: `JetBrains Mono`, `Courier New`, `Consolas`, `monospace` (Mechanical rolling gas pump counter effect).

### Typography Scale

```
[Lab Section Header]       font-serif text-2xl sm:text-3xl | font-bold | text-amber-200 | border-b border-[#785327]/50
  └── [Card Badge]         font-mono text-xs | tracking-widest | text-amber-400 | bg-[#2A1D13] border-[#785327]
        └── [Hero Readout] font-mono text-3xl sm:text-4xl | font-extrabold | text-amber-400 | bg-[#0A0705] border-2 border-[#573A1B]
```

### Mechanical Price Readout Standard
1. **Gasoline Prices**: MUST format to 3 decimal places with `/gal` suffix in an mechanical counter box:
   * Correct: `$3.890/gal`, `$3.184/gal`
   * Incorrect: `$3.89/gal`, `$3.9`
2. **Model Metrics**: Format MAE to 4 decimal places and Directional Hit Rate to 2 decimal places:
   * MAE: `$0.1069 MAE`
   * Directional Accuracy: `60.79%`

---

## 4. Vintage Component Stylings & Specifications

### 4.1 Vintage Mechanical Fuel Pump Card
```html
<div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-6 shadow-2xl space-y-4 relative overflow-hidden">
  <!-- Brass Rivet Header Badge -->
  <div class="flex items-center justify-between border-b border-[#785327]/40 pb-3">
    <span class="text-xs px-3 py-1 rounded bg-[#2A1D13] text-amber-300 border border-[#785327] font-mono tracking-widest uppercase">
      ⚙️ DELCO LABS &bull; TULSA, OK
    </span>
    <span class="text-xs text-stone-400 font-mono">EST. 1926</span>
  </div>

  <!-- Mechanical Price Counter Box -->
  <div class="bg-[#0A0705] border-2 border-[#573A1B] rounded-lg p-4 font-mono text-center shadow-inner">
    <div class="text-[10px] text-amber-600/90 uppercase tracking-widest font-bold mb-1">5-Day Out Projected Price</div>
    <div class="text-4xl font-extrabold text-amber-400 tracking-wider">$3.890<span class="text-sm text-stone-400">/gal</span></div>
  </div>

  <div class="flex items-center justify-between text-xs font-mono text-stone-400 pt-2 border-t border-[#785327]/30">
    <span>Cushing WTI Spot: <strong class="text-amber-300">$0.706/gal</strong></span>
    <span class="text-emerald-400 font-bold">▲ +$0.173 (4.58%)</span>
  </div>
</div>
```

### 4.2 Kerosene Emergency Valve Alert
```html
<div class="bg-red-950/40 border border-red-800/60 text-red-300 rounded-xl p-4 font-mono text-xs flex items-start space-x-3 shadow-lg">
  <span class="text-red-500 font-bold text-xl leading-none mt-0.5">⚠️</span>
  <div>
    <strong class="text-red-200 uppercase tracking-wider font-bold">West Tulsa Refinery EF-3 Tornado Disruption:</strong>
    <span class="text-red-300/90 ml-1">Alkylation unit pressure drop producing a +$0.173/gal (+4.58%) shock decay vector.</span>
  </div>
</div>
```

### 4.3 Sepia Lab Research Log & Formula Block
```html
<div class="bg-[#17120F] border border-[#785327]/50 rounded-2xl p-6 space-y-4 shadow-xl">
  <div class="flex items-center justify-between border-b border-[#785327]/40 pb-2">
    <span class="text-xs font-mono text-amber-400 uppercase tracking-widest">// DAYTON LAB LOG &bull; EQUATION 2.1</span>
    <span class="text-xs font-mono text-stone-400">Half-Life \(t_{1/2} = 5.0\text{ days}\)</span>
  </div>
  <div class="katex-display text-amber-100 bg-[#0A0705] p-4 rounded-xl border border-[#573A1B]">
    $$\text{Memory}_{t} = \text{Memory}_{t-1} \times e^{-\frac{\ln(2)}{t_{1/2}}} + \text{NewShock}_t$$
  </div>
</div>
```

---

## 5. Layout & Grid Principles

* **Max Width Container**: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
* **Grid Layout**: 3 Columns on desktop (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`).
* **Frame Borders**: 1px aged brass (`border-[#785327]/60`) with subtle warm amber drop-shadows (`shadow-amber-900/10`).

---

## 6. Do's and Don'ts (Design Guardrails)

### ✅ DO
* **DO** use warm sepia amber (`#F59E0B`), mahogany charcoal (`#0D0907`), and aged typewriter gray (`#A8A29E`).
* **DO** use serif typography (`Georgia`, `Garamond`) for lab section titles and `Courier Prime` / `JetBrains Mono` for readouts.
* **DO** format fuel prices with 3 decimal places inside mechanical counter boxes (`$3.890/gal`).
* **DO** frame key cards with brass rivet border styling (`border-[#785327]/60`).

### ❌ DON'T
* **DON'T** use modern neon electric colors or stark cold blues/whites (`#00FFFF`, `#FFFFFF`).
* **DON'T** use sleek modern sans-serif fonts exclusively; preserve the 1920s vintage industrial laboratory feel.
* **DON'T** omit the `/gal` price unit tag or round prices to 2 decimals (`$3.89/gal` is invalid).

---

## 7. AI Agent Prompt Guide

When asking AI coding tools (Antigravity, Cursor, Claude Code) to build components for Midgley:

```text
Follow the Midgley Vintage Fuel Design System (DESIGN.md):
- Aesthetic: 1920s Thomas Midgley Jr. Petroleum Research Lab & Vintage Gas Pump (Mahogany Charcoal #0D0907 background, Weathered Slate #17120F cards, Antique Brass #785327 borders).
- Accents: Vintage Amber (#F59E0B), Refinery Copper (#D97706), Sepia Text (#FEF3C7).
- Typography: Georgia/serif for lab headers, Courier/JetBrains Mono for mechanical counter readouts ($3.890/gal).
- Card Frame: Brass rivet borders (border-[#785327]/60) with mechanical price counter boxes (bg-[#0A0705] border-2 border-[#573A1B]).
```

---

## 8. Decoupled Regional Metadata & Visual Card Architecture

All regional driver cards, refining logistics, state/local tax structures, physical infrastructure delivery dynamics, and shock scenario definitions MUST adhere to the **Regional Storage Specification**:
- **Profiles Directory**: Maintain structured JSON files under `data/regional_metadata/<region_id>.json` (`tulsa_ok.json`, `newark_de.json`, `cincinnati_oh.json`, `greenville_nc.json`, `charlotte_nc.json`, `oakland_ca.json`, `bayarea_ca.json`).
- **Card Rendering**: Use `render_regional_driver_cards_html(region_id)` from [`src/regional_metadata.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/regional_metadata.py) inside [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py) to dynamically construct responsive Tailwind visual cards covering all 4 core dimensions. Never hardcode prose driver descriptions inside Python HTML template strings.

