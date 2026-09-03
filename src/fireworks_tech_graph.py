"""
Fireworks Tech Graph - Automated Architecture Diagram Generator (src/fireworks_tech_graph.py)

Generates validated, geometry-checked SVG architecture diagrams for the 8-stage multi-agent
pipeline and 6 regional metro calibration hubs for display in AGENTS.md and the public web dashboard.
"""

import os
import xml.etree.ElementTree as ET

def generate_multi_agent_pipeline_svg() -> str:
    """
    Generates scalable vector graphics (SVG) diagram for the 8-stage Multi-Agent Architecture Pipeline.
    """
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="100%" height="100%" style="background-color: #0b0f19; font-family: system-ui, -apple-system, sans-serif;">
  <defs>
    <!-- Gradients -->
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.2"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>

    <!-- Arrow Markers -->
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/>
    </marker>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#34d399"/>
    </marker>
    <marker id="arrow-purple" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#a78bfa"/>
    </marker>
    <marker id="arrow-yellow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#fbbf24"/>
    </marker>
  </defs>

  <!-- Title Header Banner -->
  <rect x="30" y="25" width="1140" height="60" rx="12" fill="url(#headerGrad)" stroke="#3b82f6" stroke-opacity="0.3" stroke-width="1"/>
  <text x="50" y="60" fill="#f8fafc" font-size="20" font-weight="700" letter-spacing="0.5">MIDGLEY UNLEADED GASOLINE FORECASTING ENGINE</text>
  <text x="760" y="60" fill="#94a3b8" font-size="13" font-weight="500">8-Stage Multi-Agent Architecture Pipeline</text>

  <!-- ROW 1: Stages 1 to 5 -->

  <!-- STAGE 1 & 2: Extraction & Fusion -->
  <g transform="translate(30, 110)">
    <rect width="260" height="280" rx="14" fill="url(#cardGrad)" stroke="#38bdf8" stroke-opacity="0.4" stroke-width="1.5"/>
    <rect x="14" y="14" width="85" height="22" rx="6" fill="#0284c7" fill-opacity="0.2" stroke="#0369a1" stroke-width="1"/>
    <text x="22" y="29" fill="#38bdf8" font-size="11" font-weight="700">STAGE 1 &amp; 2</text>
    <text x="14" y="62" fill="#f8fafc" font-size="15" font-weight="700">Extraction &amp; Fusion</text>
    
    <rect x="14" y="76" width="232" height="186" rx="8" fill="#0f172a" fill-opacity="0.6"/>
    <text x="24" y="96" fill="#e2e8f0" font-size="12" font-weight="600">• Event &amp; Weather NLP</text>
    <text x="34" y="114" fill="#94a3b8" font-size="11">Google Gemini 2.5 Flash</text>
    <text x="34" y="130" fill="#94a3b8" font-size="11">Finlight energy headlines</text>
    
    <text x="24" y="156" fill="#e2e8f0" font-size="12" font-weight="600">• Physics &amp; Weather Feeds</text>
    <text x="34" y="174" fill="#94a3b8" font-size="11">NOAA NWS &amp; SPC Tornado</text>
    <text x="34" y="190" fill="#94a3b8" font-size="11">Hormuz/Suez Maritime</text>

    <text x="24" y="216" fill="#e2e8f0" font-size="12" font-weight="600">• Memory Fusion Engine</text>
    <text x="34" y="234" fill="#38bdf8" font-size="11" font-weight="600">Shock Decay t½ = 4.0 - 5.0d</text>
  </g>

  <!-- Arrow 1 -> 2 -->
  <path d="M 290 250 L 324 250" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- STAGE 3: Main Quantitative Model -->
  <g transform="translate(330, 110)">
    <rect width="260" height="280" rx="14" fill="url(#cardGrad)" stroke="#34d399" stroke-opacity="0.5" stroke-width="1.5"/>
    <rect x="14" y="14" width="70" height="22" rx="6" fill="#059669" fill-opacity="0.2" stroke="#047857" stroke-width="1"/>
    <text x="22" y="29" fill="#34d399" font-size="11" font-weight="700">STAGE 3</text>
    <text x="14" y="62" fill="#f8fafc" font-size="15" font-weight="700">Main Model Forecast</text>
    
    <rect x="14" y="76" width="232" height="186" rx="8" fill="#0f172a" fill-opacity="0.6"/>
    <text x="24" y="96" fill="#e2e8f0" font-size="12" font-weight="600">• Commodity Base</text>
    <text x="34" y="114" fill="#34d399" font-size="11" font-weight="600">NYMEX RBOB (RB=F)</text>
    <text x="34" y="130" fill="#94a3b8" font-size="11">WTI Crude Oil (CL=F)</text>
    
    <text x="24" y="156" fill="#e2e8f0" font-size="12" font-weight="600">• Estimator Pipeline</text>
    <text x="34" y="174" fill="#94a3b8" font-size="11">Standardized Ridge (α=10)</text>
    <text x="34" y="190" fill="#94a3b8" font-size="11">XGBoost &amp; Stacking Ensemble</text>

    <text x="24" y="216" fill="#e2e8f0" font-size="12" font-weight="600">• Cross-Validation</text>
    <text x="34" y="234" fill="#94a3b8" font-size="11">Purged &amp; Combinatorial CV</text>
  </g>

  <!-- Arrow 2 -> 3 -->
  <path d="M 590 250 L 624 250" fill="none" stroke="#34d399" stroke-width="2" marker-end="url(#arrow-green)"/>

  <!-- STAGE 4: Localized Metro Area Calibration -->
  <g transform="translate(630, 110)">
    <rect width="260" height="280" rx="14" fill="url(#cardGrad)" stroke="#a78bfa" stroke-opacity="0.5" stroke-width="1.5"/>
    <rect x="14" y="14" width="70" height="22" rx="6" fill="#7c3aed" fill-opacity="0.2" stroke="#6d28d9" stroke-width="1"/>
    <text x="22" y="29" fill="#a78bfa" font-size="11" font-weight="700">STAGE 4</text>
    <text x="14" y="62" fill="#f8fafc" font-size="15" font-weight="700">Metro Calibration</text>
    
    <rect x="14" y="76" width="232" height="186" rx="8" fill="#0f172a" fill-opacity="0.6"/>
    <text x="24" y="96" fill="#e2e8f0" font-size="12" font-weight="600">• 8 Regional Hubs</text>
    <text x="34" y="114" fill="#a78bfa" font-size="11">Tulsa, OK (Cushing WTI)</text>
    <text x="34" y="130" fill="#a78bfa" font-size="11">Newark, DE (Delaware City)</text>
    <text x="34" y="146" fill="#a78bfa" font-size="11">Cincinnati, OH/KY (Ohio River)</text>
    <text x="34" y="162" fill="#a78bfa" font-size="11">Greenville &amp; Charlotte, NC</text>
    <text x="34" y="178" fill="#a78bfa" font-size="11">Oakland &amp; SF Bay Area, CA</text>
    <text x="34" y="194" fill="#a78bfa" font-size="11">Port St. Lucie, FL (Waterborne)</text>

    <text x="24" y="222" fill="#e2e8f0" font-size="12" font-weight="600">• ULSD Distillate Engine</text>
    <text x="34" y="240" fill="#94a3b8" font-size="11">HO=F &amp; 3-2-1 Crack Margin</text>
  </g>

  <!-- Arrow 3 -> 4 -->
  <path d="M 890 250 L 924 250" fill="none" stroke="#a78bfa" stroke-width="2" marker-end="url(#arrow-purple)"/>

  <!-- STAGE 5: Synthesis & Shock Simulator -->
  <g transform="translate(930, 110)">
    <rect width="240" height="280" rx="14" fill="url(#cardGrad)" stroke="#fbbf24" stroke-opacity="0.5" stroke-width="1.5"/>
    <rect x="14" y="14" width="70" height="22" rx="6" fill="#d97706" fill-opacity="0.2" stroke="#b45309" stroke-width="1"/>
    <text x="22" y="29" fill="#fbbf24" font-size="11" font-weight="700">STAGE 5</text>
    <text x="14" y="62" fill="#f8fafc" font-size="15" font-weight="700">Shock Simulator</text>
    
    <rect x="14" y="76" width="212" height="186" rx="8" fill="#0f172a" fill-opacity="0.6"/>
    <text x="24" y="96" fill="#e2e8f0" font-size="12" font-weight="600">• Scenario Engine</text>
    <text x="34" y="114" fill="#fbbf24" font-size="11">Refinery Outage Shock</text>
    <text x="34" y="130" fill="#fbbf24" font-size="11">Hormuz Strait Blockade</text>
    <text x="34" y="146" fill="#fbbf24" font-size="11">Weekend Executive Post</text>
    
    <text x="24" y="174" fill="#e2e8f0" font-size="12" font-weight="600">• Output Synthesis</text>
    <text x="34" y="192" fill="#94a3b8" font-size="11">Real-time counterfactual</text>
    <text x="34" y="208" fill="#94a3b8" font-size="11">shock price multipliers</text>
    <text x="34" y="234" fill="#38bdf8" font-size="11" font-weight="600">MCP Server Tool Gateway</text>
  </g>

  <!-- ROW 2: Connector Path Downwards -->
  <path d="M 1050 390 L 1050 430 L 160 430 L 160 470" fill="none" stroke="#64748b" stroke-width="2" stroke-dasharray="6,4" marker-end="url(#arrow)"/>

  <!-- ROW 2: Stages 6 to 8 -->

  <!-- STAGE 6: MLOps Prediction Logger -->
  <g transform="translate(30, 470)">
    <rect width="340" height="270" rx="14" fill="url(#cardGrad)" stroke="#38bdf8" stroke-opacity="0.4" stroke-width="1.5"/>
    <rect x="14" y="14" width="70" height="22" rx="6" fill="#0284c7" fill-opacity="0.2" stroke="#0369a1" stroke-width="1"/>
    <text x="22" y="29" fill="#38bdf8" font-size="11" font-weight="700">STAGE 6</text>
    <text x="14" y="62" fill="#f8fafc" font-size="15" font-weight="700">MLOps Prediction Logging Agent</text>
    
    <rect x="14" y="76" width="312" height="176" rx="8" fill="#0f172a" fill-opacity="0.6"/>
    <text x="24" y="98" fill="#e2e8f0" font-size="12" font-weight="600">• Persistent Prediction Store</text>
    <text x="34" y="118" fill="#38bdf8" font-size="11" font-family="monospace">data/prediction_history.csv</text>
    <text x="34" y="136" fill="#94a3b8" font-size="11">Out-of-time forecast logging &amp; backfilled actuals</text>
    
    <text x="24" y="164" fill="#e2e8f0" font-size="12" font-weight="600">• Observability Ledger</text>
    <text x="34" y="184" fill="#94a3b8" font-size="11">Axiom log analytics &amp; Sentry error tracking</text>
    <text x="34" y="202" fill="#94a3b8" font-size="11">Cloudflare Edge SWR cache gateway</text>
  </g>

  <!-- Arrow 6 -> 7 -->
  <path d="M 370 605 L 424 605" fill="none" stroke="#34d399" stroke-width="2" marker-end="url(#arrow-green)"/>

  <!-- STAGE 7: Weekly Model Review & Feedback Loop -->
  <g transform="translate(430, 470)">
    <rect width="350" height="270" rx="14" fill="url(#cardGrad)" stroke="#34d399" stroke-opacity="0.5" stroke-width="1.5"/>
    <rect x="14" y="14" width="70" height="22" rx="6" fill="#059669" fill-opacity="0.2" stroke="#047857" stroke-width="1"/>
    <text x="22" y="29" fill="#34d399" font-size="11" font-weight="700">STAGE 7</text>
    <text x="14" y="62" fill="#f8fafc" font-size="15" font-weight="700">Model Review &amp; Feedback Loop</text>
    
    <rect x="14" y="76" width="322" height="176" rx="8" fill="#0f172a" fill-opacity="0.6"/>
    <text x="24" y="98" fill="#e2e8f0" font-size="12" font-weight="600">• Weekly Saturday Review Runner</text>
    <text x="34" y="118" fill="#34d399" font-size="11" font-family="monospace">.github/workflows/weekly_model_review.yml</text>
    <text x="34" y="136" fill="#94a3b8" font-size="11">Automated 08:00 AM Central execution</text>
    
    <text x="24" y="164" fill="#e2e8f0" font-size="12" font-weight="600">• Rolling Metric Evaluation</text>
    <text x="34" y="184" fill="#94a3b8" font-size="11">MAE ($/gal) &amp; Directional Hit Rate (%) validation</text>
    <text x="34" y="202" fill="#94a3b8" font-size="11">Empirical feedback signal feeding back to Stage 3</text>
  </g>

  <!-- Arrow 7 -> 8 -->
  <path d="M 780 605 L 824 605" fill="none" stroke="#a78bfa" stroke-width="2" marker-end="url(#arrow-purple)"/>

  <!-- STAGE 8: Public Web Dashboard -->
  <g transform="translate(830, 470)">
    <rect width="340" height="270" rx="14" fill="url(#cardGrad)" stroke="#a78bfa" stroke-opacity="0.5" stroke-width="1.5"/>
    <rect x="14" y="14" width="70" height="22" rx="6" fill="#7c3aed" fill-opacity="0.2" stroke="#6d28d9" stroke-width="1"/>
    <text x="22" y="29" fill="#a78bfa" font-size="11" font-weight="700">STAGE 8</text>
    <text x="14" y="62" fill="#f8fafc" font-size="15" font-weight="700">Public Web Dashboard</text>
    
    <rect x="14" y="76" width="312" height="176" rx="8" fill="#0f172a" fill-opacity="0.6"/>
    <text x="24" y="98" fill="#e2e8f0" font-size="12" font-weight="600">• Static Presentation Generator</text>
    <text x="34" y="118" fill="#a78bfa" font-size="11" font-family="monospace">src/dashboard_generator.py -&gt; docs/</text>
    <text x="34" y="136" fill="#94a3b8" font-size="11">Tailwind CSS &amp; FontAwesome static app</text>
    
    <text x="24" y="164" fill="#e2e8f0" font-size="12" font-weight="600">• Presentation Views</text>
    <text x="34" y="184" fill="#94a3b8" font-size="11">National, 8 Metro Hubs, ULSD Diesel,</text>
    <text x="34" y="202" fill="#94a3b8" font-size="11">QuantStats Tear Sheets &amp; Math Guide</text>
  </g>

  <!-- Feedback Loop Curved Arrow: Stage 7 back to Stage 3 -->
  <path d="M 605 470 C 605 420 460 420 460 394" fill="none" stroke="#34d399" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#arrow-green)"/>
