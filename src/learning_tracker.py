"""
Model Learning & Adaptation Tracker (src/learning_tracker.py)
Tracks, documents, and visualizes quantitative model evolution, longitudinal accuracy curves,
episodic agent reflections, and autonomous hypothesis adaptation over time.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PREDICTION_HISTORY_CSV = os.path.join(PROJECT_ROOT, "data", "prediction_history.csv")
PRAXIST_EXPERIMENTS_FILE = os.path.join(PROJECT_ROOT, "data", "praxist_experiments.json")
AGENT_MEMORY_DB = os.path.join(PROJECT_ROOT, "data", "agent_memory.sqlite")
TELEMETRY_ALERTS_FILE = os.path.join(PROJECT_ROOT, "data", "telemetry_alerts.json")
MODEL_LEARNING_MD = os.path.join(PROJECT_ROOT, "MODEL_LEARNING.md")


def is_testing_environment() -> bool:
    """Checks if running inside an automated test runner."""
    return (
        os.environ.get("TESTING") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("MIDGLEY_TEST_MODE") == "1"
    )


def load_prediction_dataset(csv_path: Optional[str] = None) -> pd.DataFrame:
    """Loads and preprocesses prediction history dataframe."""
    path = csv_path or PREDICTION_HISTORY_CSV
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        if 'actual_5d_price' in df.columns:
            df = df.dropna(subset=['actual_5d_price']).copy()
        if not df.empty:
            # Parse dates
            if 'forecast_target_date' in df.columns:
                df['target_date_dt'] = pd.to_datetime(df['forecast_target_date'], errors='coerce')
            elif 'log_timestamp' in df.columns:
                df['target_date_dt'] = pd.to_datetime(df['log_timestamp'], errors='coerce')
            else:
                df['target_date_dt'] = pd.Timestamp.now()
            df = df.sort_values(by='target_date_dt')
        return df
    except Exception as e:
        logger.debug(f"Error loading prediction history in learning tracker: {e}")
        return pd.DataFrame()


def calculate_longitudinal_learning_curves(
    df: Optional[pd.DataFrame] = None,
    window_days: int = 30,
    step_days: int = 5
) -> Dict[str, Any]:
    """
    Computes rolling longitudinal learning curves over time (MAE, Naive Baseline MAE, Uplift %, LLM Win Rate).
    Returns chronological time-series points suitable for Chart.js.
    """
    if df is None:
        df = load_prediction_dataset()
    if df.empty or 'actual_5d_price' not in df.columns:
        return {
            "dates": [],
            "model_mae": [],
            "naive_mae": [],
            "uplift_pct": [],
            "hit_rate_pct": [],
            "llm_win_rate_pct": [],
            "total_points": 0
        }

    df = df.copy()
    if 'target_date_dt' not in df.columns:
        if 'forecast_target_date' in df.columns:
            df['target_date_dt'] = pd.to_datetime(df['forecast_target_date'], errors='coerce')
        elif 'log_timestamp' in df.columns:
            df['target_date_dt'] = pd.to_datetime(df['log_timestamp'], errors='coerce')
        else:
            df['target_date_dt'] = pd.Timestamp.now()

    # Clean numeric columns
    df['actual'] = pd.to_numeric(df['actual_5d_price'], errors='coerce')
    df['pred'] = pd.to_numeric(df['predicted_5d_price'], errors='coerce')
    df['base'] = pd.to_numeric(df['current_base_price'], errors='coerce')
    df['hit'] = pd.to_numeric(df.get('directional_hit', 0), errors='coerce').fillna(0)

    # Calculate LLM win vs pure quant baseline
    if 'quant_baseline_5d_price' in df.columns:
        df['quant_base'] = pd.to_numeric(df['quant_baseline_5d_price'], errors='coerce')
        llm_err = np.abs(df['actual'] - df['pred'])
        quant_err = np.abs(df['actual'] - df['quant_base'])
        df['llm_won'] = np.where(llm_err < quant_err, 1.0, 0.0)
    else:
        df['llm_won'] = 0.5

    df = df.dropna(subset=['actual', 'pred', 'base', 'target_date_dt']).sort_values('target_date_dt')
    if len(df) < 10:
        return {
            "dates": [],
            "model_mae": [],
            "naive_mae": [],
            "uplift_pct": [],
            "hit_rate_pct": [],
            "llm_win_rate_pct": [],
            "total_points": 0
        }

    min_date = pd.Timestamp(df['target_date_dt'].min())
    max_date = pd.Timestamp(df['target_date_dt'].max())

    date_points = []
    model_mae_list = []
    naive_mae_list = []
    uplift_list = []
    hit_rate_list = []
    llm_win_rate_list = []

    # Slide window from min_date + window_days up to max_date
    current_end = min_date + pd.Timedelta(days=int(window_days))
    if current_end > max_date:
        current_end = max_date

    while current_end <= max_date + pd.Timedelta(days=int(step_days) - 1):
        window_start = current_end - pd.Timedelta(days=int(window_days))
        window_df = df[(df['target_date_dt'] >= window_start) & (df['target_date_dt'] <= current_end)]

        if len(window_df) >= 5:
            m_err = np.abs(window_df['actual'] - window_df['pred'])
            n_err = np.abs(window_df['actual'] - window_df['base'])

            m_mae = float(np.mean(m_err))
            n_mae = float(np.mean(n_err))
            uplift = float(((n_mae - m_mae) / n_mae) * 100.0) if n_mae > 0 else 0.0
            h_rate = float(np.mean(window_df['hit']) * 100.0)
            llm_win = float(np.mean(window_df['llm_won']) * 100.0)

            date_str = current_end.strftime("%Y-%m-%d")
            date_points.append(date_str)
            model_mae_list.append(round(m_mae, 4))
            naive_mae_list.append(round(n_mae, 4))
            uplift_list.append(round(uplift, 2))
            hit_rate_list.append(round(h_rate, 2))
            llm_win_rate_list.append(round(llm_win, 2))

        current_end += pd.Timedelta(days=int(step_days))

    return {
        "dates": date_points,
        "model_mae": model_mae_list,
        "naive_mae": naive_mae_list,
        "uplift_pct": uplift_list,
        "hit_rate_pct": hit_rate_list,
        "llm_win_rate_pct": llm_win_rate_list,
        "total_points": len(date_points)
    }


def get_multi_window_performance_summary(df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """
    Computes performance summary across standard longitudinal windows: 7d, 14d, 30d, 90d, All-Time.
    """
    if df is None:
        df = load_prediction_dataset()
    df = df.copy()
    if 'target_date_dt' not in df.columns:
        if 'forecast_target_date' in df.columns:
            df['target_date_dt'] = pd.to_datetime(df['forecast_target_date'], errors='coerce')
        elif 'log_timestamp' in df.columns:
            df['target_date_dt'] = pd.to_datetime(df['log_timestamp'], errors='coerce')
        else:
            df['target_date_dt'] = pd.Timestamp.now()

    df['actual'] = pd.to_numeric(df['actual_5d_price'], errors='coerce')
    df['pred'] = pd.to_numeric(df['predicted_5d_price'], errors='coerce')
    df['base'] = pd.to_numeric(df['current_base_price'], errors='coerce')
    df['hit'] = pd.to_numeric(df.get('directional_hit', 0), errors='coerce').fillna(0)

    if 'quant_baseline_5d_price' in df.columns:
        df['quant_base'] = pd.to_numeric(df['quant_baseline_5d_price'], errors='coerce')
        llm_err = np.abs(df['actual'] - df['pred'])
        quant_err = np.abs(df['actual'] - df['quant_base'])
        df['llm_won'] = np.where(llm_err < quant_err, 1.0, 0.0)
    else:
        df['llm_won'] = 0.5

    clean_df = df.dropna(subset=['actual', 'pred', 'base', 'target_date_dt']).sort_values('target_date_dt')
    if clean_df.empty:
        return []

    max_dt = pd.Timestamp(clean_df['target_date_dt'].max())
    windows = [
        ("7-Day Window", 7),
        ("14-Day Window", 14),
        ("30-Day Window", 30),
        ("90-Day Window", 90),
        ("All-Time Window", None)
    ]

    results = []
    for label, days in windows:
        if days is not None:
            cutoff = max_dt - pd.Timedelta(days=int(days))
            w_df = clean_df[clean_df['target_date_dt'] >= cutoff]
        else:
            w_df = clean_df

        n_eval = len(w_df)
        if n_eval == 0:
            continue

        m_mae = float(np.mean(np.abs(w_df['actual'] - w_df['pred'])))
        n_mae = float(np.mean(np.abs(w_df['actual'] - w_df['base'])))
        uplift = float(((n_mae - m_mae) / n_mae) * 100.0) if n_mae > 0 else 0.0
        hit_rate = float(np.mean(w_df['hit']) * 100.0)
        llm_win = float(np.mean(w_df['llm_won']) * 100.0)

        results.append({
            "window_name": label,
            "days": days or "All",
            "evaluations": n_eval,
            "model_mae": round(m_mae, 4),
            "naive_mae": round(n_mae, 4),
            "uplift_pct": round(uplift, 2),
            "directional_hit_pct": round(hit_rate, 2),
            "llm_win_rate_pct": round(llm_win, 2),
            "status": "🟢 Optimal" if uplift > 0 else "⚠️ Calibration Active"
        })

    return results


def get_praxist_learning_timeline(experiments_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads and formats Sapient PRAXIST hypothesis evaluation timeline."""
    path = experiments_path or PRAXIST_EXPERIMENTS_FILE
    if not os.path.exists(path):
        return {
            "total_hypotheses": 0,
            "accepted_hypotheses": 0,
            "baseline_params": {
                "half_life_days": 4.5,
                "geopolitical_weight": 0.35,
                "supply_disruption_weight": 0.40,
                "opec_action_weight": 0.25,
                "weekend_gap_multiplier": 1.42
            },
            "experiments": []
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "total_hypotheses": data.get("total_hypotheses_tested", len(data.get("experiments", []))),
                "accepted_hypotheses": data.get("accepted_hypotheses", 0),
                "baseline_params": {
                    "half_life_days": 4.5,
                    "geopolitical_weight": 0.35,
                    "supply_disruption_weight": 0.40,
                    "opec_action_weight": 0.25,
                    "weekend_gap_multiplier": 1.42
                },
                "experiments": data.get("experiments", [])
            }
    except Exception as e:
        logger.debug(f"Error loading praxist experiments: {e}")
        return {
            "total_hypotheses": 0,
            "accepted_hypotheses": 0,
            "baseline_params": {},
            "experiments": []
        }


