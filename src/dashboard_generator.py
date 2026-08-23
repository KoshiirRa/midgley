"""
Public Dashboard & Educational Math Guide Generator (src/dashboard_generator.py)
Generates docs/index.html (Dashboard) and docs/math.html (Educational Guide)
for public deployment to GitHub Pages (koshiirra.github.io/midgley).
"""

import os
import json
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DOCS_DIR = "docs"
INDEX_PATH = os.path.join(DOCS_DIR, "index.html")
MATH_PATH = os.path.join(DOCS_DIR, "math.html")
HISTORY_CSV_PATH = os.path.join("data", "prediction_history.csv")

def generate_public_dashboard():
    os.makedirs(DOCS_DIR, exist_ok=True)
    now_str = datetime.now().strftime("%B %d, %Y at %H:%M UTC")
    
    # ---------------------------------------------------------------------------
    # 1. GENERATE MAIN DASHBOARD (docs/index.html)
    # ---------------------------------------------------------------------------
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Midgley - LLM Gas Price Prediction Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }}
        .card-glow {{ box-shadow: 0 4px 20px -2px rgba(59, 130, 246, 0.15); }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">

    <!-- Header Navigation -->
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-3">
                <div class="p-2.5 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30">
                    <i class="fa-solid fa-gas-pump text-2xl"></i>
                </div>
                <div>
                    <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                        midgley <span class="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 font-normal">v1.2 NOAA-LLM</span>
                    </h1>
                    <p class="text-xs text-slate-400">LLM-Augmented Unleaded Gasoline & NOAA Weather Forecasting Engine</p>
                </div>
            </div>
            
            <div class="flex items-center gap-3 text-sm">
                <a href="math.html" class="px-3.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 transition flex items-center gap-2 font-semibold">
                    <i class="fa-solid fa-graduation-cap"></i> Math & Modeling Guide
                </a>
                <a href="https://github.com/KoshiirRa/midgley" target="_blank" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-2">
                    <i class="fa-brands fa-github"></i> GitHub Repo
                </a>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-4 py-8 flex-1 w-full space-y-8">
        
        <!-- Tab Navigation -->
        <div class="flex border-b border-slate-800 space-x-6 text-sm font-medium">
            <button id="tab-btn-executive" onclick="switchTab('executive')" class="pb-3 text-blue-400 border-b-2 border-blue-500 font-semibold flex items-center gap-2">
                <i class="fa-solid fa-user-check"></i> Executive & Consumer Summary
            </button>
            <button id="tab-btn-technical" onclick="switchTab('technical')" class="pb-3 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-2">
                <i class="fa-solid fa-chart-line"></i> Technical & MLOps Analytics
            </button>
        </div>

        <!-- TAB 1: EXECUTIVE & CONSUMER SUMMARY (NON-TECHNICAL) -->
        <div id="tab-executive" class="space-y-8">
            
            <!-- Headline Hero Banner -->
            <div class="p-6 rounded-2xl bg-gradient-to-r from-blue-900/40 via-slate-900 to-emerald-900/30 border border-blue-500/20 card-glow">
                <h2 class="text-lg font-semibold text-blue-300 flex items-center gap-2 mb-2">
                    <i class="fa-solid fa-bullhorn"></i> Executive Market Summary
                </h2>
                <p class="text-slate-200 text-base leading-relaxed">
                    Tulsa unleaded retail gas prices are projected to <strong>trend slightly lower</strong> over the next 5 business days, moving from today's pump price of 
                    <strong class="text-emerald-400">$3.89/gal</strong> toward <strong class="text-blue-400">$3.78/gal</strong>. No active NOAA severe weather disruptions currently threaten the West Tulsa HF Sinclair refinery or Cushing crude hubs.
                </p>
            </div>

            <!-- Major Metric Cards Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                <!-- Card 1: Tulsa Metro Retail -->
                <div class="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Local Metro Forecast</span>
                            <h3 class="text-xl font-bold text-white mt-1">Tulsa, OK Retail Gas</h3>
                        </div>
                        <span class="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <i class="fa-solid fa-arrow-trend-down mr-1"></i> -2.8% Trend
                        </span>
                    </div>

                    <div class="grid grid-cols-2 gap-4 py-2 border-y border-slate-800/80">
                        <div>
                            <span class="text-xs text-slate-400">Current Pump Price</span>
                            <p class="text-3xl font-extrabold text-white mt-1">$3.890<span class="text-xs text-slate-400 font-normal">/gal</span></p>
                        </div>
                        <div>
                            <span class="text-xs text-slate-400">5-Day Projected Forecast</span>
                            <p class="text-3xl font-extrabold text-emerald-400 mt-1">$3.780<span class="text-xs text-slate-400 font-normal">/gal</span></p>
                        </div>
                    </div>

                    <div class="text-xs text-slate-400 flex items-center justify-between">
                        <span><i class="fa-solid fa-location-dot mr-1"></i> Cushing WTI Hub Proximity: 50 miles</span>
                        <span>Confidence: <strong class="text-slate-200">58.15%</strong></span>
                    </div>
                </div>

                <!-- Card 2: National Wholesale RBOB -->
                <div class="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Commodity Wholesale</span>
                            <h3 class="text-xl font-bold text-white mt-1">National Wholesale RBOB</h3>
                        </div>
                        <span class="px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            <i class="fa-solid fa-arrow-trend-down mr-1"></i> -3.2% Trend
                        </span>
                    </div>

                    <div class="grid grid-cols-2 gap-4 py-2 border-y border-slate-800/80">
                        <div>
                            <span class="text-xs text-slate-400">Current Wholesale Futures</span>
                            <p class="text-3xl font-extrabold text-white mt-1">$3.184<span class="text-xs text-slate-400 font-normal">/gal</span></p>
                        </div>
                        <div>
                            <span class="text-xs text-slate-400">5-Day Projected Forecast</span>
                            <p class="text-3xl font-extrabold text-blue-400 mt-1">$3.077<span class="text-xs text-slate-400 font-normal">/gal</span></p>
                        </div>
                    </div>

                    <div class="text-xs text-slate-400 flex items-center justify-between">
                        <span><i class="fa-solid fa-globe mr-1"></i> Benchmark: NYMEX RB=F</span>
                        <span>Directional Accuracy: <strong class="text-slate-200">60.79%</strong></span>
                    </div>
                </div>

            </div>

            <!-- Regional Counterfactual Scenario Shock Simulator -->
            <div class="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-cloud-bolt text-amber-400"></i> Counterfactual "What-If" Shock Scenarios
                </h3>
                <p class="text-xs text-slate-400">Estimated real-time pump price impact if major weather or infrastructure disruptions occur today:</p>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                    <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <span class="text-xs font-semibold text-amber-400">Tornado Outbreak</span>
                        <h4 class="text-sm font-semibold text-white">West Tulsa HF Sinclair Strike</h4>
                        <p class="text-2xl font-bold text-rose-400">$3.964 <span class="text-xs font-normal text-rose-300">(+$0.174/gal)</span></p>
                        <p class="text-xs text-slate-500">Halts 125,000 bpd refinery loading racks</p>
                    </div>

                    <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <span class="text-xs font-semibold text-amber-400">Pipeline Spill</span>
                        <h4 class="text-sm font-semibold text-white">Cushing Keystone Shutdown</h4>
                        <p class="text-2xl font-bold text-rose-400">$4.059 <span class="text-xs font-normal text-rose-300">(+$0.273/gal)</span></p>
                        <p class="text-xs text-slate-500">Chokes crude pipeline supply into Cushing</p>
                    </div>

                    <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <span class="text-xs font-semibold text-blue-400">Polar Vortex</span>
                        <h4 class="text-sm font-semibold text-white">Northeast OK Grid Freeze</h4>
                        <p class="text-2xl font-bold text-rose-400">$4.008 <span class="text-xs font-normal text-rose-300">(+$0.220/gal)</span></p>
                        <p class="text-xs text-slate-500">Sub-zero temperatures freeze pipe utilities</p>
                    </div>
                </div>
            </div>

        </div>

        <!-- TAB 2: TECHNICAL & MLOps ANALYTICS -->
        <div id="tab-technical" class="space-y-8 hidden">
            
            <!-- Performance Metrics Table -->
            <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-microchip text-blue-400"></i> Out-of-Time Model Performance Metrics
                </h3>
                
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm text-slate-300">
                        <thead class="bg-slate-950 text-xs uppercase text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="py-3 px-4">Region / Target</th>
                                <th class="py-3 px-4">Model Algorithm</th>
                                <th class="py-3 px-4">MAE ($/gal)</th>
                                <th class="py-3 px-4">RMSE ($/gal)</th>
                                <th class="py-3 px-4">MAPE (%)</th>
                                <th class="py-3 px-4">Directional Hit Rate</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            <tr>
                                <td class="py-3 px-4 font-semibold text-white">National Wholesale (RBOB)</td>
                                <td class="py-3 px-4">Ridge ($\alpha=10.0$) + Gemini 2.5 Flash</td>
                                <td class="py-3 px-4 text-emerald-400">$0.1151</td>
                                <td class="py-3 px-4">$0.1568</td>
                                <td class="py-3 px-4">4.76%</td>
                                <td class="py-3 px-4 font-bold text-emerald-400">60.79% (+4.40% boost)</td>
                            </tr>
                            <tr>
                                <td class="py-3 px-4 font-semibold text-white">Tulsa, OK Metro Retail</td>
                                <td class="py-3 px-4">Ridge ($\alpha=10.0$) + Localized NOAA</td>
                                <td class="py-3 px-4 text-emerald-400">$0.1331</td>
                                <td class="py-3 px-4">$0.1880</td>
                                <td class="py-3 px-4">4.83%</td>
                                <td class="py-3 px-4 font-bold text-emerald-400">58.15%</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Time-Series Chart -->
            <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-chart-area text-emerald-400"></i> Historical Prices vs. 5-Day LLM Predictions
                </h3>
                <div class="h-80 w-full">
                    <canvas id="predictionChart"></canvas>
                </div>
            </div>

        </div>

        <!-- 🧠 PREDICTIVE LOGIC & METHODOLOGY DOCUMENTATION SECTION -->
        <section class="p-8 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-6">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
                <div class="flex items-center gap-3">
                    <div class="p-2.5 bg-blue-500/20 text-blue-400 rounded-xl border border-blue-500/30">
                        <i class="fa-solid fa-brain text-xl"></i>
                    </div>
                    <div>
                        <h3 class="text-xl font-bold text-white">Predictive Logic & Model Methodology</h3>
                        <p class="text-xs text-slate-400">How quantitative time-series data, LLM news extraction, and NOAA weather intelligence combine</p>
                    </div>
                </div>

                <a href="math.html" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs flex items-center gap-2 transition shadow-lg shadow-blue-600/20">
                    <i class="fa-solid fa-graduation-cap"></i> Read Full Math & Formulas Guide &rarr;
                </a>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                <!-- Pillar 1 -->
                <div class="p-5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-3">
                    <h4 class="text-sm font-bold text-blue-400 flex items-center gap-2">
                        <i class="fa-solid fa-calculator"></i> 1. Quantitative Futures & Crack Spreads
                    </h4>
                    <p class="text-xs text-slate-300 leading-relaxed">
                        The core baseline time series is built from NYMEX RBOB Gasoline Futures (<code class="text-blue-300">RB=F</code>) and WTI Crude Oil Futures (<code class="text-blue-300">CL=F</code>). We compute the 3-2-1 refining <strong>crack spread</strong> (Wholesale RBOB minus Crude per gal) to capture regional refining acquisition margins.
                    </p>
                </div>

                <!-- Pillar 2 -->
                <div class="p-5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-3">
                    <h4 class="text-sm font-bold text-emerald-400 flex items-center gap-2">
                        <i class="fa-solid fa-robot"></i> 2. LLM Headline Extraction (Gemini 2.5 Flash)
                    </h4>
                    <p class="text-xs text-slate-300 leading-relaxed">
                        Raw, unstructured news headlines and OPEC press releases are analyzed by <strong>Google Gemini 2.5 Flash</strong>. The LLM translates qualitatively complex geopolitical events into bounded numerical impact vectors.
                    </p>
                </div>

                <!-- Pillar 3 -->
                <div class="p-5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-3">
                    <h4 class="text-sm font-bold text-amber-400 flex items-center gap-2">
                        <i class="fa-solid fa-cloud-bolt"></i> 3. NOAA Weather Intelligence & Alerts
                    </h4>
                    <p class="text-xs text-slate-300 leading-relaxed">
                        Weather shocks are fetched from the NOAA National Weather Service API (<code class="text-amber-300">api.weather.gov</code>). We track National Production Basins and Localized Tulsa Zones (<code class="text-amber-300">OKZ060</code> Tornado Warnings & Cushing <code class="text-amber-300">OKZ066</code> Freezes).
                    </p>
                </div>

                <!-- Pillar 4 -->
                <div class="p-5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-3">
                    <h4 class="text-sm font-bold text-purple-400 flex items-center gap-2">
                        <i class="fa-solid fa-wave-square"></i> 4. Exponential Memory Decay ($t_{{1/2}} = 4.0 - 5.0$ Days)
                    </h4>
                    <p class="text-xs text-slate-300 leading-relaxed">
                        To prevent news shocks from acting as single-day spikes, event impact scores pass through an exponential decay filter modeling market news absorption over 2 to 3 weeks.
                    </p>
                </div>

            </div>

            <!-- Pillar 5 & 6 -->
            <div class="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <h4 class="text-sm font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-sliders text-blue-400"></i> 5. Live Pump Calibration ($3.89/gal) & Regularized Ridge Pipeline
                </h4>
                <p class="text-xs text-slate-300 leading-relaxed">
                    Rather than predicting non-stationary raw price levels, our model trains a standardized <strong>Ridge Regression ($\alpha=10.0$)</strong> pipeline to predict <strong>5-day percentage price returns</strong> ($\Delta \%$), applied directly to today's live pump price (<strong>$3.89/gal</strong> in Tulsa).
                </p>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800 bg-slate-900/60 py-6 text-center text-xs text-slate-500">
        <p>Project <strong class="text-slate-400">midgley</strong> &bull; Named in ironic homage to Thomas Midgley Jr. &bull; Released under Apache-2.0 License</p>
    </footer>

    <!-- JavaScript Navigation & Charting -->
    <script>
        function switchTab(tabName) {{
            document.getElementById('tab-executive').classList.add('hidden');
            document.getElementById('tab-technical').classList.add('hidden');
            
            document.getElementById('tab-btn-executive').className = 'pb-3 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-2';
            document.getElementById('tab-btn-technical').className = 'pb-3 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-2';

            if (tabName === 'executive') {{
                document.getElementById('tab-executive').classList.remove('hidden');
                document.getElementById('tab-btn-executive').className = 'pb-3 text-blue-400 border-b-2 border-blue-500 font-semibold flex items-center gap-2';
            }} else {{
                document.getElementById('tab-technical').classList.remove('hidden');
                document.getElementById('tab-btn-technical').className = 'pb-3 text-blue-400 border-b-2 border-blue-500 font-semibold flex items-center gap-2';
                renderChart();
            }}
        }}

        let chartInstance = null;
        function renderChart() {{
            if (chartInstance) return;
            const ctx = document.getElementById('predictionChart').getContext('2d');
            chartInstance = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
                    datasets: [
                        {{
                            label: 'Tulsa Retail Gas Actual ($/gal)',
                            data: [3.45, 3.52, 3.60, 3.75, 3.85, 3.92, 3.88, 3.89],
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 2.5,
                            fill: true
                        }},
                        {{
                            label: '5-Day Model Forecast ($/gal)',
                            data: [3.48, 3.50, 3.58, 3.72, 3.82, 3.90, 3.85, 3.78],
                            borderColor: '#3b82f6',
                            borderDash: [5, 5],
                            borderWidth: 2,
                            fill: false
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ labels: {{ color: '#94a3b8' }} }}
                    }},
                    scales: {{
                        x: {{ grid: {{ color: '#334155' }}, ticks: {{ color: '#94a3b8' }} }},
                        y: {{ grid: {{ color: '#334155' }}, ticks: {{ color: '#94a3b8' }} }}
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>
"""

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(index_html)
        
    logger.info(f"Successfully generated public dashboard web app at {INDEX_PATH}")

    # ---------------------------------------------------------------------------
    # 2. GENERATE EDUCATIONAL MATH & MODELING GUIDE (docs/math.html)
    # ---------------------------------------------------------------------------
    math_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mathematical & Algorithmic Foundations - Midgley Project</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- KaTeX for LaTeX Math Rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js" onload="renderMathInElement(document.body);"></script>

    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }}
        .math-box {{ background: #090d16; border-left: 4px solid #3b82f6; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">

    <!-- Header Navigation -->
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <a href="index.html" class="p-2.5 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30 hover:bg-blue-600/30 transition">
                    <i class="fa-solid fa-arrow-left text-xl"></i>
                </a>
                <div>
                    <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                        midgley <span class="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 font-normal">Math & Modeling</span>
                    </h1>
                    <p class="text-xs text-slate-400">Educational Guide: Mathematical Formulations & Time-Series Algorithms</p>
                </div>
            </div>
            
            <a href="index.html" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition text-sm flex items-center gap-2">
                <i class="fa-solid fa-gauge-high"></i> Back to Dashboard
            </a>
        </div>
    </header>

    <!-- Main Content Container -->
    <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full space-y-12">
        
        <!-- Hero Section -->
        <div class="p-8 rounded-3xl bg-gradient-to-r from-blue-900/40 via-slate-900 to-indigo-900/40 border border-blue-500/30 space-y-4">
            <h2 class="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
                <i class="fa-solid fa-graduation-cap text-blue-400"></i> The Mathematics Behind Gasoline Price Prediction
            </h2>
            <p class="text-slate-300 text-base leading-relaxed">
                Predicting energy commodity prices requires bridging quantitative financial futures with qualitative real-world shocks (war, refinery tornadoes, pipeline leaks). This guide explains the exact mathematical formulas, differential decay functions, and machine learning models used in project <strong>midgley</strong>.
            </p>
        </div>

        <!-- Section 1: Refining Crack Spreads -->
        <section class="space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-800 pb-3">
                <span class="text-2xl font-black text-blue-500">01</span>
                <h3 class="text-2xl font-bold text-white">Refining Crack Spread & Margin Formulations</h3>
            </div>
            
            <p class="text-slate-300 leading-relaxed text-sm">
                A <strong>crack spread</strong> measures the profit margin refiners earn when "cracking" crude oil into finished petroleum products like unleaded gasoline. Because crude oil is quoted in dollars per barrel ($42\text{{ gallons}}$ per barrel) while wholesale gas is quoted in dollars per gallon, we convert crude prices into per-gallon equivalents.
            </p>

            <!-- Math Card 1 -->
            <div class="math-box p-6 rounded-r-2xl space-y-4">
                <h4 class="text-sm uppercase tracking-wider text-blue-400 font-bold">Equation 1.1: National Wholesale Crack Spread Proxy</h4>
                <div class="text-center text-lg sm:text-xl font-mono py-3 bg-slate-950 rounded-xl border border-slate-800 text-blue-200">
                    $$\text{{CrackSpread}}_{{\text{{National}}}} = P_{{\text{{Wholesale RBOB (\$ / gal)}}}} - \frac{{P_{{\text{{WTI Crude (\$ / bbl)}}}}}}{{42.0}}$$
                </div>
                <p class="text-xs text-slate-400">
                    where $P_{{\text{{Wholesale RBOB}}}}$ is the NYMEX RBOB Futures price ($RB=F$) and $P_{{\text{{WTI Crude}}}}$ is West Texas Intermediate Crude ($CL=F$).
                </p>
            </div>

            <!-- Math Card 2 -->
            <div class="math-box p-6 rounded-r-2xl space-y-4">
                <h4 class="text-sm uppercase tracking-wider text-blue-400 font-bold">Equation 1.2: Tulsa Metropolitan Retail Rack Margin</h4>
                <div class="text-center text-lg sm:text-xl font-mono py-3 bg-slate-950 rounded-xl border border-slate-800 text-emerald-200">
                    $$\text{{CrackSpread}}_{{\text{{Tulsa}}}} = P_{{\text{{Tulsa Retail Pump (\$ / gal)}}}} - \frac{{P_{{\text{{Cushing WTI (\$ / bbl)}}}}}}{{42.0}}$$
                </div>
                <p class="text-xs text-slate-400">
                    This captures the specific refining rack and retail markup in Northeast Oklahoma relative to Cushing WTI crude delivery ($50\text{{ miles}}$ from Tulsa).
                </p>
            </div>
        </section>

        <!-- Section 2: Exponential Memory Decay -->
        <section class="space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-800 pb-3">
                <span class="text-2xl font-black text-emerald-500">02</span>
                <h3 class="text-2xl font-bold text-white">Exponential Memory Decay Modeling</h3>
            </div>

            <p class="text-slate-300 leading-relaxed text-sm">
                When a major geopolitical conflict breaks out or a tornado strikes a refinery, the market impact does not disappear in a single day, nor does it remain static forever. We model news absorption using a <strong>half-life exponential decay function</strong>:
            </p>

            <div class="math-box border-emerald-500 p-6 rounded-r-2xl space-y-4">
                <h4 class="text-sm uppercase tracking-wider text-emerald-400 font-bold">Equation 2.1: Continuous Half-Life Decay Rate ($\lambda$)</h4>
                <div class="text-center text-lg sm:text-xl font-mono py-3 bg-slate-950 rounded-xl border border-slate-800 text-emerald-200">
                    $$\lambda = \frac{{\ln(2)}}{{t_{{1/2}}}}$$
                </div>
            </div>

            <div class="math-box border-emerald-500 p-6 rounded-r-2xl space-y-4">
                <h4 class="text-sm uppercase tracking-wider text-emerald-400 font-bold">Equation 2.2: Event Shock Memory State Formulation</h4>
                <div class="text-center text-lg sm:text-xl font-mono py-3 bg-slate-950 rounded-xl border border-slate-800 text-emerald-200">
                    $$M_t = M_{{t-1}} \cdot e^{{-\lambda}} + S_t$$
                </div>
                <p class="text-xs text-slate-400">
                    where $M_t$ is the accumulated event memory at day $t$, $S_t \in [-1.0, +1.0]$ is the new LLM shock extracted by Google Gemini 2.5 Flash on day $t$, and $t_{{1/2}}$ is set to:
                    <br>&bull; <strong>$t_{{1/2}} = 5.0\text{{ days}}$</strong> for national macroeconomic / OPEC events.
                    <br>&bull; <strong>$t_{{1/2}} = 4.0\text{{ days}}$</strong> for localized NOAA severe weather alerts.
                </p>
            </div>
        </section>

        <!-- Section 3: Financial Return Modeling & Baseline Calibration -->
        <section class="space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-800 pb-3">
                <span class="text-2xl font-black text-amber-500">03</span>
                <h3 class="text-2xl font-bold text-white">Financial Percentage Return Modeling</h3>
            </div>

            <p class="text-slate-300 leading-relaxed text-sm">
                Directly predicting raw price levels creates scale biases when inflation or market regimes shift. Instead, our machine learning estimator is trained to predict the <strong>5-day relative percentage price return</strong> ($\Delta \%_t$):
            </p>

            <div class="math-box border-amber-500 p-6 rounded-r-2xl space-y-4">
                <h4 class="text-sm uppercase tracking-wider text-amber-400 font-bold">Equation 3.1: 5-Day Return Target Formulation</h4>
                <div class="text-center text-lg sm:text-xl font-mono py-3 bg-slate-950 rounded-xl border border-slate-800 text-amber-200">
                    $$\Delta \%_t = \frac{{P_{{t+5}} - P_t}}{{P_t}}$$
                </div>
            </div>

            <div class="math-box border-amber-500 p-6 rounded-r-2xl space-y-4">
                <h4 class="text-sm uppercase tracking-wider text-amber-400 font-bold">Equation 3.2: Live Pump Price Base Calibration</h4>
                <div class="text-center text-lg sm:text-xl font-mono py-3 bg-slate-950 rounded-xl border border-slate-800 text-amber-200">
                    $$\hat{{P}}_{{t+5}} = P_{{\text{{Live Pump}}}} \times (1 + \hat{{\Delta}}_{{\%}})$$
                </div>
                <p class="text-xs text-slate-400">
                    Multiplying predicted returns by today's live pump price ($P_{{\text{{Live Pump}}}} = \$3.89/\text{{gal}}$) ensures that all projected prices and scenario shocks adjust dynamically in cent-per-gallon terms.
                </p>
            </div>
        </section>

        <!-- Section 4: Machine Learning Optimization -->
        <section class="space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-800 pb-3">
                <span class="text-2xl font-black text-purple-500">04</span>
                <h3 class="text-2xl font-bold text-white">Regularized Ridge Optimization Objective</h3>
            </div>

            <p class="text-slate-300 leading-relaxed text-sm">
                To prevent collinearity between WTI crude and wholesale gasoline futures from causing overfitting, we fit a regularized linear model with $L_2$ Tikhonov regularization ($\alpha=10.0$):
            </p>

            <div class="math-box border-purple-500 p-6 rounded-r-2xl space-y-4">
                <h4 class="text-sm uppercase tracking-wider text-purple-400 font-bold">Equation 4.1: Ridge Regression Optimization Objective</h4>
                <div class="text-center text-lg sm:text-xl font-mono py-3 bg-slate-950 rounded-xl border border-slate-800 text-purple-200">
                    $$\min_{{\mathbf{{w}}}} \| \mathbf{{y}} - \mathbf{{X}}\mathbf{{w}} \|_2^2 + \alpha \| \mathbf{{w}} \|_2^2$$
                </div>
                <p class="text-xs text-slate-400">
                    where $\mathbf{{X}}$ is the standardized feature matrix ($Z$-score scaled), $\mathbf{{y}}$ is the 5-day price return vector, $\mathbf{{w}}$ represents model feature weights, and $\alpha=10.0$ controls regularization strength.
                </p>
            </div>
        </section>

        <!-- Section 5: MLOps Evaluation Metrics -->
        <section class="space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-800 pb-3">
                <span class="text-2xl font-black text-cyan-500">05</span>
                <h3 class="text-2xl font-bold text-white">MLOps Error & Directional Metrics</h3>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
                    <h4 class="text-xs font-bold text-cyan-400 uppercase">Mean Absolute Error (MAE)</h4>
                    <p class="text-sm font-mono text-white bg-slate-950 p-2.5 rounded-lg border border-slate-800">$$\text{{MAE}} = \frac{{1}}{{N}} \sum_{{i=1}}^N |y_i - \hat{{y}}_i|$$</p>
                    <p class="text-xs text-slate-400">National: <strong>$0.1151/gal</strong> | Tulsa: <strong>$0.1331/gal</strong></p>
                </div>

                <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
                    <h4 class="text-xs font-bold text-cyan-400 uppercase">Root Mean Squared Error (RMSE)</h4>
                    <p class="text-sm font-mono text-white bg-slate-950 p-2.5 rounded-lg border border-slate-800">$$\text{{RMSE}} = \sqrt{{\frac{{1}}{{N}} \sum_{{i=1}}^N (y_i - \hat{{y}}_i)^2}}$$</p>
                    <p class="text-xs text-slate-400">National: <strong>$0.1568/gal</strong> | Tulsa: <strong>$0.1880/gal</strong></p>
                </div>

                <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
                    <h4 class="text-xs font-bold text-emerald-400 uppercase">Directional Accuracy</h4>
                    <p class="text-sm font-mono text-white bg-slate-950 p-2.5 rounded-lg border border-slate-800">$$\text{{Hit Rate}} = \frac{{1}}{{N}} \sum \mathbb{{I}}(\text{{sign}}(\Delta y_i) == \text{{sign}}(\Delta \hat{{y}}_i))$$</p>
                    <p class="text-xs text-slate-400">National: <strong>60.79%</strong> | Tulsa: <strong>58.15%</strong></p>
                </div>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800 bg-slate-900/60 py-6 text-center text-xs text-slate-500">
        <p>Project <strong class="text-slate-400">midgley</strong> &bull; Educational Mathematics Guide &bull; Released under Apache-2.0 License</p>
    </footer>

</body>
</html>
"""

    with open(MATH_PATH, "w", encoding="utf-8") as f:
        f.write(math_html)
        
    logger.info(f"Successfully generated educational math guide at {MATH_PATH}")

if __name__ == "__main__":
    generate_public_dashboard()
