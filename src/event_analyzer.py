"""
LLM Event Analyzer Module
Extracts structured numerical factor scores from unstructured text headlines and news reports.
Supports live LLM invocation (Google GenAI Gemini API) with a robust rule-based fallback.
"""

import os
import re
import json
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# System prompt for LLM event scoring
LLM_EXTRACTION_PROMPT = """
You are an expert energy market economist and oil commodities analyst.
Analyze the following energy news headline/event description and extract structured numerical impact scores regarding unleaded gasoline and crude oil prices.

Headline/Event: "{headline}"

Return ONLY a raw JSON object with the following fields:
- "geopolitical_risk": float between -1.0 (de-escalation/peace) and +1.0 (war/sanctions/conflict)
- "supply_disruption": float between 0.0 (no disruption) and +1.0 (major refinery/pipeline/shipping shutdown)
- "demand_sentiment": float between -1.0 (severe economic slowdown/recession) and +1.0 (booming demand/driving season)
- "opec_action": float between -1.0 (production surge/price war) and +1.0 (steep supply cuts)
- "overall_price_pressure": float between -1.0 (strong downward price pressure) and +1.0 (strong upward price pressure)

JSON Output:
"""

def extract_event_features_llm(headline: str, api_key: str = None) -> dict:
    """
    Attempts to score a headline using Google Gemini API via `google-genai` or `google.generativeai`.
    Falls back to deterministic rule-based score if API is unavailable.
    """
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if api_key:
        try:
            # Try importing Google GenAI SDK
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=LLM_EXTRACTION_PROMPT.format(headline=headline)
                )
                text = response.text.strip()
            except ImportError:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=api_key)
                model = genai_legacy.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(LLM_EXTRACTION_PROMPT.format(headline=headline))
                text = response.text.strip()
                
            # Clean markdown codeblocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(text)
            return {
                "geopolitical_risk": float(parsed.get("geopolitical_risk", 0.0)),
                "supply_disruption": float(parsed.get("supply_disruption", 0.0)),
                "demand_sentiment": float(parsed.get("demand_sentiment", 0.0)),
                "opec_action": float(parsed.get("opec_action", 0.0)),
                "overall_price_pressure": float(parsed.get("overall_price_pressure", 0.0))
            }
        except Exception as e:
            logger.debug(f"LLM API call failed or not configured ({e}). Using rule-based analyzer.")
            
    return extract_event_features_rule_based(headline)


def extract_event_features_rule_based(headline: str) -> dict:
    """
    Deterministic domain-specific NLP lexicon extractor for energy market headlines.
    Used for offline benchmark reproducibility and fallback.
    """
    text = headline.lower()
    
    # Lexicon patterns
    war_sanction_patterns = ["invad", "war", "conflict", "sanction", "missile", "airstrike", "attack", "hostilities", "houthi"]
    supply_cut_patterns = ["cut", "outage", "disrupt", "explosion", "freeze", "shutdown", "evacuat", "hurricane", "reroute", "delay"]
    demand_weak_patterns = ["recession", "rate hike", "slowdown", "cooling", "inflation fears", "sell-off", "weak demand"]
    opec_cut_patterns = ["opec+ announces cut", "voluntary production cut", "output cut", "solo output cut", "extend voluntary"]
    opec_hike_patterns = ["phase out", "production surge", "increase output", "output increase"]
    
    # Calculate scores
    geo_score = 0.8 if any(p in text for p in war_sanction_patterns) else 0.0
    
    supply_score = 0.0
    if any(p in text for p in supply_cut_patterns):
        supply_score = 0.8 if ("hurricane" in text or "explosion" in text or "cut" in text or "ban" in text) else 0.4
        
    demand_score = -0.6 if any(p in text for p in demand_weak_patterns) else (0.4 if "driving demand" in text or "record highs" in text else 0.0)
    
    opec_score = 0.0
    if any(p in text for p in opec_cut_patterns):
        opec_score = 0.9
    elif any(p in text for p in opec_hike_patterns):
        opec_score = -0.7
    elif "opec" in text and "cut" in text:
        opec_score = 0.6
        
    price_pressure = np.clip(0.3 * geo_score + 0.35 * supply_score + 0.25 * opec_score + 0.2 * demand_score, -1.0, 1.0)
    
    return {
        "geopolitical_risk": round(geo_score, 2),
        "supply_disruption": round(supply_score, 2),
        "demand_sentiment": round(demand_score, 2),
        "opec_action": round(opec_score, 2),
        "overall_price_pressure": round(price_pressure, 2)
    }


def process_event_dataset(events_df: pd.DataFrame, use_llm_api: bool = False) -> pd.DataFrame:
    """
    Takes a DataFrame of events with 'date' and 'headline' columns and appends
    LLM/NLP extracted feature columns.
    """
    logger.info(f"Analyzing {len(events_df)} unstructured event headlines...")
    
    records = []
    api_key = os.environ.get("GEMINI_API_KEY") if use_llm_api else None
    
    for idx, row in events_df.iterrows():
        headline = row['headline']
        scores = extract_event_features_llm(headline, api_key=api_key)
        record = {**row.to_dict(), **scores}
        records.append(record)
        
    scored_df = pd.DataFrame(records)
    return scored_df