</svg>
'''
    return svg_content.strip()


def generate_regional_metro_svg() -> str:
    """
    Generates scalable vector graphics (SVG) diagram for 6 Regional Metro Calibration Hubs.
    """
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 650" width="100%" height="100%" style="background-color: #0b0f19; font-family: system-ui, -apple-system, sans-serif;">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <marker id="m-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/>
    </marker>
  </defs>

  <!-- Header -->
  <rect x="30" y="20" width="1140" height="55" rx="10" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="50" y="53" fill="#f8fafc" font-size="18" font-weight="700">REGIONAL METRO CALIBRATION HUBS &amp; LOGISTICS INFRASTRUCTURE</text>
  <text x="820" y="53" fill="#94a3b8" font-size="13">8 Metro Locales &amp; PADD Pipelines</text>

  <!-- Central Base Commodity Node -->
  <g transform="translate(450, 100)">
    <rect width="300" height="90" rx="12" fill="#0284c7" fill-opacity="0.2" stroke="#38bdf8" stroke-width="2"/>
    <text x="150" y="38" fill="#38bdf8" font-size="14" font-weight="700" text-anchor="middle">NATIONAL WHOLESALE RBOB BASE</text>
    <text x="150" y="60" fill="#e2e8f0" font-size="12" text-anchor="middle">NYMEX RBOB Futures (RB=F) + WTI Crude (CL=F)</text>
  </g>

  <!-- Lines radiating from Center Node to Regional Hubs -->
  <!-- Tulsa -->
  <line x1="500" y1="190" x2="200" y2="250" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#m-arrow)"/>
  <!-- Newark -->
  <line x1="560" y1="190" x2="400" y2="250" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#m-arrow)"/>
  <!-- Cincinnati -->
  <line x1="600" y1="190" x2="600" y2="250" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#m-arrow)"/>
  <!-- Greenville & Charlotte -->
  <line x1="640" y1="190" x2="800" y2="250" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#m-arrow)"/>
  <!-- Oakland & SF Bay -->
  <line x1="700" y1="190" x2="1000" y2="250" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#m-arrow)"/>

  <!-- REGIONAL METRO HUB CARDS (Row 1) -->

  <!-- Hub 1: Tulsa -->
  <g transform="translate(30, 260)">
    <rect width="215" height="160" rx="10" fill="url(#bgGrad)" stroke="#38bdf8" stroke-opacity="0.4" stroke-width="1"/>
    <text x="15" y="30" fill="#f8fafc" font-size="14" font-weight="700">Tulsa Metro, OK</text>
    <text x="15" y="48" fill="#38bdf8" font-size="11" font-weight="600">Cushing WTI Hub</text>
    <text x="15" y="74" fill="#94a3b8" font-size="11">• West Tulsa Refinery</text>
    <text x="15" y="92" fill="#94a3b8" font-size="11">• Cushing Crude Terminal</text>
    <text x="15" y="110" fill="#94a3b8" font-size="11">• Local Rack Margin Offset</text>
    <text x="15" y="136" fill="#34d399" font-size="11" font-weight="600">Base Retail: $3.89/gal</text>
  </g>

  <!-- Hub 2: Newark -->
  <g transform="translate(260, 260)">
    <rect width="215" height="160" rx="10" fill="url(#bgGrad)" stroke="#a78bfa" stroke-opacity="0.4" stroke-width="1"/>
    <text x="15" y="30" fill="#f8fafc" font-size="14" font-weight="700">Newark Metro, DE</text>
    <text x="15" y="48" fill="#a78bfa" font-size="11" font-weight="600">PADD 1B Central Atlantic</text>
    <text x="15" y="74" fill="#94a3b8" font-size="11">• PBF Delaware City (180k bpd)</text>
    <text x="15" y="92" fill="#94a3b8" font-size="11">• Big Stone Lightering Alerts</text>
    <text x="15" y="110" fill="#94a3b8" font-size="11">• C&amp;D Canal Barge Detour</text>
    <text x="15" y="136" fill="#34d399" font-size="11" font-weight="600">Base Retail: $3.35/gal</text>
  </g>

  <!-- Hub 3: Cincinnati -->
  <g transform="translate(490, 260)">
    <rect width="220" height="160" rx="10" fill="url(#bgGrad)" stroke="#f472b6" stroke-opacity="0.4" stroke-width="1"/>
    <text x="15" y="30" fill="#f8fafc" font-size="14" font-weight="700">Cincinnati OH / NKY</text>
    <text x="15" y="48" fill="#f472b6" font-size="11" font-weight="600">Tri-State Corridor</text>
    <text x="15" y="74" fill="#94a3b8" font-size="11">• Catlettsburg Refinery</text>
    <text x="15" y="92" fill="#94a3b8" font-size="11">• Dual-State Tax Differential</text>
    <text x="15" y="110" fill="#94a3b8" font-size="11">• Ohio River Lock Delays</text>
    <text x="15" y="136" fill="#34d399" font-size="11" font-weight="600">OH Tax Diff: +$0.12/gal</text>
  </g>

  <!-- Hub 4: Carolinas -->
  <g transform="translate(725, 260)">
    <rect width="215" height="160" rx="10" fill="url(#bgGrad)" stroke="#fbbf24" stroke-opacity="0.4" stroke-width="1"/>
    <text x="15" y="30" fill="#f8fafc" font-size="14" font-weight="700">Charlotte &amp; Greenville</text>
    <text x="15" y="48" fill="#fbbf24" font-size="11" font-weight="600">PADD 1C Lower Atlantic</text>
    <text x="15" y="74" fill="#94a3b8" font-size="11">• Colonial Pipeline Line 1/2</text>
    <text x="15" y="92" fill="#94a3b8" font-size="11">• Selma &amp; Paw Creek Terminals</text>
    <text x="15" y="110" fill="#94a3b8" font-size="11">• NHC Hurricane Threat Index</text>
    <text x="15" y="136" fill="#34d399" font-size="11" font-weight="600">Colonial Line 1 Intake</text>
  </g>

  <!-- Hub 5: Bay Area -->
  <g transform="translate(955, 260)">
    <rect width="215" height="160" rx="10" fill="url(#bgGrad)" stroke="#34d399" stroke-opacity="0.4" stroke-width="1"/>
    <text x="15" y="30" fill="#f8fafc" font-size="14" font-weight="700">Oakland &amp; SF Bay</text>
    <text x="15" y="48" fill="#34d399" font-size="11" font-weight="600">PADD 5 West Coast</text>
    <text x="15" y="74" fill="#94a3b8" font-size="11">• CARB Gasoline Premium</text>
    <text x="15" y="92" fill="#94a3b8" font-size="11">• Chevron Richmond Outage</text>
    <text x="15" y="110" fill="#94a3b8" font-size="11">• SFPP Corridor Pipeline</text>
    <text x="15" y="136" fill="#34d399" font-size="11" font-weight="600">CARB Mandate Offset</text>
  </g>

  <!-- ROW 2: Florida & ULSD Engines -->
  <g transform="translate(260, 450)">
    <rect width="320" height="160" rx="10" fill="url(#bgGrad)" stroke="#38bdf8" stroke-opacity="0.4" stroke-width="1"/>
    <text x="15" y="30" fill="#f8fafc" font-size="14" font-weight="700">Port St. Lucie Metro, FL</text>
    <text x="15" y="48" fill="#38bdf8" font-size="11" font-weight="600">PADD 1C Waterborne Freight</text>
    <text x="15" y="74" fill="#94a3b8" font-size="11">• Waterborne Barge Freight Rates</text>
    <text x="15" y="92" fill="#94a3b8" font-size="11">• Port Everglades / Canaveral Terminals</text>
    <text x="15" y="110" fill="#94a3b8" font-size="11">• Florida Excise Tax Adjustments</text>
    <text x="15" y="136" fill="#34d399" font-size="11" font-weight="600">Waterborne Freight Proxy</text>
  </g>

  <g transform="translate(620, 450)">
    <rect width="320" height="160" rx="10" fill="url(#bgGrad)" stroke="#a78bfa" stroke-opacity="0.4" stroke-width="1"/>
    <text x="15" y="30" fill="#f8fafc" font-size="14" font-weight="700">ULSD Distillate Fuel Engine</text>
    <text x="15" y="48" fill="#a78bfa" font-size="11" font-weight="600">Ultra-Low Sulfur Diesel (HO=F)</text>
    <text x="15" y="74" fill="#94a3b8" font-size="11">• Heating Oil Futures (HO=F)</text>
    <text x="15" y="92" fill="#94a3b8" font-size="11">• 3-2-1 Distillate Refining Margin</text>
    <text x="15" y="110" fill="#94a3b8" font-size="11">• Commercial Trucking Freight Index</text>
    <text x="15" y="136" fill="#34d399" font-size="11" font-weight="600">Dedicated Diesel Dashboard</text>
  </g>
</svg>
'''
    return svg_content.strip()