def get_episodic_reflections_summary(
    db_path: Optional[str] = None,
    max_records: int = 12
) -> Dict[str, Any]:
    """
    Loads and categorizes episodic memory reflections from SQLite memory store.
    Categorizes into Seasonal Transition, Refinery Outage, Pipeline Constraint, Geopolitical, and General.
    """
    path = db_path or AGENT_MEMORY_DB
    if not os.path.exists(path):
        return {
            "total_reflections": 0,
            "total_memories": 0,
            "categories": {},
            "recent_feed": []
        }

    try:
        conn = sqlite3.connect(path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM memories")
        mem_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM reflections")
        ref_count = c.fetchone()[0]

        c.execute("""
            SELECT id, reflection_id, region, anomaly_type, title, root_cause,
                   historical_analogy, calibration_suggestion, created_at
            FROM reflections
            ORDER BY id DESC
            LIMIT ?
        """, (max_records,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()

        # Group by category
        categories = {
            "Seasonal Transition": [],
            "Refinery Outage": [],
            "Pipeline / Waterway Constraint": [],
            "Geopolitical & OPEC Shock": [],
            "Price Discrepancy & General Outliers": []
        }

        for row in rows:
            text = f"{row.get('title', '')} {row.get('root_cause', '')} {row.get('anomaly_type', '')}".lower()
            if "season" in text or "rvp" in text or "winter" in text or "summer" in text:
                categories["Seasonal Transition"].append(row)
            elif "refinery" in text or "flaring" in text or "turnaround" in text or "outage" in text:
                categories["Refinery Outage"].append(row)
            elif "pipeline" in text or "barge" in text or "river" in text or "canal" in text or "terminal" in text:
                categories["Pipeline / Waterway Constraint"].append(row)
            elif "opec" in text or "tariff" in text or "sanction" in text or "war" in text or "hormuz" in text:
                categories["Geopolitical & OPEC Shock"].append(row)
            else:
                categories["Price Discrepancy & General Outliers"].append(row)

        return {
            "total_reflections": ref_count,
            "total_memories": mem_count,
            "categories": categories,
            "recent_feed": rows
        }
    except Exception as e:
        logger.debug(f"Error reading episodic reflections in learning tracker: {e}")
        return {
            "total_reflections": 0,
            "total_memories": 0,
            "categories": {},
            "recent_feed": []
        }


def generate_learning_journal_markdown(
    output_path: Optional[str] = None,
    df: Optional[pd.DataFrame] = None
) -> str:
    """
    Generates the comprehensive MODEL_LEARNING.md document recording cumulative milestones,
    longitudinal performance windows, parameter evolution, and episodic reflections.
    """
    save_path = output_path or MODEL_LEARNING_MD
    curves = calculate_longitudinal_learning_curves(df=df)
    windows = get_multi_window_performance_summary(df=df)
    praxist = get_praxist_learning_timeline()
    reflections = get_episodic_reflections_summary()

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    from src.version import get_model_version
    model_ver = get_model_version()

    # Build Markdown Content
    lines = [
        "# 🧠 Model Learning, Adaptation & Longitudinal Evolution Journal",
        "",
        f"> **Last Evaluated & Synced:** `{now_utc}` | **Repository Architecture:** `{model_ver}`",
        "",
        "This journal tracks and documents how Midgley's multi-agent quantitative and LLM system learns, recalibrates, and adapts over time through **Rolling Ridge Re-weighting**, **Episodic Outlier Reflection (Retain-Recall-Reflect)**, and **Sapient PRAXIST Autonomous Hypothesis Testing**.",
        "",
        "---",
        "",
        "## 📈 Longitudinal Performance Evolution (Multi-Window)",
        "",
        "| Time Window | Evaluations | Model MAE | Naive Baseline MAE | Model Uplift vs. Naive | Directional Hit Rate | LLM Win Rate | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for w in windows:
        uplift_str = f"**`{w['uplift_pct']:+.2f}%`**" if w['uplift_pct'] > 0 else f"`{w['uplift_pct']:+.2f}%`"
        lines.append(
            f"| **{w['window_name']}** | {w['evaluations']} | `${w['model_mae']:.4f}/gal` | `${w['naive_mae']:.4f}/gal` | {uplift_str} | **`{w['directional_hit_pct']:.2f}%`** | `{w['llm_win_rate_pct']:.1f}%` | {w['status']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 🔬 Sapient PRAXIST Parameter Evolution & Hypothesis Ledger",
        "",
        f"- **Total Hypotheses Evaluated:** `{praxist['total_hypotheses']}`",
        f"- **Accepted Hypotheses in Production:** `{praxist['accepted_hypotheses']}`",
        "- **Active Calibrated Baseline Parameters:**",
        f"  - Exogenous Shock Half-Life ($t_{{1/2}}$): **`{praxist['baseline_params'].get('half_life_days', 4.5)} days`**",
        f"  - Geopolitical Shock Weight: **`{praxist['baseline_params'].get('geopolitical_weight', 0.35)}`**",
        f"  - Supply Disruption Weight: **`{praxist['baseline_params'].get('supply_disruption_weight', 0.40)}`**",
        f"  - OPEC Action Weight: **`{praxist['baseline_params'].get('opec_action_weight', 0.25)}`**",
        f"  - Weekend Gap Multiplier: **`{praxist['baseline_params'].get('weekend_gap_multiplier', 1.42)}x`**",
        "",
        "### 📜 Evaluated Hypothesis History",
        "",
        "| Timestamp | Hypothesis Name | Candidate Parameters | Baseline MAE | Candidate MAE | Delta ($\\Delta$) | $t$-Statistic ($p$-value) | Verdict |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |"
    ])

    if praxist.get("experiments"):
        for exp in praxist["experiments"]:
            params = exp.get("candidate_params", {})
            param_str = f"$t_{{1/2}}={params.get('half_life_days', 4.5)}\\text{{d}}, W_{{wknd}}={params.get('weekend_gap_multiplier', 1.42)}\\times$"
            t_str = f"$t={exp.get('t_statistic', 0.0):.2f}$ ($p={exp.get('p_value', 1.0):.4f}$)"
            status_badge = "🟢 **ACCEPTED**" if exp.get("status") == "ACCEPTED" else "⚪ `REJECTED`"
            lines.append(
                f"| `{exp.get('evaluated_at', '')[:10]}` | **`{exp.get('hypothesis_name', '')}`** | {param_str} | `${exp.get('baseline_mae', 0.0):.4f}` | `${exp.get('candidate_mae', 0.0):.4f}` | `{exp.get('mae_delta', 0.0):+.4f}` | {t_str} | {status_badge} |"
            )
    else:
        lines.append("| _No recorded PRAXIST experiments_ | - | - | - | - | - | - | - |")

    lines.extend([
        "",
        "---",
        "",
        "## 🧠 Episodic Qualitative Failure Modes & Reflection Archive",
        "",
        f"Total indexed episodic memories in local store: **`{reflections['total_memories']}`** | Total synthesized reflections: **`{reflections['total_reflections']}`**",
        "",
        "### 📂 Categorized Anomaly Case Studies",
        ""
    ])

    for cat_name, cat_items in reflections["categories"].items():
        lines.append(f"#### 🏷️ {cat_name} ({len(cat_items)} case studies)")
        if cat_items:
            for item in cat_items[:3]:
                lines.extend([
                    f"- **{item.get('title', 'Case Study')}** (`{item.get('region', '')}` | `{item.get('created_at', '')[:10]}`)",
                    f"  - **Root Cause:** {item.get('root_cause', 'N/A')}",
                    f"  - **Historical Analogy:** {item.get('historical_analogy', 'N/A')}",
                    f"  - **Calibration Suggestion:** `{item.get('calibration_suggestion', 'N/A')}`",
                    ""
                ])
        else:
            lines.append("_No anomalies logged in this category._\n")

    lines.extend([
        "---",
        "",
        "## 🛠️ Continuous Learning Mechanism Overview",
        "",
        "```",
        " ┌─────────────────────────────────────────────────────────────┐",
        " │             1. DAILY PREDICTION & OUTCOME LOGGING           │",
        " │  Logs 5-day out-of-time forecasts -> backfills actual price │",
        " └──────────────────────────────┬──────────────────────────────┘",
        "                                │",
        "                                ▼",
        " ┌─────────────────────────────────────────────────────────────┐",
        " │         2. EPISODIC MEMORY PASS (Retain-Recall-Reflect)     │",
        " │  Isolates forecast outliers -> generates root-cause post-   │",
        " │  mortems & stores in SQLite FTS5 / Vectorize Hindsight API  │",
        " └──────────────────────────────┬──────────────────────────────┘",
        "                                │",
        "                                ▼",
        " ┌─────────────────────────────────────────────────────────────┐",
        " │             3. SAPIENT PRAXIST HYPOTHESIS HARNESS           │",
        " │  Autonomous grid sweep & t-tests on shock decay parameters   │",
        " └──────────────────────────────┬──────────────────────────────┘",
        "                                │",
        "                                ▼",
        " ┌─────────────────────────────────────────────────────────────┐",
        " │          4. MLOps TELEMETRY & OBSERVABILITY DASHBOARD       │",
        " │  Updates MODEL_LEARNING.md, telemetry.html, and W&B charts  │",
        " └─────────────────────────────────────────────────────────────┘",
        "```",
        "",
        "_Automated Model Learning Journal maintained by `src/learning_tracker.py`._"
    ])

    markdown_content = "\n".join(lines)

    if not is_testing_environment() or os.environ.get("TEST_LEARNING_PERSIST"):
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        except Exception as e:
            logger.debug(f"Error writing MODEL_LEARNING.md: {e}")

    return markdown_content


def generate_learning_telemetry_html_snippet(
    df: Optional[pd.DataFrame] = None,
    rel_prefix: str = ""
) -> str:
    """
    Generates the responsive HTML component (Tailwind CSS + Chart.js) to be embedded
    inside docs/telemetry.html (Issue #255).
    """
    curves = calculate_longitudinal_learning_curves(df=df)
    windows = get_multi_window_performance_summary(df=df)
    praxist = get_praxist_learning_timeline()
    reflections = get_episodic_reflections_summary()

    # JSON strings for Chart.js
    dates_json = json.dumps(curves.get("dates", []))
    model_mae_json = json.dumps(curves.get("model_mae", []))
    naive_mae_json = json.dumps(curves.get("naive_mae", []))
    uplift_json = json.dumps(curves.get("uplift_pct", []))
    llm_win_json = json.dumps(curves.get("llm_win_rate_pct", []))

    # Multi-window table rows
    window_rows_html = ""
    for w in windows:
        badge_color = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" if w['uplift_pct'] > 0 else "bg-amber-500/20 text-amber-400 border-amber-500/30"
        uplift_class = "text-emerald-400 font-bold" if w['uplift_pct'] > 0 else "text-amber-400"
        window_rows_html += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-3 px-4 font-semibold text-slate-200">{w['window_name']}</td>
            <td class="py-3 px-4 text-slate-400">{w['evaluations']}</td>
            <td class="py-3 px-4 font-mono font-semibold text-sky-400">${w['model_mae']:.4f}</td>
            <td class="py-3 px-4 font-mono text-slate-400">${w['naive_mae']:.4f}</td>
            <td class="py-3 px-4 font-mono {uplift_class}">{w['uplift_pct']:+.2f}%</td>
            <td class="py-3 px-4 font-mono text-slate-200">{w['directional_hit_pct']:.1f}%</td>
            <td class="py-3 px-4 font-mono text-indigo-400">{w['llm_win_rate_pct']:.1f}%</td>
            <td class="py-3 px-4">
                <span class="px-2 py-0.5 rounded text-[10px] font-semibold border {badge_color}">{w['status']}</span>
            </td>
        </tr>
        """

    # PRAXIST experiment items
    praxist_items_html = ""
    for exp in praxist.get("experiments", [])[-5:]:
        p = exp.get("candidate_params", {})
        status_badge = '<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">ACCEPTED</span>' if exp.get("status") == "ACCEPTED" else '<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-700/60 text-slate-400 border border-slate-600/30">REJECTED</span>'
        praxist_items_html += f"""
        <div class="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-mono font-bold text-sky-300">{exp.get('hypothesis_name', 'Hypothesis')}</span>
                    {status_badge}
                </div>
                <div class="text-slate-400 mt-1">
                    Candidate: <code class="text-amber-300">t1/2={p.get('half_life_days', 4.5)}d</code>, 
                    Weekend Mult: <code class="text-amber-300">{p.get('weekend_gap_multiplier', 1.42)}x</code> | 
                    Evaluated: <span class="text-slate-300">{exp.get('evaluated_at', '')[:10]}</span>
                </div>
            </div>
            <div class="text-right font-mono text-[11px] text-slate-400">
                ΔMAE: <span class="{'text-emerald-400' if exp.get('mae_delta', 0) < 0 else 'text-slate-300'}">{exp.get('mae_delta', 0):+.4f}</span> | 
                t={exp.get('t_statistic', 0):.2f} (p={exp.get('p_value', 1):.4f})
            </div>
        </div>
        """

    # Episodic Reflections list
    reflections_html = ""
    for r in reflections.get("recent_feed", [])[:4]:
        reflections_html += f"""
        <div class="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
            <div class="flex items-center justify-between">
                <span class="font-semibold text-slate-200 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-amber-400"></span>
                    {r.get('title', 'Outlier Post-Mortem')}
                </span>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400">{r.get('region', '')}</span>
            </div>
            <p class="text-slate-400 leading-relaxed"><strong class="text-slate-300">Root Cause:</strong> {r.get('root_cause', 'N/A')}</p>
            <div class="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/40 text-[11px] text-slate-300">
                <span class="text-emerald-400 font-semibold">💡 Calibration Suggestion:</span> {r.get('calibration_suggestion', 'N/A')}
            </div>
        </div>
        """

    html = f"""
    <!-- MODEL LEARNING & ADAPTATION TRACKING (Issue #255) -->
    <div class="mt-12 space-y-8" id="model-learning-section">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
                <div class="flex items-center gap-2">
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">MLOps Evolution</span>
                    <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
                        🧠 Model Learning, Adaptation & Longitudinal Tracking
                    </h2>
                </div>
                <p class="text-xs text-slate-400 mt-1">
                    Continuous monitoring of empirical learning curves, baseline convergence, PRAXIST hypothesis testing, and episodic memory reflections.
                </p>
            </div>
            <div class="flex items-center gap-2">
                <a href="https://github.com/KoshiirRa/midgley/blob/main/MODEL_LEARNING.md" target="_blank" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition">
                    <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    View MODEL_LEARNING.md
                </a>
            </div>
        </div>

        <!-- Longitudinal Learning Charts -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Learning Curve Chart -->
            <div class="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
                            Rolling 30-Day MAE vs. Naive Persistence Baseline
                        </h3>
                        <span class="text-[10px] font-mono text-slate-400">Lower is better</span>
                    </div>
                    <p class="text-xs text-slate-400 mb-4">
                        Evaluates whether model forecast error (sky line) consistently tracks below or converges against the zero-change naive benchmark (amber line).
                    </p>
                </div>
                <div class="h-64 relative">
                    <canvas id="learningCurveChart"></canvas>
                </div>
            </div>

            <!-- LLM Win Rate & Uplift Chart -->
            <div class="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-indigo-400"></span>
                            LLM Augmentation Win Rate & Baseline Uplift (%)
                        </h3>
                        <span class="text-[10px] font-mono text-slate-400">Target > 55%</span>
                    </div>
                    <p class="text-xs text-slate-400 mb-4">
                        Tracks the empirical frequency where real-time qualitative LLM feature injection outperforms pure quantitative Ridge regression.
                    </p>
                </div>
                <div class="h-64 relative">
                    <canvas id="llmWinRateChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Longitudinal Multi-Window Scoreboard -->
        <div class="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl">
            <h3 class="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                Longitudinal Accuracy & Convergence Horizons
            </h3>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 bg-slate-950/40">
                            <th class="py-2.5 px-4 font-semibold">Horizon Window</th>
                            <th class="py-2.5 px-4 font-semibold">Evaluations</th>
                            <th class="py-2.5 px-4 font-semibold">Model MAE</th>
                            <th class="py-2.5 px-4 font-semibold">Naive MAE</th>
                            <th class="py-2.5 px-4 font-semibold">Uplift vs Naive</th>
                            <th class="py-2.5 px-4 font-semibold">Directional Hit</th>
                            <th class="py-2.5 px-4 font-semibold">LLM Win Rate</th>
                            <th class="py-2.5 px-4 font-semibold">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {window_rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- PRAXIST & Episodic Memory Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- PRAXIST Parameter Timeline -->
            <div class="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl space-y-4">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
                            <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
                            Sapient PRAXIST Hypothesis Evolution
                        </h3>
                        <p class="text-xs text-slate-400 mt-0.5">Autonomous testing of exogenous decay half-life & shock multipliers.</p>
                    </div>
                    <span class="px-2 py-1 rounded-lg bg-purple-500/20 text-purple-300 font-mono text-xs border border-purple-500/30">
                        {praxist.get('accepted_hypotheses', 0)} / {praxist.get('total_hypotheses', 0)} Accepted
                    </span>
                </div>
                <div class="space-y-2.5">
                    {praxist_items_html or '<p class="text-xs text-slate-500 italic">No PRAXIST experiments logged yet.</p>'}
                </div>
            </div>

            <!-- Episodic Memory Case Studies -->
            <div class="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl space-y-4">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
                            <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                            Episodic Memory Reflections & Failure Modes
                        </h3>
                        <p class="text-xs text-slate-400 mt-0.5">Retain-Recall-Reflect root cause post-mortems for major prediction errors.</p>
                    </div>
                    <span class="px-2 py-1 rounded-lg bg-amber-500/20 text-amber-300 font-mono text-xs border border-amber-500/30">
                        {reflections.get('total_reflections', 0)} Reflections
                    </span>
                </div>
                <div class="space-y-3">
                    {reflections_html or '<p class="text-xs text-slate-500 italic">No episodic reflections indexed yet.</p>'}
                </div>
            </div>
        </div>
    </div>

    <!-- Chart.js Initialization for Model Learning -->
    <script>
    document.addEventListener("DOMContentLoaded", function() {{
        const learningDates = {dates_json};
        const modelMAE = {model_mae_json};
        const naiveMAE = {naive_mae_json};
        const upliftData = {uplift_json};
        const llmWinData = {llm_win_json};

        if (learningDates.length > 0 && document.getElementById('learningCurveChart')) {{
            const ctx1 = document.getElementById('learningCurveChart').getContext('2d');
            new Chart(ctx1, {{
                type: 'line',
                data: {{
                    labels: learningDates,
                    datasets: [
                        {{
                            label: 'Model MAE ($/gal)',
                            data: modelMAE,
                            borderColor: '#38bdf8',
                            backgroundColor: 'rgba(56, 189, 248, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.25
                        }},
                        {{
                            label: 'Naive Baseline MAE ($/gal)',
                            data: naiveMAE,
                            borderColor: '#fbbf24',
                            backgroundColor: 'transparent',
                            borderWidth: 2,
                            borderDash: [4, 4],
                            tension: 0.25
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(51, 65, 85, 0.3)' }}, ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }} }},
                        y: {{ grid: {{ color: 'rgba(51, 65, 85, 0.3)' }}, ticks: {{ color: '#94a3b8', font: {{ size: 10 }}, callback: v => '$' + v.toFixed(2) }} }}
                    }},
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ color: '#cbd5e1', font: {{ size: 11 }} }} }}
                    }}
                }}
            }});
        }}

        if (learningDates.length > 0 && document.getElementById('llmWinRateChart')) {{
            const ctx2 = document.getElementById('llmWinRateChart').getContext('2d');
            new Chart(ctx2, {{
                type: 'line',
                data: {{
                    labels: learningDates,
                    datasets: [
                        {{
                            label: 'LLM Win Rate (%)',
                            data: llmWinData,
                            borderColor: '#818cf8',
                            backgroundColor: 'rgba(129, 140, 248, 0.1)',
                            borderWidth: 2,
                            tension: 0.25,
                            yAxisID: 'y'
                        }},
                        {{
                            label: 'Uplift vs Naive (%)',
                            data: upliftData,
                            borderColor: '#34d399',
                            backgroundColor: 'transparent',
                            borderWidth: 2,
                            borderDash: [3, 3],
                            tension: 0.25,
                            yAxisID: 'y1'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(51, 65, 85, 0.3)' }}, ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }} }},
                        y: {{ type: 'linear', position: 'left', grid: {{ color: 'rgba(51, 65, 85, 0.3)' }}, ticks: {{ color: '#818cf8', callback: v => v.toFixed(0) + '%' }} }},
                        y1: {{ type: 'linear', position: 'right', grid: {{ drawOnChartArea: false }}, ticks: {{ color: '#34d399', callback: v => v.toFixed(0) + '%' }} }}
                    }},
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ color: '#cbd5e1', font: {{ size: 11 }} }} }}
                    }}
                }}
            }});
        }}
    }});
    </script>
    """
    return html
