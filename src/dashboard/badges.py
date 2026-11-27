"""Header badges, analytics script, and basemap URL helpers for public dashboards (Issue #562)."""

import os
from src.version import get_model_version, get_version, is_release_branch


def get_release_badge() -> str:
    """Generates dynamic HTML badge for the header based on git branch or environment."""
    version = get_version()
    if is_release_branch():
        return f'<span class="text-xs px-2.5 py-0.5 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 font-normal">Release v{version}</span>'
    return f'<span class="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 font-normal">Dev Branch v{version}-dev</span>'


def get_model_badge() -> str:
    """Generates dynamic HTML badge for the active quantitative model engine version."""
    model_ver = get_model_version()
    return f'<span class="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 font-normal">Model {model_ver}</span>'


def get_multi_agent_sim_badge() -> str:
    """Generates dynamic HTML badge indicating whether MiroFish Multi-Agent Financial Simulation mode is active."""
    try:
        from src.scenario_simulator import is_multi_agent_sim_enabled
        is_active = is_multi_agent_sim_enabled()
    except Exception:
        is_active = False

    if is_active:
        return '<span class="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-normal" title="MiroFish Multi-Agent Simulation Cohort Active"><i class="fa-solid fa-users-gear text-[10px] mr-1"></i>Multi-Agent Cohort: ON</span>'
    return '<span class="text-xs px-2.5 py-0.5 rounded-full bg-slate-500/20 text-slate-400 border border-slate-500/30 font-normal" title="Standard Linear Scenario Engine Active"><i class="fa-solid fa-users-slash text-[10px] mr-1"></i>Multi-Agent Cohort: OFF</span>'


def get_analytics_script() -> str:
    """Generates Cloudflare Web Analytics script tag if CLOUDFLARE_ANALYTICS_TOKEN is present in environment."""
    beacon_val = os.environ.get("CLOUDFLARE_ANALYTICS_TOKEN", "").strip()
    if not beacon_val:
        return ""

    safe_beacon = "".join(c for c in beacon_val if c.isalnum() or c in "-_")
    return f"""    <!-- Cloudflare Web Analytics -->
    <script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "{safe_beacon}"}}'></script>"""


def get_carto_basemap_url() -> str:
    """Returns the CARTO dark basemap tile URL with sanitized credential parameter if configured."""
    custom_url = os.environ.get("MIDGLEY_BASEMAP_TILE_URL", "").strip()
    if custom_url:
        return custom_url

    client_param = (
        os.environ.get("CARTO_API_KEY")
        or os.environ.get("CARTO_CLIENT_ID")
        or ""
    ).strip()
    if not client_param:
        return "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"

    safe_param = "".join(c for c in client_param if c.isalnum() or c in "-_")
    if safe_param:
        return f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png?key={safe_param}"
    return "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