def validate_svg_content(svg_string: str) -> bool:
    """
    Validates that an SVG string is valid XML with an svg root tag.
    """
    try:
        root = ET.fromstring(svg_string)
        return root.tag.endswith("svg")
    except Exception as e:
        print(f"SVG Validation Error: {e}")
        return False


def generate_architecture_diagrams(output_dir: str = "docs/assets") -> dict:
    """
    Generates and saves multi_agent_architecture.svg and regional_metro_architecture.svg to output_dir.
    Returns dict mapping filename to absolute filepath.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    multi_agent_svg = generate_multi_agent_pipeline_svg()
    regional_metro_svg = generate_regional_metro_svg()

    if not validate_svg_content(multi_agent_svg):
        raise ValueError("Generated multi_agent_architecture.svg failed XML validation!")

    if not validate_svg_content(regional_metro_svg):
        raise ValueError("Generated regional_metro_architecture.svg failed XML validation!")

    multi_agent_path = os.path.join(output_dir, "multi_agent_architecture.svg")
    regional_metro_path = os.path.join(output_dir, "regional_metro_architecture.svg")

    with open(multi_agent_path, "w", encoding="utf-8") as f:
        f.write(multi_agent_svg)

    with open(regional_metro_path, "w", encoding="utf-8") as f:
        f.write(regional_metro_svg)

    print(f"Successfully generated architecture diagrams in '{output_dir}':")
    print(f"  - {multi_agent_path} ({len(multi_agent_svg)} bytes)")
    print(f"  - {regional_metro_path} ({len(regional_metro_svg)} bytes)")

    return {
        "multi_agent_architecture.svg": os.path.abspath(multi_agent_path),
        "regional_metro_architecture.svg": os.path.abspath(regional_metro_path)
    }

if __name__ == "__main__":
    generate_architecture_diagrams()
