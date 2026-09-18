"""
MiroFish Multi-Agent Financial Simulation & Scenario Decision Graph Engine (src/scenario_simulator.py)

Integrates deliberative multi-agent market simulations inspired by MiroFish (Issue #307).
Features a 4-persona deliberative market cohort:
  1. Agent_Refiner: Crack spreads, crude differentials, refinery unit outages, turnaround schedules.
  2. Agent_Logistics: Colonial Pipeline batches, inland river barge drafts (Ohio/Mississippi), terminal rack freight.
  3. Agent_Consumer: Demand destruction thresholds, retail price elasticity, driving season habits.
  4. Agent_Macro: Cboe OVX tail volatility, OPEC+ production policies, central bank policy, tariff declarations.

Includes:
- Feature flag toggle via MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION (default: "0" / False) or request override.
- Single-round batched prompt consensus contract for maximum token efficiency (1 LLM call).
- Tier 3 Deterministic Elasticity Matrix fallback for 100% offline reliability and $0 API spend.
- Behavioral Divergence Index (sigma) quantifying market disagreement across personas.
- Cross-commodity modeling: RBOB Wholesale Gasoline, Heating Oil / ULSD Distillate, and Regional Freight Basis.
- Mermaid and JSON scenario decision graph exports.
"""

import os
import sys
import re
import json
import math
import time
import logging
import argparse
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Feature toggle environment variable name
ENV_ENABLE_MULTI_AGENT_SIM = "MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION"


def is_multi_agent_sim_enabled(override: Optional[bool] = None) -> bool:
    """
    Evaluates whether the 4-persona multi-agent simulation mode is active.
    
    Order of precedence:
    1. Explicit function/request argument `override` (if not None).
    2. Environment variable `MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION` ("1", "true", "yes", "on").
    3. Default: False (0).
    """
    if override is not None:
        return bool(override)
    env_val = os.environ.get(ENV_ENABLE_MULTI_AGENT_SIM, "0").strip().lower()
    return env_val in ("1", "true", "yes", "on")


# Single-Round Batched Prompt Contract (CoSPOT & MiroFish Token Efficiency Paradigm)
COHORT_SIMULATION_PROMPT = """
You are simulating a deliberative energy market consensus between 4 distinct market personas regarding a supply/demand shock event:
Shock Event Headline: "{headline}"
Target Metro / Locale: "{locale}"
Base Gasoline Retail Price: ${base_price:.3f}/gal

You must act as the following 4 personas simultaneously:
1. "Agent_Refiner" (Refinery Operations & 3-2-1 Crack Spread Analyst): Focuses on crude slates, FCCU/Hydrocracker status, refining yield loss, and product substitution.
2. "Agent_Logistics" (Pipeline, River Barge & Waterborne Arbitrageur): Focuses on Colonial Pipeline allocations, Ohio/Mississippi River barge tow drafts, terminal rack inventories, and freight basis.
3. "Agent_Consumer" (Commercial Fleet & Retail Fuel Purchaser): Focuses on demand destruction, commuter driving sensitivity, and retail margin resistance.
4. "Agent_Macro" (Macro Strategist & Geopolitical Energy Analyst): Focuses on Cboe OVX tail volatility, OPEC+ quotas, trade tariffs, and broader macroeconomic sentiment.

Return ONLY a raw JSON object with this exact structure:
{{
  "Agent_Refiner": {{
    "stance": "BULLISH" | "BEARISH" | "NEUTRAL" | "DISRUPTIVE",
    "price_shock_pct": float (e.g. 0.055 for +5.5% or -0.020 for -2.0%),
    "confidence": float (0.0 to 1.0),
    "key_catalysts": ["catalyst 1", "catalyst 2"],
    "risk_factors": ["risk 1", "risk 2"],
    "reasoning": "1-2 sentence concise operational assessment"
  }},
  "Agent_Logistics": {{
    "stance": "BULLISH" | "BEARISH" | "NEUTRAL" | "DISRUPTIVE",
    "price_shock_pct": float,
    "confidence": float,
    "key_catalysts": ["catalyst 1", "catalyst 2"],
    "risk_factors": ["risk 1", "risk 2"],
    "reasoning": "1-2 sentence concise logistical assessment"
  }},
  "Agent_Consumer": {{
    "stance": "BULLISH" | "BEARISH" | "NEUTRAL" | "DISRUPTIVE",
    "price_shock_pct": float,
    "confidence": float,
    "key_catalysts": ["catalyst 1", "catalyst 2"],
    "risk_factors": ["risk 1", "risk 2"],
    "reasoning": "1-2 sentence concise retail demand assessment"
  }},
  "Agent_Macro": {{
    "stance": "BULLISH" | "BEARISH" | "NEUTRAL" | "DISRUPTIVE",
    "price_shock_pct": float,
    "confidence": float,
    "key_catalysts": ["catalyst 1", "catalyst 2"],
    "risk_factors": ["risk 1", "risk 2"],
    "reasoning": "1-2 sentence concise macroeconomic assessment"
  }},
  "consensus_summary": "Synthesized 2-3 sentence consensus explaining the net market equilibrium and primary disagreement drivers."
}}
"""


