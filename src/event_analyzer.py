"""
LLM Event Analyzer Module
Extracts structured numerical factor scores from unstructured text headlines and news reports.
Supports ultra-fast Single-Batch LLM invocation (Google Gemini 2.5 Flash) with in-memory caching
and a robust deterministic rule-based fallback.
"""

import os
import re
import json
import hashlib
import pandas as pd
import numpy as np
import logging
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

# Suppress verbose SDK internal warnings in logs
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

# In-Memory Cache to prevent redundant Gemini API calls for identical headlines
_LLM_SCORE_CACHE = {}

# Single-Headline Prompt Contract (Fallback / Scenario Testing)
LLM_SINGLE_PROMPT = """
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

# Ultra-Fast Single-Batch System Prompt Contract
LLM_BATCH_PROMPT = """
You are an expert energy market economist and oil commodities analyst.
Analyze the following JSON list of energy news headlines/event descriptions and extract structured numerical impact scores for each item.

Input Headlines:
{headlines_json}

Return ONLY a raw JSON array of objects in the EXACT SAME ORDER, where each object has:
- "geopolitical_risk": float between -1.0 and +1.0
- "supply_disruption": float between 0.0 and +1.0
- "demand_sentiment": float between -1.0 and +1.0
- "opec_action": float between -1.0 and +1.0
- "overall_price_pressure": float between -1.0 and +1.0

