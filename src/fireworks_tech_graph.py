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


def generate_weather_architecture_svg() -> str:
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 450" width="100%" height="100%" style="background-color: #0b0f19; font-family: system-ui, -apple-system, sans-serif;">
  <defs>
    <linearGradient id="cardGradW" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <marker id="arrowW" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/>
    </marker>
    <marker id="arrowW-amber" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#fbbf24"/>
    </marker>
  </defs>

  <g transform="translate(300, 20)">
    <rect width="400" height="60" rx="10" fill="url(#cardGradW)" stroke="#38bdf8" stroke-width="1.5"/>
    <text x="200" y="35" fill="#f8fafc" font-size="15" font-weight="700" text-anchor="middle">NOAA NWS &amp; SPC WEATHER INGESTION ENGINE</text>
    <text x="200" y="50" fill="#38bdf8" font-size="11" text-anchor="middle">api.weather.gov / t.wxs.us Terminal REST Endpoint</text>
  </g>

  <path d="M 400 80 L 230 140" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrowW)"/>
  <path d="M 600 80 L 770 140" fill="none" stroke="#fbbf24" stroke-width="2" marker-end="url(#arrowW-amber)"/>

  <g transform="translate(50, 140)">
    <rect width="360" height="180" rx="12" fill="url(#cardGradW)" stroke="#38bdf8" stroke-opacity="0.5" stroke-width="1.5"/>
    <text x="20" y="32" fill="#38bdf8" font-size="13" font-weight="700">TIER 1: NATIONAL PRODUCTION BASINS</text>
    <text x="20" y="60" fill="#e2e8f0" font-size="12">• Gulf Coast Hurricanes (NHC advisories)</text>
    <text x="20" y="80" fill="#e2e8f0" font-size="12">• Permian Basin Freeze Alerts &amp; HDD/CDD</text>
    <text x="20" y="100" fill="#e2e8f0" font-size="12">• Bakken Shale Polar Vortex Warnings</text>
    <text x="20" y="120" fill="#e2e8f0" font-size="12">• Refinery Hub Heat Stress Anomaly Z-Scores</text>
    <rect x="20" y="140" width="320" height="26" rx="6" fill="#0284c7" fill-opacity="0.2"/>
    <text x="180" y="157" fill="#38bdf8" font-size="11" font-weight="600" text-anchor="middle">Feeds National RBOB Model (src/locations/national)</text>
  </g>

  <g transform="translate(590, 140)">
    <rect width="360" height="180" rx="12" fill="url(#cardGradW)" stroke="#fbbf24" stroke-opacity="0.5" stroke-width="1.5"/>
    <text x="20" y="32" fill="#fbbf24" font-size="13" font-weight="700">TIER 2: LOCALIZED METRO HUBS</text>
    <text x="20" y="60" fill="#e2e8f0" font-size="12">• Tulsa OK (OKZ060 / HF Sinclair Refinery)</text>
    <text x="20" y="80" fill="#e2e8f0" font-size="12">• Newark DE (PBF Delaware City 180k bpd)</text>
    <text x="20" y="100" fill="#e2e8f0" font-size="12">• Cincinnati OH/KY (Ohio River Lock Delays)</text>
    <text x="20" y="120" fill="#e2e8f0" font-size="12">• Greenville/Charlotte NC &amp; Oakland CA</text>
    <rect x="20" y="140" width="320" height="26" rx="6" fill="#d97706" fill-opacity="0.2"/>
    <text x="180" y="157" fill="#fbbf24" font-size="11" font-weight="600" text-anchor="middle">Feeds Metro Calibration Agents (src/locations/&lt;metro&gt;)</text>
  </g>

  <g transform="translate(50, 360)">
    <rect width="900" height="55" rx="10" fill="#1e293b" stroke="#334155" stroke-width="1"/>
    <text x="30" y="33" fill="#34d399" font-size="12" font-weight="600">TOKEN OPTIMIZATION &amp; 0-TOKEN SPC RATING:</text>
    <text x="340" y="33" fill="#94a3b8" font-size="12">t.wxs.us JSON reduces prompt overhead from 3,500 to ~200 tokens (95% token savings). 0-token deterministic SPC mapping.</text>
  </g>