# Tier 3 Deterministic Elasticity Matrix (Calibrated historical sensitivities for 100% offline fallback)
TIER3_DETERMINISTIC_PERSONA_PROFILES: Dict[str, Dict[str, Any]] = {
    "refinery_outage": {
        "Agent_Refiner": {
            "stance": "DISRUPTIVE",
            "shock_multiplier": 1.35,
            "confidence": 0.92,
            "catalysts": ["Unplanned unit trip", "Crack spread expansion", "Secondary unit feedstock backup"],
            "risks": ["Extended turnaround duration", "Catalyst bed contamination"],
            "reasoning": "Refinery unit outage triggers immediate local supply deficits and spikes regional 3-2-1 crack spreads."
        },
        "Agent_Logistics": {
            "stance": "BULLISH",
            "shock_multiplier": 1.15,
            "confidence": 0.85,
            "catalysts": ["Inter-PADD supply rerouting", "Terminal rack drawdown", "Spot trucking freight premiums"],
            "risks": ["Pipeline batch delays", "Rack allocations at secondary terminals"],
            "reasoning": "Secondary terminals must draw down safety stock and arrange replacement pipeline batches."
        },
        "Agent_Consumer": {
            "stance": "NEUTRAL",
            "shock_multiplier": 0.70,
            "confidence": 0.78,
            "catalysts": ["Inelastic near-term commute demand", "Delayed retail pump pass-through"],
            "risks": ["Consumer price resistance above local psychological thresholds"],
            "reasoning": "Retail consumer demand remains initially inelastic, though sustained price spikes induce marginal demand destruction."
        },
        "Agent_Macro": {
            "stance": "BULLISH",
            "shock_multiplier": 0.85,
            "confidence": 0.80,
            "catalysts": ["Localized product crack firming", "Short-term regional inventory tightness"],
            "risks": ["Broader macroeconomic demand headwinds"],
            "reasoning": "Localized operational shock creates moderate upward pricing support without systemic crude market repricing."
        }
    },
    "pipeline_disruption": {
        "Agent_Refiner": {
            "stance": "BEARISH",
            "shock_multiplier": 0.65,
            "confidence": 0.85,
            "catalysts": ["Origin refinery tank farm congestion", "Back-pressure run-rate cuts"],
            "risks": ["Full origin storage forcing unplanned rate curtailments"],
            "reasoning": "Refiners at the pipeline origin face storage bottlenecks and may curtail throughput if takeaway halts."
        },
        "Agent_Logistics": {
            "stance": "DISRUPTIVE",
            "shock_multiplier": 1.50,
            "confidence": 0.95,
            "catalysts": ["Mainline batch freeze", "Emergency barge/truck reallocations", "Terminal rack runouts"],
            "risks": ["Severe regional basis blowout along downstream delivery nodes"],
            "reasoning": "Mainline transit halt starves destination terminal racks, creating acute freight basis spikes and spot delivery delays."
        },
        "Agent_Consumer": {
            "stance": "BULLISH",
            "shock_multiplier": 1.10,
            "confidence": 0.82,
            "catalysts": ["Panic buying runs at retail stations", "Local station dry-outs"],
            "risks": ["Rapid retail pump markup by station operators"],
            "reasoning": "Panic buying and local station outages amplify spot retail pricing above underlying wholesale cost spikes."
        },
        "Agent_Macro": {
            "stance": "BULLISH",
            "shock_multiplier": 0.85,
            "confidence": 0.88,
            "catalysts": ["Cboe OVX tail premium", "Energy infrastructure vulnerability focus"],
            "risks": ["Regulatory emergency waiver intervention (Jones Act / RVP)"],
            "reasoning": "Critical infrastructure disruptions elevate market risk premiums until emergency waivers or line restarts occur."
        }
    },
    "meteorological": {
        "Agent_Refiner": {
            "stance": "DISRUPTIVE",
            "shock_multiplier": 1.30,
            "confidence": 0.90,
            "catalysts": ["Precautionary refinery shutdowns", "Storm surge / flood risk", "Power grid instability"],
            "risks": ["Prolonged restart sequence after severe weather events"],
            "reasoning": "Coastal or convective weather forces precautionary shutdowns and damages auxiliary grid / water treatment units."
        },
        "Agent_Logistics": {
            "stance": "DISRUPTIVE",
            "shock_multiplier": 1.25,
            "confidence": 0.88,
            "catalysts": ["Port and marine terminal closures", "Barge navigation halts", "Roadway flooding"],
            "risks": ["Channel siltation and tanker draft limitations"],
            "reasoning": "Marine berths, ports, and inland waterway routes halt operations, preventing both crude delivery and product export."
        },
        "Agent_Consumer": {
            "stance": "BEARISH",
            "shock_multiplier": 0.60,
            "confidence": 0.75,
            "catalysts": ["Severe storm driving cessation", "Evacuation driving temporary surge followed by demand collapse"],
            "risks": ["Prolonged regional economic paralysis"],
            "reasoning": "Post-storm localized travel halts sharply compress regional fuel consumption despite initial pre-storm hoarding."
        },
        "Agent_Macro": {
            "stance": "BULLISH",
            "shock_multiplier": 1.05,
            "confidence": 0.86,
            "catalysts": ["Gulf of Mexico crude shut-ins (BSEE)", "National inventory deficit expectations"],
            "risks": ["Federal Strategic Petroleum Reserve (SPR) release threat"],
            "reasoning": "Severe meteorological events create simultaneous upstream crude shut-ins and downstream product outages."
        }
    },
    "hydrological": {
        "Agent_Refiner": {
            "stance": "BULLISH",
            "shock_multiplier": 1.10,
            "confidence": 0.82,
            "catalysts": ["Refinery cooling water thermal limits", "Effluent discharge curtailment"],
            "risks": ["Mandatory run-rate curtailments during peak summer heat or extreme high water"],
            "reasoning": "Extreme river temperatures or discharge limits constrain cooling water efficiency, capping refinery utilization."
        },
        "Agent_Logistics": {
            "stance": "DISRUPTIVE",
            "shock_multiplier": 1.40,
            "confidence": 0.92,
            "catalysts": ["Low-water barge draft cuts (e.g. 9ft down to 7.5ft)", "Tow size reductions", "Channel dredging delays"],
            "risks": ["Inland barge freight rate spikes across Mississippi/Ohio corridors"],
            "reasoning": "Low or high water drafts force 20-30% lighter barge loadings, causing waterborne transport shortages and freight basis spikes."
        },
        "Agent_Consumer": {
            "stance": "NEUTRAL",
            "shock_multiplier": 0.75,
            "confidence": 0.80,
            "catalysts": ["Gradual wholesale cost pass-through", "Normal seasonal consumption"],
            "risks": ["Secondary rack pass-through to retail pumps"],
            "reasoning": "Consumers experience gradual wholesale-to-retail price creep without immediate supply shortages."
        },
        "Agent_Macro": {
            "stance": "NEUTRAL",
            "shock_multiplier": 0.80,
            "confidence": 0.78,
            "catalysts": ["Inland supply chain friction", "Regional feedstock supply adjustments"],
            "risks": ["Protracted drought conditions across midcontinent river basins"],
            "reasoning": "Hydrological bottlenecks create localized regional basis premiums without altering global crude fundamentals."
        }
    },
    "geopolitical": {
        "Agent_Refiner": {
            "stance": "BULLISH",
            "shock_multiplier": 1.15,
            "confidence": 0.88,
            "catalysts": ["Global crude slate cost inflation", "Heavy/sour crude differential widening"],
            "risks": ["Feedstock substitution costs and shipping freight surcharges"],
            "reasoning": "Geopolitical chokepoint risks and sanctions escalate crude acquisition costs, squeezing refinery gross margins."
        },
        "Agent_Logistics": {
            "stance": "BULLISH",
            "shock_multiplier": 1.25,
            "confidence": 0.90,
            "catalysts": ["Global tanker voyage rerouting (Cape of Good Hope)", "War-risk marine insurance premiums"],
            "risks": ["Extended tanker transit times and port demurrage"],
            "reasoning": "Maritime chokepoint disruptions inflate maritime ton-mile demand and prompt sharp shipping insurance surcharges."
        },
        "Agent_Consumer": {
            "stance": "BEARISH",
            "shock_multiplier": 0.70,
            "confidence": 0.84,
            "catalysts": ["Pump shock demand elasticity", "Consumer discretionary budget tightening"],
            "risks": ["Widespread demand destruction at retail fuel stations"],
            "reasoning": "Sustained global crude inflation triggers retail demand friction, curtailing discretionary highway miles."
        },
        "Agent_Macro": {
            "stance": "DISRUPTIVE",
            "shock_multiplier": 1.45,
            "confidence": 0.94,
            "catalysts": ["Cboe OVX options volatility spike", "OPEC+ supply quota responses", "Global macroeconomic stagflation risk"],
            "risks": ["Retaliatory energy sanction escalations and central bank rate actions"],
            "reasoning": "Geopolitical chokepoints and embargoes generate strong macro tail risk premiums and aggressive speculative bidding."
        }
    },
    "regulatory_spec": {
        "Agent_Refiner": {
            "stance": "DISRUPTIVE",
            "shock_multiplier": 1.35,
            "confidence": 0.94,
            "catalysts": ["Boutique summer RVP blend switchover", "Low-RVP alkylate/reformate blending costs"],
            "risks": ["Off-spec blending batches during turnaround transitions"],
            "reasoning": "Statutory transition to low-RVP summer blends removes low-cost butane components, driving up refinery blending costs."
        },
        "Agent_Logistics": {
            "stance": "BULLISH",
            "shock_multiplier": 1.15,
            "confidence": 0.88,
            "catalysts": ["Terminal tank flushing deadlines", "Segregated boutique fuel batch transport"],
            "risks": ["Stranded winter-blend inventories at secondary terminals"],
            "reasoning": "Terminals must strictly segregate and flush storage tanks prior to statutory deadlines to ensure zero cross-contamination."
        },
        "Agent_Consumer": {
            "stance": "NEUTRAL",
            "shock_multiplier": 0.80,
            "confidence": 0.82,
            "catalysts": ["Seasonal spring retail pump increases", "Commencement of spring driving season"],
            "risks": ["Consumer fatigue over recurring seasonal spec increases"],
            "reasoning": "Retail pump prices predictably absorb summer-blend cost increases alongside spring seasonal driving recovery."
        },
        "Agent_Macro": {
            "stance": "NEUTRAL",
            "shock_multiplier": 0.75,
            "confidence": 0.80,
            "catalysts": ["Predictable regulatory calendar transition", "Regional boutique fuel market bifurcation"],
            "risks": ["EPA emergency temporary RVP waiver intervention"],
            "reasoning": "Regulatory transitions represent structured seasonal events with well-understood regional price premiums."
        }
    }
}