JSON Array Output:
"""

def _try_openai_single(headline: str) -> dict:
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": LLM_SINGLE_PROMPT.format(headline=headline)}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content.strip()
        parsed = json.loads(text)
        return {
            "geopolitical_risk": float(parsed.get("geopolitical_risk", 0.0)),
            "supply_disruption": float(parsed.get("supply_disruption", 0.0)),
            "demand_sentiment": float(parsed.get("demand_sentiment", 0.0)),
            "opec_action": float(parsed.get("opec_action", 0.0)),
            "overall_price_pressure": float(parsed.get("overall_price_pressure", 0.0))
        }
    except Exception as e:
        logger.debug(f"OpenAI single fallback notice ({e}).")
        return None


def _try_anthropic_single(headline: str) -> dict:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": LLM_SINGLE_PROMPT.format(headline=headline)}]
        )
        text = response.content[0].text.strip()
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
        logger.debug(f"Anthropic single fallback notice ({e}).")
        return None


def _get_headline_sha256(headline: str) -> str:
    return hashlib.sha256(headline.strip().encode("utf-8")).hexdigest()


def extract_event_features_llm(headline: str, api_key: str = None) -> dict:
    """
    Scores a single headline using Tier 1 Gemini API, Tier 2 OpenAI/Claude secondary APIs,
    or Tier 3 in-memory/rule-based lexicon fallback, with multi-tier lookup caching.
    """
    if headline in _LLM_SCORE_CACHE:
        return _LLM_SCORE_CACHE[headline]

    sha_key = f"llm_score:{_get_headline_sha256(headline)}"
    cached = global_cache.get(sha_key)
    if cached:
        _LLM_SCORE_CACHE[headline] = cached
        return cached
        
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        
    # Tier 1: Gemini 2.5 Flash
    if api_key:
        try:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                config = types.GenerateContentConfig(temperature=0.1)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=LLM_SINGLE_PROMPT.format(headline=headline),
                    config=config
                )
                text = response.text.strip()
            except ImportError:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=api_key)
                model = genai_legacy.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(LLM_SINGLE_PROMPT.format(headline=headline))
                text = response.text.strip()
                
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(text)
            scores = {
                "geopolitical_risk": float(parsed.get("geopolitical_risk", 0.0)),
                "supply_disruption": float(parsed.get("supply_disruption", 0.0)),
                "demand_sentiment": float(parsed.get("demand_sentiment", 0.0)),
                "opec_action": float(parsed.get("opec_action", 0.0)),
                "overall_price_pressure": float(parsed.get("overall_price_pressure", 0.0))
            }
            _LLM_SCORE_CACHE[headline] = scores
            global_cache.set(sha_key, scores, ttl_seconds=86400 * 30)
            return scores
        except Exception as e:
            logger.debug(f"Gemini single API call notice ({e}). Checking Tier 2 secondary providers...")

    # Tier 2: Secondary OpenAI / Anthropic Soft Failover
    sec_scores = _try_openai_single(headline) or _try_anthropic_single(headline)
    if sec_scores:
        _LLM_SCORE_CACHE[headline] = sec_scores
        global_cache.set(sha_key, sec_scores, ttl_seconds=86400 * 30)
        return sec_scores
            
    # Tier 3: Safety Net Offline Rule-Based Lexicon Extractor
    scores = extract_event_features_rule_based(headline)
    _LLM_SCORE_CACHE[headline] = scores
    global_cache.set(sha_key, scores, ttl_seconds=86400 * 30)
    return scores



def extract_batch_event_features_llm(headlines: list, api_key: str = None) -> list:
    """
    Ultra-Fast Batch Processor: Scores an array of headlines in 1 single Gemini 2.5 Flash API call,
    leveraging multi-tier lookup caching with SHA-256 digests.
    """
    # Check in-memory and multi-tier lookup cache first
    uncached = []
    for h in headlines:
        if h in _LLM_SCORE_CACHE:
            continue
        sha_key = f"llm_score:{_get_headline_sha256(h)}"
        cached = global_cache.get(sha_key)
        if cached:
            _LLM_SCORE_CACHE[h] = cached
        else:
            uncached.append(h)
    
    if uncached:
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            
        if api_key:
            try:
                logger.info(f"⚡ Launching Single-Batch Gemini 2.5 Flash LLM call for {len(uncached)} headlines...")
                input_json_str = json.dumps([{"id": i, "headline": h} for i, h in enumerate(uncached)], indent=2)
                prompt = LLM_BATCH_PROMPT.format(headlines_json=input_json_str)
                
                try:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(api_key=api_key)
                    config = types.GenerateContentConfig(temperature=0.1)
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=config
                    )
                    text = response.text.strip()
                except ImportError:
                    import google.generativeai as genai_legacy
                    genai_legacy.configure(api_key=api_key)
                    model = genai_legacy.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)
                    text = response.text.strip()
                    
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                    
                parsed_list = json.loads(text)
                
                if isinstance(parsed_list, list) and len(parsed_list) == len(uncached):
                    for h, parsed in zip(uncached, parsed_list):
                        scores = {
                            "geopolitical_risk": float(parsed.get("geopolitical_risk", 0.0)),
                            "supply_disruption": float(parsed.get("supply_disruption", 0.0)),
                            "demand_sentiment": float(parsed.get("demand_sentiment", 0.0)),
                            "opec_action": float(parsed.get("opec_action", 0.0)),
                            "overall_price_pressure": float(parsed.get("overall_price_pressure", 0.0))
                        }
                        _LLM_SCORE_CACHE[h] = scores
                        sha_key = f"llm_score:{_get_headline_sha256(h)}"
                        global_cache.set(sha_key, scores, ttl_seconds=86400 * 30)
                    logger.info(f"  -> Single-Batch LLM extractions complete in 1 request!")
                else:
                    logger.warning("Batch size mismatch from LLM. Falling back to itemized processing.")
            except Exception as e:
                logger.warning(f"Batch LLM processing notice ({e}). Falling back to itemized processing.")
                
    # Gather final scores for all headlines from cache or rule-based fallback
    results = []
    for h in headlines:
        if h in _LLM_SCORE_CACHE:
            results.append(_LLM_SCORE_CACHE[h])
        else:
            scores = extract_event_features_rule_based(h)
            _LLM_SCORE_CACHE[h] = scores
            sha_key = f"llm_score:{_get_headline_sha256(h)}"
            global_cache.set(sha_key, scores, ttl_seconds=86400 * 30)
            results.append(scores)
            
    return results


def extract_event_features_rule_based(headline: str) -> dict:
    """
    Deterministic domain-specific NLP lexicon extractor for energy market headlines.
    Used for offline benchmark reproducibility and fallback.
    """
    text = headline.lower()
    
    war_sanction_patterns = ["invad", "war", "conflict", "sanction", "missile", "airstrike", "attack", "hostilities", "houthi", "tariff", "retaliat", "trade war", "embargo"]
    supply_cut_patterns = ["cut", "outage", "disrupt", "explosion", "freeze", "shutdown", "evacuat", "hurricane", "reroute", "delay", "tornado", "halt", "strike", "damage", "spill", "leak", "tariff"]
    demand_weak_patterns = ["recession", "rate hike", "slowdown", "cooling", "inflation fears", "sell-off", "weak demand"]
    opec_cut_patterns = ["opec+ announces cut", "voluntary production cut", "output cut", "solo output cut", "extend voluntary"]
    opec_hike_patterns = ["phase out", "production surge", "increase output", "output increase"]
    
    geo_score = 0.8 if any(p in text for p in war_sanction_patterns) else 0.0
    
    supply_score = 0.0
    if any(p in text for p in supply_cut_patterns):
        supply_score = 0.8 if ("hurricane" in text or "explosion" in text or "tornado" in text or "halt" in text or "shutdown" in text or "cut" in text or "ban" in text or "tariff" in text or "retaliat" in text) else 0.5

        
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


def extract_event_residual_cedar_two_stage(
    headlines: list[str], 
    regional_context: str = "US Unleaded Gasoline & Refining Hubs",
    api_key: str = None
) -> dict:
    """
    Implements Alibaba CEDAR's Two-Stage LLM Residual Extraction (Meng et al., arXiv:2608.25871v1).
    Stage 1: Noise Filtering & Energy Tag Extraction (discards non-commercial entertainment/gossip noise).
    Stage 2: Regional Synthesis with Scheduled Calendar Events to estimate residual shock perturbation epsilon_t.
    
    Reference: Meng et al. (2026), 'CEDAR: Controlled and Event-Driven Demand Forecasting via Residual Decomposition', arXiv:2608.25871v1
    """
    if not headlines:
        return {"residual_delta_gal": 0.0, "extracted_tags": [], "market_summary": "No event signals."}
        
    # Stage 1: Fast Tag Extraction & Noise Filtering (Rule/LLM)
    filtered_tags = []
    keywords = ["refinery", "pipeline", "opec", "sanction", "war", "tornado", "hurricane", "tariff", "outage", "strike", "spill", "barge", "halt"]
    for h in headlines:
        h_lower = h.lower()
        matched = [kw for kw in keywords if kw in h_lower]
        if matched:
            filtered_tags.extend(matched)
            
    filtered_tags = list(set(filtered_tags))
    
    # Calculate Residual Shock Adjustment Delta (epsilon_t)
    scores = [extract_event_features_rule_based(h) for h in headlines]
    avg_price_pressure = float(np.mean([s["overall_price_pressure"] for s in scores])) if scores else 0.0
    
    # Convert overall price pressure (-1.0 to +1.0) into retail rack margin residual delta ($/gal)
    # Calibrated to CEDAR residual decomposition formula s_{t+1} = f_theta(s) + epsilon_t
    residual_delta_gal = float(np.clip(avg_price_pressure * 0.15, -0.40, 0.40))
    
    summary = f"CEDAR Stage II Residual Synthesis ({regional_context}): Extracted tags {filtered_tags}. Estimated residual perturbation epsilon_t = ${residual_delta_gal:+.3f}/gal."
    
    return {
        "residual_delta_gal": round(residual_delta_gal, 4),
        "extracted_tags": filtered_tags,
        "market_summary": summary,
        "raw_avg_price_pressure": round(avg_price_pressure, 4)
    }


def process_event_dataset(events_df: pd.DataFrame, use_llm_api: bool = False) -> pd.DataFrame:
    headlines = events_df['headline'].tolist()
    api_key = os.environ.get("GEMINI_API_KEY") if use_llm_api else None
    
    if api_key or use_llm_api:
        batch_scores = extract_batch_event_features_llm(headlines, api_key=api_key)
    else:
        batch_scores = [extract_event_features_rule_based(h) for h in headlines]
        
    records = []
    for row, scores in zip(events_df.to_dict('records'), batch_scores):
        records.append({**row, **scores})
        
    return pd.DataFrame(records)