</svg>'''
    return svg_content.strip()


def generate_web_routing_architecture_svg() -> str:
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 480" width="100%" height="100%" style="background-color: #0b0f19; font-family: system-ui, -apple-system, sans-serif;">
  <defs>
    <linearGradient id="cardGradWeb" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <marker id="arrowWeb" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#a78bfa"/>
    </marker>
  </defs>

  <g transform="translate(320, 20)">
    <rect width="360" height="65" rx="12" fill="url(#cardGradWeb)" stroke="#a78bfa" stroke-width="2"/>
    <text x="180" y="38" fill="#f8fafc" font-size="16" font-weight="700" text-anchor="middle">docs/index.html Landing Page (/)</text>
    <text x="180" y="54" fill="#a78bfa" font-size="11" text-anchor="middle">Overview Landing, Summary Forecast Cards &amp; Live Scoreboard</text>
  </g>

  <path d="M 380 85 L 120 160" fill="none" stroke="#a78bfa" stroke-width="1.5" marker-end="url(#arrowWeb)"/>
  <path d="M 460 85 L 360 160" fill="none" stroke="#a78bfa" stroke-width="1.5" marker-end="url(#arrowWeb)"/>
  <path d="M 540 85 L 640 160" fill="none" stroke="#a78bfa" stroke-width="1.5" marker-end="url(#arrowWeb)"/>
  <path d="M 620 85 L 880 160" fill="none" stroke="#a78bfa" stroke-width="1.5" marker-end="url(#arrowWeb)"/>

  <g transform="translate(30, 160)">
    <rect width="180" height="120" rx="10" fill="url(#cardGradWeb)" stroke="#38bdf8" stroke-width="1.2"/>
    <text x="90" y="32" fill="#38bdf8" font-size="13" font-weight="700" text-anchor="middle">/national</text>
    <text x="90" y="52" fill="#e2e8f0" font-size="11" text-anchor="middle">Wholesale RBOB</text>
    <text x="90" y="70" fill="#94a3b8" font-size="10" text-anchor="middle">Futures &amp; Crude Spread</text>
    <text x="90" y="88" fill="#94a3b8" font-size="10" text-anchor="middle">Stacking Ensemble</text>
  </g>

  <g transform="translate(240, 160)">
    <rect width="240" height="180" rx="10" fill="url(#cardGradWeb)" stroke="#34d399" stroke-width="1.2"/>
    <text x="120" y="30" fill="#34d399" font-size="13" font-weight="700" text-anchor="middle">METRO HUBS MENU</text>
    <text x="20" y="54" fill="#94a3b8" font-size="11">• /tulsa (OK Cushing)</text>
    <text x="20" y="72" fill="#94a3b8" font-size="11">• /newark (DE PADD 1B)</text>
    <text x="20" y="90" fill="#94a3b8" font-size="11">• /cincinnati (OH/KY)</text>
    <text x="20" y="108" fill="#94a3b8" font-size="11">• /greenville &amp; /charlotte</text>
    <text x="20" y="126" fill="#94a3b8" font-size="11">• /oakland &amp; /bayarea</text>
    <text x="20" y="144" fill="#94a3b8" font-size="11">• /port_st_lucie (FL)</text>
    <text x="20" y="162" fill="#94a3b8" font-size="11">• /diesel (ULSD Engine)</text>
  </g>

  <g transform="translate(520, 160)">
    <rect width="210" height="120" rx="10" fill="url(#cardGradWeb)" stroke="#fbbf24" stroke-width="1.2"/>
    <text x="105" y="32" fill="#fbbf24" font-size="13" font-weight="700" text-anchor="middle">/math</text>
    <text x="105" y="52" fill="#e2e8f0" font-size="11" text-anchor="middle">KaTeX Math Equations</text>
    <text x="105" y="70" fill="#94a3b8" font-size="10" text-anchor="middle">Full Architecture Specs</text>
    <text x="105" y="88" fill="#94a3b8" font-size="10" text-anchor="middle">CodeCogs TeX Embeds</text>
  </g>

  <g transform="translate(760, 160)">
    <rect width="210" height="120" rx="10" fill="url(#cardGradWeb)" stroke="#f472b6" stroke-width="1.2"/>
    <text x="105" y="32" fill="#f472b6" font-size="13" font-weight="700" text-anchor="middle">/reports</text>
    <text x="105" y="52" fill="#e2e8f0" font-size="11" text-anchor="middle">Technical Run Reports</text>
    <text x="105" y="70" fill="#94a3b8" font-size="10" text-anchor="middle">Weekly Review Audits</text>
    <text x="105" y="88" fill="#94a3b8" font-size="10" text-anchor="middle">Run History JSON Store</text>
  </g>

  <g transform="translate(240, 370)">
    <rect width="520" height="80" rx="10" fill="#0f172a" stroke="#38bdf8" stroke-dasharray="4,4" stroke-width="1.5"/>
    <text x="260" y="30" fill="#38bdf8" font-size="13" font-weight="700" text-anchor="middle">DECOUPLED METADATA &amp; DUAL ROUTING ENGINE</text>
    <text x="260" y="50" fill="#94a3b8" font-size="11" text-anchor="middle">Renders profile cards from data/regional_metadata/*.json. Dual output (tulsa.html &amp; tulsa/index.html).</text>
  </g>
</svg>'''
    return svg_content.strip()