def _classify_scenario_category(scenario_id: str, headline: str = "") -> str:
    """Helper to classify a scenario or headline into a deterministic persona profile category."""
    text = (scenario_id + " " + headline).lower()
    if any(k in text for k in ["hurricane", "vortex", "tornado", "freeze", "microburst", "storm", "blizzard"]):
        return "meteorological"
    elif any(k in text for k in ["river", "hydrological", "cooling water", "thermal", "drought", "barge", "waterway", "carquinez"]):
        return "hydrological"
    elif any(k in text for k in ["pipeline", "keystone", "colonial", "selma", "tank farm", "batch"]):
        return "pipeline_disruption"
    elif any(k in text for k in ["refinery", "fccu", "hydrocracker", "turnaround", "sinclair", "marathon", "chevron", "catlettsburg"]):
        return "refinery_outage"
    elif any(k in text for k in ["carb", "rvp", "summer-blend", "regulatory", "spec", "rin", "excise", "tax"]):
        return "regulatory_spec"
    elif any(k in text for k in ["hormuz", "suez", "red sea", "opec", "tariff", "sanction", "war", "blockade", "geopolitical"]):
        return "geopolitical"
    return "refinery_outage"


def _evaluate_tier3_deterministic_cohort(
    scenario_id: str,
    headline: str,
    locale: str,
    base_price: float,
    base_shock_pct: float
) -> Dict[str, Any]:
    """
    Constructs deterministic 4-persona deliberative assessments using the Tier 3 Elasticity Matrix.
    Provides 100% offline fallback with $0 cost.
    """
    cat = _classify_scenario_category(scenario_id, headline)
    profile = TIER3_DETERMINISTIC_PERSONA_PROFILES.get(cat, TIER3_DETERMINISTIC_PERSONA_PROFILES["refinery_outage"])

    personas = {}
    weighted_shock_sum = 0.0
    total_conf = 0.0
    shock_values = []

    for p_name in ["Agent_Refiner", "Agent_Logistics", "Agent_Consumer", "Agent_Macro"]:
        p_cfg = profile[p_name]
        mult = p_cfg["shock_multiplier"]
        conf = p_cfg["confidence"]
        
        # Scale persona shock percentage based on baseline scenario magnitude
        p_shock = round(base_shock_pct * mult, 4)
        shock_values.append(p_shock)
        
        weighted_shock_sum += p_shock * conf
        total_conf += conf

        personas[p_name] = {
            "persona_name": p_name,
            "role_title": {
                "Agent_Refiner": "Refinery Operations & Crack Spread Analyst",
                "Agent_Logistics": "Pipeline, Barge & Waterborne Arbitrageur",
                "Agent_Consumer": "Commercial Fleet & Retail Fuel Purchaser",
                "Agent_Macro": "Macro Strategist & Geopolitical Analyst"
            }[p_name],
            "stance": p_cfg["stance"],
            "price_shock_pct": p_shock,
            "confidence": conf,
            "key_catalysts": p_cfg["catalysts"],
            "risk_factors": p_cfg["risks"],
            "reasoning": p_cfg["reasoning"]
        }

    # Calculate Consensus & Behavioral Divergence Index (sigma)
    consensus_shock_pct = round(weighted_shock_sum / max(total_conf, 0.001), 4)
    
    # Population standard deviation of persona shocks represents divergence
    mean_shock = sum(shock_values) / len(shock_values)
    variance = sum((s - mean_shock) ** 2 for s in shock_values) / len(shock_values)
    divergence_index = round(math.sqrt(variance), 4)

    # Cross-Commodity Impacts
    rbob_delta_dollars = round(base_price * consensus_shock_pct, 3)
    # HO Distillate impact typically tracks 1.05x - 1.25x of refining/geopolitical shocks
    ho_mult = 1.15 if cat in ["geopolitical", "meteorological", "refinery_outage"] else 0.90
    ho_distillate_delta_dollars = round(base_price * consensus_shock_pct * ho_mult, 3)
    # Regional Freight Basis in cents/gal
    basis_delta_cents = round(consensus_shock_pct * base_price * 100 * (0.35 if cat in ["pipeline_disruption", "hydrological"] else 0.15), 2)

    consensus_summary = (
        f"Consensus evaluation for {locale.upper()} indicates a {consensus_shock_pct*100:+.2f}% net price equilibrium shock. "
        f"Primary upward driver is {personas['Agent_Logistics']['persona_name']} ({personas['Agent_Logistics']['stance']}), "
        f"balanced against demand elasticity moderation from {personas['Agent_Consumer']['persona_name']}. "
        f"Behavioral market divergence index is {divergence_index:.3f}."
    )

    return {
        "status": "success",
        "provider_used": "tier_3_deterministic_matrix",
        "scenario_id": scenario_id,
        "scenario_category": cat,
        "headline": headline,
        "locale": locale,
        "baseline_price_per_gal": base_price,
        "personas": personas,
        "consensus": {
            "price_shock_pct": consensus_shock_pct,
            "divergence_index": divergence_index,
            "rbob_shock_dollars_per_gal": rbob_delta_dollars,
            "ho_distillate_shock_dollars_per_gal": ho_distillate_delta_dollars,
            "regional_freight_basis_delta_cents": basis_delta_cents,
            "consensus_stance": "BULLISH" if consensus_shock_pct > 0.01 else ("BEARISH" if consensus_shock_pct < -0.01 else "NEUTRAL"),
            "consensus_summary": consensus_summary
        }
    }


