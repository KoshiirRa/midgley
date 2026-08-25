"""
Generate 1920s Vintage Design System Mockup Page (scripts/generate_design_mockup.py)
Generates `docs/design_mockup.html` implementing the 1920s Vintage Petroleum Laboratory & Antique Brass Gas Pump Design System (`DESIGN.md`).
"""

import os

DOCS_DIR = "docs"
MOCKUP_PATH = os.path.join(DOCS_DIR, "design_mockup.html")

MOCKUP_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1920s Vintage Midgley Design System | DELCO Petroleum Terminal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js" onload="renderMathInElement(document.body);"></script>
    <style>
        body {
            background-color: #0D0907;
            color: #FEF3C7;
            font-family: Georgia, Garamond, Cambria, "Times New Roman", serif;
        }
        .font-mono {
            font-family: "Courier Prime", "Courier New", Courier, monospace;
        }
        .font-pump {
            font-family: "JetBrains Mono", "Courier New", Consolas, monospace;
        }
        .katex-display {
            overflow-x: auto;
            overflow-y: hidden;
            max-width: 100%;
            padding: 0.5rem 0.2rem;
            margin: 0.5em 0;
        }
    </style>
</head>
<body class="min-h-screen flex flex-col antialiased selection:bg-amber-900/40 selection:text-amber-200">

    <!-- Sticky Antique Navigation Header -->
    <header class="sticky top-0 z-50 bg-[#120D0A]/90 backdrop-blur-md border-b border-[#785327]/60">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-700 via-amber-800 to-amber-950 flex items-center justify-center text-amber-200 font-bold font-mono text-lg border border-[#785327] shadow-lg">M</div>
                    <div>
                        <a href="index.html" class="text-lg font-bold text-amber-100 tracking-tight flex items-center space-x-2 hover:text-amber-400 transition-colors font-mono">
                            <span>MIDGLEY 1926</span>
                            <span class="text-[11px] px-2.5 py-0.5 rounded bg-[#2A1D13] text-amber-300 border border-[#785327] font-mono">Vintage Lab Spec</span>
                        </a>
                    </div>
                </div>

                <nav class="hidden md:flex items-center space-x-2 text-xs font-mono">
                    <a href="index.html" class="px-3 py-1.5 rounded text-amber-300 hover:text-amber-100 hover:bg-[#2A1D13] transition-all">Overview</a>
                    <a href="national.html" class="px-3 py-1.5 rounded text-amber-300 hover:text-amber-100 hover:bg-[#2A1D13] transition-all">Wholesale RBOB</a>
                    <a href="tulsa.html" class="px-3 py-1.5 rounded text-amber-300 hover:text-amber-100 hover:bg-[#2A1D13] transition-all">Tulsa Refinery</a>
                    <a href="math.html" class="px-3 py-1.5 rounded text-amber-300 hover:text-amber-100 hover:bg-[#2A1D13] transition-all">Math Logs</a>
                    <a href="design_mockup.html" class="px-3 py-1.5 rounded bg-[#2A1D13] text-amber-300 border border-[#785327] font-bold shadow-sm">Vintage Design System</a>
                </nav>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">

        <!-- Hero Title Banner -->
        <section class="bg-gradient-to-r from-[#17120F] via-[#1C1613] to-[#2B1B10] border-2 border-[#785327]/70 rounded-2xl p-6 sm:p-8 relative overflow-hidden shadow-2xl">
            <div class="absolute -right-10 -bottom-10 w-72 h-72 bg-amber-600/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="relative z-10 space-y-3">
                <div class="inline-flex items-center space-x-2 px-3 py-1 rounded bg-[#2A1D13] border border-[#785327] text-amber-400 text-xs font-mono">
                    <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                    <span>DAYTON ENGINEERING LABORATORIES (DELCO) &bull; EST. 1926</span>
                </div>
                <h1 class="text-3xl sm:text-4xl font-extrabold text-amber-100 tracking-tight font-serif">Thomas Midgley Jr. Vintage Petroleum Design System</h1>
                <p class="text-stone-300 text-sm sm:text-base max-w-3xl leading-relaxed">
                    1920s Industrial Petroleum Research &amp; Vintage Filling Station Terminal Specification. Featuring antique brass frame borders, mechanical rolling gas pump counter readouts, mahogany charcoal canvas styling, and sepia lab research logs.
                </p>
            </div>
        </section>

        <!-- Section 1: Color Tokens & Vintage Swatches -->
        <section class="space-y-4">
            <div class="flex items-center justify-between border-b border-[#785327]/50 pb-3">
                <h2 class="text-xl font-bold text-amber-100 tracking-tight font-serif flex items-center space-x-2">
                    <span class="text-amber-500">01.</span>
                    <span>Vintage Industrial Color Tokens</span>
                </h2>
                <span class="text-xs font-mono text-stone-400">1920s Palette Tokens</span>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                <!-- Swatch 1 -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-3 space-y-2">
                    <div class="h-14 rounded bg-[#0D0907] border border-stone-800 flex items-end p-2 text-[10px] font-mono text-stone-400">#0D0907</div>
                    <div>
                        <div class="text-xs font-bold text-amber-200">Mahogany Charcoal</div>
                        <div class="text-[11px] text-stone-400 font-mono">Page Canvas</div>
                    </div>
                </div>

                <!-- Swatch 2 -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-3 space-y-2">
                    <div class="h-14 rounded bg-[#17120F] border border-stone-700 flex items-end p-2 text-[10px] font-mono text-stone-400">#17120F</div>
                    <div>
                        <div class="text-xs font-bold text-amber-200">Weathered Slate</div>
                        <div class="text-[11px] text-stone-400 font-mono">Card Frame</div>
                    </div>
                </div>

                <!-- Swatch 3 -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-3 space-y-2">
                    <div class="h-14 rounded bg-[#F59E0B] flex items-end p-2 text-[10px] font-mono text-stone-950 font-bold">#F59E0B</div>
                    <div>
                        <div class="text-xs font-bold text-amber-400">Midgley Amber</div>
                        <div class="text-[11px] text-stone-400 font-mono">Counter Readouts</div>
                    </div>
                </div>

                <!-- Swatch 4 -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-3 space-y-2">
                    <div class="h-14 rounded bg-[#D97706] flex items-end p-2 text-[10px] font-mono text-stone-950 font-bold">#D97706</div>
                    <div>
                        <div class="text-xs font-bold text-amber-500">Refinery Copper</div>
                        <div class="text-[11px] text-stone-400 font-mono">WTI Crude Dials</div>
                    </div>
                </div>

                <!-- Swatch 5 -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-3 space-y-2">
                    <div class="h-14 rounded bg-[#785327] flex items-end p-2 text-[10px] font-mono text-amber-100 font-bold">#785327</div>
                    <div>
                        <div class="text-xs font-bold text-amber-300">Antique Brass</div>
                        <div class="text-[11px] text-stone-400 font-mono">Rivet Frame Lines</div>
                    </div>
                </div>

                <!-- Swatch 6 -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-3 space-y-2">
                    <div class="h-14 rounded bg-[#DC2626] flex items-end p-2 text-[10px] font-mono text-stone-100 font-bold">#DC2626</div>
                    <div>
                        <div class="text-xs font-bold text-red-400">Kerosene Red</div>
                        <div class="text-[11px] text-stone-400 font-mono">Disruption Shocks</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 2: Mechanical Rolling Counter Metro Cards -->
        <section class="space-y-4">
            <div class="flex items-center justify-between border-b border-[#785327]/50 pb-3">
                <h2 class="text-xl font-bold text-amber-100 tracking-tight font-serif flex items-center space-x-2">
                    <span class="text-amber-500">02.</span>
                    <span>Mechanical Rolling Gas Pump Counters</span>
                </h2>
                <span class="text-xs font-mono text-stone-400">3-Decimal Fuel Standard</span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

                <!-- Card 1: Tulsa Metro Mechanical Counter -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-6 shadow-2xl space-y-4 relative overflow-hidden">
                    <div class="flex items-center justify-between border-b border-[#785327]/40 pb-3">
                        <span class="text-xs px-3 py-1 rounded bg-[#2A1D13] text-amber-300 border border-[#785327] font-mono font-semibold">⚙️ DELCO LABS &bull; TULSA, OK</span>
                        <span class="text-xs text-stone-400 font-mono">EST. 1926</span>
                    </div>

                    <!-- Mechanical Counter Window -->
                    <div class="bg-[#0A0705] border-2 border-[#573A1B] rounded-lg p-4 font-pump text-center shadow-inner space-y-1">
                        <div class="text-[10px] text-amber-600 uppercase tracking-widest font-bold">5-Day Out Projected Price</div>
                        <div class="text-4xl font-extrabold text-amber-400 tracking-wider">$3.890<span class="text-sm text-stone-400 font-normal">/gal</span></div>
                    </div>

                    <div class="pt-3 border-t border-[#785327]/30 flex items-center justify-between text-xs font-mono text-stone-400">
                        <span>Cushing Margin: <strong class="text-amber-300">$0.706/gal</strong></span>
                        <span class="text-emerald-400 font-bold">▲ +$0.173 (4.58%)</span>
                    </div>
                </div>

                <!-- Card 2: National RBOB Wholesale -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-6 shadow-2xl space-y-4 relative overflow-hidden">
                    <div class="flex items-center justify-between border-b border-[#785327]/40 pb-3">
                        <span class="text-xs px-3 py-1 rounded bg-[#2A1D13] text-amber-300 border border-[#785327] font-mono font-semibold">🏛️ NYMEX RBOB &bull; NATIONAL</span>
                        <span class="text-xs text-stone-400 font-mono">FUTURES HUB</span>
                    </div>

                    <!-- Mechanical Counter Window -->
                    <div class="bg-[#0A0705] border-2 border-[#573A1B] rounded-lg p-4 font-pump text-center shadow-inner space-y-1">
                        <div class="text-[10px] text-amber-600 uppercase tracking-widest font-bold">Wholesale Benchmark Target</div>
                        <div class="text-4xl font-extrabold text-amber-300 tracking-wider">$3.184<span class="text-sm text-stone-400 font-normal">/gal</span></div>
                    </div>

                    <div class="pt-3 border-t border-[#785327]/30 flex items-center justify-between text-xs font-mono text-stone-400">
                        <span>Directional Hit: <strong class="text-emerald-400">60.79%</strong></span>
                        <span>MAE: <strong class="text-amber-400">$0.1069</strong></span>
                    </div>
                </div>

                <!-- Card 3: Oakland PADD 5 -->
                <div class="bg-[#17120F] border border-[#785327]/60 rounded-xl p-6 shadow-2xl space-y-4 relative overflow-hidden">
                    <div class="flex items-center justify-between border-b border-[#785327]/40 pb-3">
                        <span class="text-xs px-3 py-1 rounded bg-[#2A1D13] text-amber-300 border border-[#785327] font-mono font-semibold">🌊 PADD 5 &bull; OAKLAND, CA</span>
                        <span class="text-xs text-stone-400 font-mono">CARB SPEC</span>
                    </div>

                    <!-- Mechanical Counter Window -->
                    <div class="bg-[#0A0705] border-2 border-[#573A1B] rounded-lg p-4 font-pump text-center shadow-inner space-y-1">
                        <div class="text-[10px] text-amber-600 uppercase tracking-widest font-bold">West Coast High-Cost Pump</div>
                        <div class="text-4xl font-extrabold text-amber-500 tracking-wider">$4.950<span class="text-sm text-stone-400 font-normal">/gal</span></div>
                    </div>

                    <div class="pt-3 border-t border-[#785327]/30 flex items-center justify-between text-xs font-mono text-stone-400">
                        <span>CARB Tax Overhead: <strong class="text-red-400">$0.953/gal</strong></span>
                    </div>
                </div>

            </div>
        </section>

        <!-- Section 3: Kerosene Disruption Valves -->
        <section class="space-y-4">
            <div class="flex items-center justify-between border-b border-[#785327]/50 pb-3">
                <h2 class="text-xl font-bold text-amber-100 tracking-tight font-serif flex items-center space-x-2">
                    <span class="text-amber-500">03.</span>
                    <span>Refinery Emergency Relief Valve Warnings</span>
                </h2>
                <span class="text-xs font-mono text-stone-400">Pressure Telemetry</span>
            </div>

            <div class="space-y-3">
                <div class="bg-red-950/40 border border-red-800/60 text-red-300 rounded-xl p-4 font-mono text-xs flex items-start space-x-3 shadow-lg">
                    <span class="text-red-500 font-bold text-xl leading-none mt-0.5">⚠️</span>
                    <div class="space-y-1">
                        <div class="flex items-center space-x-2">
                            <strong class="text-red-200 uppercase tracking-wider font-bold">West Tulsa HF Sinclair Refinery EF-3 Tornado Disruption</strong>
                            <span class="text-[10px] px-2 py-0.5 rounded bg-red-900/40 text-red-300 border border-red-700/50">+4.58% SURGE</span>
                        </div>
                        <p class="text-xs text-red-300/80 leading-relaxed">
                            Direct physical alkylation unit disruption. Dynamic rack margin shock expansion of <strong class="text-red-200">+$0.173/gal</strong> decaying with half-life \(t_{1/2} = 4.0\text{ days}\).
                        </p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 4: Sepia Research Log & KaTeX Equation -->
        <section class="space-y-4">
            <div class="flex items-center justify-between border-b border-[#785327]/50 pb-3">
                <h2 class="text-xl font-bold text-amber-100 tracking-tight font-serif flex items-center space-x-2">
                    <span class="text-amber-500">04.</span>
                    <span>Sepia Research Log (LaTeX Equation Standard)</span>
                </h2>
                <span class="text-xs font-mono text-stone-400">Dayton Lab Archive</span>
            </div>

            <div class="bg-[#17120F] border border-[#785327]/50 rounded-2xl p-6 space-y-4 shadow-xl">
                <div class="flex items-center justify-between border-b border-[#785327]/40 pb-2">
                    <span class="text-xs font-mono text-amber-400 uppercase tracking-widest">// DAYTON LAB RESEARCH LOG &bull; EQUATION 2.1</span>
                    <span class="text-xs font-mono text-stone-400">Half-Life \(t_{1/2} = 5.0\text{ days}\)</span>
                </div>
                <div class="katex-display text-amber-100 bg-[#0A0705] p-5 rounded-xl border border-[#573A1B]">
                    $$\text{Memory}_{t} = \text{Memory}_{t-1} \times e^{-\frac{\ln(2)}{t_{1/2}}} + \text{NewShock}_t$$
                </div>
                <p class="text-xs text-stone-400 font-mono leading-relaxed">
                    Models point-shock decay over 2-3 weeks, resolving persistence across geopolitical news releases, NOAA freeze alerts, and executive social media posts.
                </p>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="mt-auto border-t border-[#785327]/60 bg-[#0A0705] py-6">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-stone-400 font-mono space-y-2 sm:space-y-0">
            <div>Thomas Midgley Jr. Petroleum Engine &copy; 1926 - 2026</div>
            <div>Refinery Telemetry &bull; Cushing WTI &bull; NOAA Weather &bull; RBOB Futures</div>
        </div>
    </footer>

</body>
</html>
"""

def generate():
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(MOCKUP_PATH, "w", encoding="utf-8") as f:
        f.write(MOCKUP_HTML)
    print(f"Successfully generated 1920s vintage {MOCKUP_PATH}")

if __name__ == "__main__":
    generate()