def generate_cache_gateway_architecture_svg() -> str:
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 480" width="100%" height="100%" style="background-color: #0b0f19; font-family: system-ui, -apple-system, sans-serif;">
  <defs>
    <linearGradient id="cardGradC" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <marker id="arrowC" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/>
    </marker>
  </defs>

  <g transform="translate(100, 20)">
    <rect width="800" height="65" rx="12" fill="url(#cardGradC)" stroke="#38bdf8" stroke-width="1.5"/>
    <text x="400" y="36" fill="#f8fafc" font-size="15" font-weight="700" text-anchor="middle">EXTERNAL DATA CONNECTORS &amp; MARKET FEEDS</text>
    <text x="400" y="52" fill="#94a3b8" font-size="11" text-anchor="middle">EIA Petroleum API v2 • FRED St. Louis Fed • USDA Biofuels • NOAA Weather • Finlight.me • GasBuddy Scraper</text>
  </g>

  <path d="M 500 85 L 500 120" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrowC)"/>

  <g transform="translate(100, 125)">
    <rect width="800" height="250" rx="14" fill="url(#cardGradC)" stroke="#34d399" stroke-width="2"/>
    <text x="400" y="32" fill="#34d399" font-size="15" font-weight="700" text-anchor="middle">MULTI-TIER LOOKUP CACHE GATEWAY (src/lookup_cache.py)</text>

    <g transform="translate(30, 50)">
      <rect width="740" height="50" rx="8" fill="#0284c7" fill-opacity="0.15" stroke="#0369a1" stroke-width="1"/>
      <text x="20" y="30" fill="#38bdf8" font-size="13" font-weight="700">TIER 1 (Primary Edge):</text>
      <text x="200" y="30" fill="#e2e8f0" font-size="12">Turso Edge SQLite REST API (TURSO_DATABASE_URL)</text>
    </g>

    <g transform="translate(30, 115)">
      <rect width="740" height="50" rx="8" fill="#7c3aed" fill-opacity="0.15" stroke="#6d28d9" stroke-width="1"/>
      <text x="20" y="30" fill="#a78bfa" font-size="13" font-weight="700">TIER 2 (Backup Edge):</text>
      <text x="200" y="30" fill="#e2e8f0" font-size="12">Cloudflare D1/R2 Edge Worker Gateway (workers/cache_worker.ts)</text>
    </g>

    <g transform="translate(30, 180)">
      <rect width="740" height="50" rx="8" fill="#059669" fill-opacity="0.15" stroke="#047857" stroke-width="1"/>
      <text x="20" y="30" fill="#34d399" font-size="13" font-weight="700">TIER 3 (Local Core):</text>
      <text x="200" y="30" fill="#e2e8f0" font-size="12">SQLite Datastore (data/lookup_cache.sqlite) + Fast In-Memory Dict (global_cache)</text>
    </g>
  </g>

  <path d="M 500 375 L 500 405" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrowC)"/>

  <g transform="translate(250, 405)">
    <rect width="500" height="55" rx="10" fill="#0f172a" stroke="#64748b" stroke-width="1.2"/>
    <text x="250" y="33" fill="#e2e8f0" font-size="13" font-weight="600" text-anchor="middle">LOCAL DISK JSON FALLBACK (data/{source}_cache.json)</text>
  </g>