def _call_gemini_single_round_cohort(
    headline: str,
    locale: str,
    base_price: float,
    api_key: str
) -> Optional[Dict[str, Any]]:
    """Invokes Google Gemini with the single-round 4-persona prompt contract."""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        
        prompt = COHORT_SIMULATION_PROMPT.format(
            headline=headline,
            locale=locale,
            base_price=base_price
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=1024
            )
        )
        if response and response.text:
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```[a-zA-Z]*\n", "", text)
                text = re.sub(r"\n```$", "", text).strip()
            parsed = json.loads(text)
            return parsed
    except Exception as e:
        logger.debug(f"Gemini multi-agent cohort simulation API notice: {e}")
    return None


def export_scenario_decision_graph_mermaid(simulation_result: Dict[str, Any]) -> str:
    """
    Generates clean, syntactically valid Mermaid flowchart markup illustrating
    the scenario catalyst, the 4 persona assessments, market consensus, and cross-commodity deltas.
    """
    scenario_name = simulation_result.get("scenario_name", simulation_result.get("scenario_id", "Shock Catalyst"))
    clean_title = scenario_name.replace('"', '').replace("'", "").replace("(", "").replace(")", "")
    if len(clean_title) > 40:
        clean_title = clean_title[:37] + "..."

    personas = simulation_result.get("personas", {})
    consensus = simulation_result.get("consensus", {})

    refiner = personas.get("Agent_Refiner", {})
    logistics = personas.get("Agent_Logistics", {})
    consumer = personas.get("Agent_Consumer", {})
    macro = personas.get("Agent_Macro", {})

    r_pct = refiner.get("price_shock_pct", 0.0) * 100
    r_stance = refiner.get("stance", "NEUTRAL")

    l_pct = logistics.get("price_shock_pct", 0.0) * 100
    l_stance = logistics.get("stance", "NEUTRAL")

    c_pct = consumer.get("price_shock_pct", 0.0) * 100
    c_stance = consumer.get("stance", "NEUTRAL")

    m_pct = macro.get("price_shock_pct", 0.0) * 100
    m_stance = macro.get("stance", "NEUTRAL")

    con_pct = consensus.get("price_shock_pct", 0.0) * 100
    divergence = consensus.get("divergence_index", 0.0)
    rbob_delta = consensus.get("rbob_shock_dollars_per_gal", 0.0)
    ho_delta = consensus.get("ho_distillate_shock_dollars_per_gal", 0.0)
    basis_delta = consensus.get("regional_freight_basis_delta_cents", 0.0)

    mermaid_str = f"""flowchart TD
    Catalyst["⚡ Shock Event: {clean_title}"]
    
    Catalyst --> Refiner["🏭 Agent_Refiner\n[{r_stance}] {r_pct:+.1f}%"]
    Catalyst --> Logistics["🚚 Agent_Logistics\n[{l_stance}] {l_pct:+.1f}%"]
    Catalyst --> Consumer["🚗 Agent_Consumer\n[{c_stance}] {c_pct:+.1f}%"]
    Catalyst --> Macro["📊 Agent_Macro\n[{m_stance}] {m_pct:+.1f}%"]
    
    Refiner --> Consensus["🎯 Equilibrium Consensus: {con_pct:+.2f}%\n(Disagreement σ: {divergence:.3f})"]
    Logistics --> Consensus
    Consumer --> Consensus
    Macro --> Consensus
    
    Consensus --> OutGas["⛽ RBOB Delta: ${rbob_delta:+.3f}/gal"]
    Consensus --> OutDiesel["🚛 ULSD/HO Delta: ${ho_delta:+.3f}/gal"]
    Consensus --> OutBasis["📍 Regional Freight Basis: {basis_delta:+.1f}¢/gal"]
    
    style Catalyst fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc
    style Consensus fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#f8fafc
    style OutGas fill:#064e3b,stroke:#10b981,stroke-width:1px,color:#f8fafc
    style OutDiesel fill:#1e1b4b,stroke:#818cf8,stroke-width:1px,color:#f8fafc
    style OutBasis fill:#3730a3,stroke:#a5b4fc,stroke-width:1px,color:#f8fafc"""

    return mermaid_str


def simulate_market_cohort(
    scenario_id: str,
    headline: Optional[str] = None,
    locale: str = "national",
    base_price: float = 3.184,
    base_shock_pct: float = 0.05,
    scenario_name: Optional[str] = None,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Executes the 4-persona deliberative market simulation for a given scenario shock.
    
    Returns structured simulation results containing individual persona assessments,
    confidence-weighted consensus, behavioral divergence index, cross-commodity impact vectors,
    and Mermaid decision graph markup.
    """
    target_headline = headline or scenario_name or scenario_id.replace("_", " ").title()
    target_name = scenario_name or scenario_id.replace("_", " ").title()

    api_key = os.environ.get("GEMINI_API_KEY") if use_llm else None
    parsed_llm = None
    provider_used = "tier_3_deterministic_matrix"

    if api_key and use_llm:
        parsed_llm = _call_gemini_single_round_cohort(target_headline, locale, base_price, api_key)
        if parsed_llm and all(p in parsed_llm for p in ["Agent_Refiner", "Agent_Logistics", "Agent_Consumer", "Agent_Macro"]):
            provider_used = "tier_1_gemini"

    if parsed_llm and provider_used == "tier_1_gemini":
        personas = {}
        weighted_shock_sum = 0.0
        total_conf = 0.0
        shock_values = []

        for p_name in ["Agent_Refiner", "Agent_Logistics", "Agent_Consumer", "Agent_Macro"]:
            p_data = parsed_llm[p_name]
            p_shock = float(p_data.get("price_shock_pct", 0.0))
            conf = float(p_data.get("confidence", 0.8))
            shock_values.append(p_shock)

            weighted_shock_sum += p_shock * conf
            total_conf += conf

            personas[p_name] = {
                "persona_name": p_name,
                "role_title": {
                    "Agent_Refiner": "Refinery Operations & Crack Spread Analyst",
                    "Agent_Logistics": "Pipeline, Barge & Waterborne Arbitrageur",
                    "Agent_Consumer": "Commercial Fleet & Retail Fuel Purchaser",
                    "Agent_Macro": "Macro Strategist & Geopolitical Analyst"
                }[p_name],
                "stance": p_data.get("stance", "NEUTRAL"),
                "price_shock_pct": p_shock,
                "confidence": conf,
                "key_catalysts": p_data.get("key_catalysts", []),
                "risk_factors": p_data.get("risk_factors", []),
                "reasoning": p_data.get("reasoning", "")
            }

        consensus_shock_pct = round(weighted_shock_sum / max(total_conf, 0.001), 4)
        mean_shock = sum(shock_values) / len(shock_values)
        variance = sum((s - mean_shock) ** 2 for s in shock_values) / len(shock_values)
        divergence_index = round(math.sqrt(variance), 4)

        rbob_delta_dollars = round(base_price * consensus_shock_pct, 3)
        ho_distillate_delta_dollars = round(base_price * consensus_shock_pct * 1.15, 3)
        basis_delta_cents = round(consensus_shock_pct * base_price * 100 * 0.20, 2)

        result = {
            "status": "success",
            "provider_used": provider_used,
            "scenario_id": scenario_id,
            "scenario_name": target_name,
            "headline": target_headline,
            "locale": locale,
            "baseline_price_per_gal": base_price,
            "personas": personas,
            "consensus": {
                "price_shock_pct": consensus_shock_pct,
                "divergence_index": divergence_index,
                "rbob_shock_dollars_per_gal": rbob_delta_dollars,
                "ho_distillate_shock_dollars_per_gal": ho_distillate_delta_dollars,
                "regional_freight_basis_delta_cents": basis_delta_cents,
                "consensus_stance": "BULLISH" if consensus_shock_pct > 0.01 else ("BEARISH" if consensus_shock_pct < -0.01 else "NEUTRAL"),
                "consensus_summary": parsed_llm.get("consensus_summary", "")
            }
        }
    else:
        # Fall back to Tier 3 Deterministic Elasticity Matrix
        result = _evaluate_tier3_deterministic_cohort(
            scenario_id=scenario_id,
            headline=target_headline,
            locale=locale,
            base_price=base_price,
            base_shock_pct=base_shock_pct
        )
        result["scenario_name"] = target_name

    # Attach Mermaid Decision Graph Markup
    result["decision_graph_mermaid"] = export_scenario_decision_graph_mermaid(result)
    result["is_multi_agent_mode"] = True
    return result


def main():
    """CLI Tooling for standalone multi-agent simulation testing."""
    parser = argparse.ArgumentParser(description="MiroFish Multi-Agent Financial Scenario Simulator for Midgley Fuel Markets")
    parser.add_argument("--scenario", type=str, default="hormuz_blockade", help="Scenario ID to simulate")
    parser.add_argument("--locale", type=str, default="national", help="Target locale code (e.g. national, tulsa, newark, oakland)")
    parser.add_argument("--base-price", type=float, default=3.184, help="Baseline retail fuel price ($/gal)")
    parser.add_argument("--shock-pct", type=float, default=0.05, help="Baseline shock percentage (e.g. 0.05 for +5%%)")
    parser.add_argument("--headline", type=str, default=None, help="Custom headline or breaking news prose")
    parser.add_argument("--no-llm", action="store_true", help="Force Tier 3 Deterministic Elasticity Matrix (offline zero-cost)")
    parser.add_argument("--json", action="store_true", help="Output full raw JSON payload")

    args = parser.parse_args()

    enabled = is_multi_agent_sim_enabled()
    print(f"\n[Midgley Multi-Agent Simulation Engine]")
    print(f"Feature Flag (MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION): {'ON (Active)' if enabled else 'OFF (Linear Default)'}")
    print(f"Simulating Scenario: {args.scenario} | Locale: {args.locale} | Base: ${args.base_price:.3f}/gal\n")

    res = simulate_market_cohort(
        scenario_id=args.scenario,
        headline=args.headline,
        locale=args.locale,
        base_price=args.base_price,
        base_shock_pct=args.shock_pct,
        use_llm=not args.no_llm
    )

    if args.json:
        print(json.dumps(res, indent=2))
        return

    print(f"Provider: {res['provider_used']}")
    print(f"Consensus Stance: {res['consensus']['consensus_stance']} | Price Shock: {res['consensus']['price_shock_pct']*100:+.2f}%")
    print(f"Divergence Index (σ): {res['consensus']['divergence_index']:.4f}")
    print(f"RBOB Impact: ${res['consensus']['rbob_shock_dollars_per_gal']:+.3f}/gal | ULSD Impact: ${res['consensus']['ho_distillate_shock_dollars_per_gal']:+.3f}/gal")
    print(f"Regional Freight Basis: {res['consensus']['regional_freight_basis_delta_cents']:+.2f}¢/gal")
    print(f"\nConsensus Summary:\n{res['consensus']['consensus_summary']}\n")

    print("-" * 60)
    print("4-PERSONA DELIBERATION BREAKDOWN:")
    for p_name, p in res["personas"].items():
        print(f"  • {p_name} ({p['role_title']}): [{p['stance']}] {p['price_shock_pct']*100:+.1f}% (Conf: {p['confidence']:.2f})")
        print(f"    Reasoning: {p['reasoning']}")
    print("-" * 60)
    print("\nMERMAID DECISION GRAPH:\n")
    print(res["decision_graph_mermaid"])
    print()


if __name__ == "__main__":
    main()