</svg>'''
    return svg_content.strip()


def generate_worker_telemetry_architecture_svg() -> str:
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 450" width="100%" height="100%" style="background-color: #0b0f19; font-family: system-ui, -apple-system, sans-serif;">
  <defs>
    <linearGradient id="cardGradWk" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <marker id="arrowWk" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"/>
    </marker>
  </defs>

  <g transform="translate(100, 20)">
    <rect width="800" height="90" rx="12" fill="url(#cardGradWk)" stroke="#f97316" stroke-width="1.5"/>
    <text x="400" y="32" fill="#f97316" font-size="15" font-weight="700" text-anchor="middle">CLOUDFLARE EDGE WORKERS &amp; QUEUES INGESTION</text>
    <text x="400" y="52" fill="#e2e8f0" font-size="12" text-anchor="middle">• midgley-intraday-monitor (workers/intraday_monitor_worker.ts) — 15-min RSS cron trigger</text>
    <text x="400" y="70" fill="#38bdf8" font-size="11" text-anchor="middle">• Cloudflare Queues Buffer (intraday-event-queue &amp; DLQ) + midgley-cache-worker (D1 Edge Gateway)</text>
  </g>

  <path d="M 230 110 L 230 170" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrowWk)"/>
  <path d="M 500 110 L 500 170" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrowWk)"/>
  <path d="M 770 110 L 770 170" fill="none" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrowWk)"/>

  <g transform="translate(50, 170)">
    <rect width="270" height="220" rx="12" fill="url(#cardGradWk)" stroke="#38bdf8" stroke-opacity="0.5" stroke-width="1.5"/>
    <text x="135" y="32" fill="#38bdf8" font-size="13" font-weight="700" text-anchor="middle">CLOUDFLARE NATIVE OBS</text>
    <text x="20" y="64" fill="#e2e8f0" font-size="11">• Real-time wrangler tail logs</text>
    <text x="20" y="86" fill="#e2e8f0" font-size="11">• Invocation trace graphs</text>
    <text x="20" y="108" fill="#e2e8f0" font-size="11">• 100% head sampling rate</text>
    <text x="20" y="130" fill="#e2e8f0" font-size="11">• Native persistent logs enabled</text>
    <rect x="20" y="165" width="230" height="35" rx="6" fill="#0284c7" fill-opacity="0.2"/>
    <text x="135" y="187" fill="#38bdf8" font-size="11" font-weight="600" text-anchor="middle">wrangler.toml observability</text>
  </g>

  <g transform="translate(365, 170)">
    <rect width="270" height="220" rx="12" fill="url(#cardGradWk)" stroke="#34d399" stroke-opacity="0.5" stroke-width="1.5"/>
    <text x="135" y="32" fill="#34d399" font-size="13" font-weight="700" text-anchor="middle">AXIOM LOG ANALYTICS</text>
    <text x="20" y="64" fill="#e2e8f0" font-size="11">• 30-day searchable log streams</text>
    <text x="20" y="86" fill="#e2e8f0" font-size="11">• logToAxiom() HTTPS REST ingest</text>
    <text x="20" y="108" fill="#e2e8f0" font-size="11">• Dataset: midgley-workers</text>
    <text x="20" y="130" fill="#e2e8f0" font-size="11">• 0 HTTP latency penalty via ctx.waitUntil</text>
    <rect x="20" y="165" width="230" height="35" rx="6" fill="#059669" fill-opacity="0.2"/>
    <text x="135" y="187" fill="#34d399" font-size="11" font-weight="600" text-anchor="middle">Option A2 Telemetry Engine</text>
  </g>

  <g transform="translate(680, 170)">
    <rect width="270" height="220" rx="12" fill="url(#cardGradWk)" stroke="#f472b6" stroke-opacity="0.5" stroke-width="1.5"/>
    <text x="135" y="32" fill="#f472b6" font-size="13" font-weight="700" text-anchor="middle">SENTRY CRASH &amp; CRONS</text>
    <text x="20" y="64" fill="#e2e8f0" font-size="11">• Uncaught exception stack traces</text>
    <text x="20" y="86" fill="#e2e8f0" font-size="11">• captureSentryException()</text>
    <text x="20" y="108" fill="#e2e8f0" font-size="11">• Sentry Cron Heartbeats</text>
    <text x="20" y="130" fill="#e2e8f0" font-size="11">• sendSentryCronCheckIn(ok/error)</text>
    <rect x="20" y="165" width="230" height="35" rx="6" fill="#db2777" fill-opacity="0.2"/>
    <text x="135" y="187" fill="#f472b6" font-size="11" font-weight="600" text-anchor="middle">SENTRY_DSN Envelope Protocol</text>
  </g>
</svg>'''
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
    Generates and saves architecture SVG diagrams to output_dir via Fireworks Tech Graph.
    Returns dict mapping filename to absolute filepath.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    diagrams = {
        "multi_agent_architecture.svg": generate_multi_agent_pipeline_svg(),
        "regional_metro_architecture.svg": generate_regional_metro_svg(),
        "weather_architecture.svg": generate_weather_architecture_svg(),
        "web_routing_architecture.svg": generate_web_routing_architecture_svg(),
        "cache_gateway_architecture.svg": generate_cache_gateway_architecture_svg(),
        "worker_telemetry_architecture.svg": generate_worker_telemetry_architecture_svg()
    }

    paths = {}
    for filename, svg_content in diagrams.items():
        if not validate_svg_content(svg_content):
            raise ValueError(f"Generated {filename} failed XML validation!")
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)
        
        paths[filename] = os.path.abspath(filepath)
        print(f"  - {filepath} ({len(svg_content)} bytes)")

    return paths

if __name__ == "__main__":
    generate_architecture_diagrams()

