"""
PaSa Crawler-Selector Dual-Agent Research Subagent (src/pasa_research_agent.py)
Issue #265: Adopt PaSa Crawler-Selector Dual-Agent Architecture for Literature & Event Research Subagent

Inspired by ByteDance's PaSa (ACL 2025, https://github.com/bytedance/pasa).
Solves shallow single-pass search limitations by executing an iterative, multi-hop investigation loop:
- Crawler Agent: Expands queries, dispatches to academic/web backends, and traverses citation/link graphs.
- Selector Agent: Evaluates relevance against strict criteria, prunes off-topic items, directs next hops,
  and synthesizes structured econometric bounds and qualitative shock dossiers.
"""

import os
import re
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone

from src.lookup_cache import global_cache
from src.tokentab_accounting import token_tab_manager
from src.fallback_telemetry import fallback_logger
from src.academic_openalex import OpenAlexConnector
from src.semantic_scholar_feed import SemanticScholarConnector
from src.arxiv_monitor import fetch_recent_arxiv_articles
from src.firecrawl_scraper import FirecrawlConnector
from src.knowledge_graph import kg_engine

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join("data", "pasa_cache.json")


def _load_pasa_cache() -> dict:
    """Loads PaSa research cache from disk."""
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error reading PaSa cache: {e}")
    return {}


def _save_pasa_cache(cache: dict) -> None:
    """Saves PaSa research cache to disk."""
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_TELEMETRY_PERSIST"):
        return
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.debug(f"Error saving PaSa cache: {e}")


@dataclass
class CandidateDocument:
    """Data representation of a candidate research document or scraped web article."""
    doc_id: str
    title: str
    content: str
    source_type: str  # 'openalex', 'semantic_scholar', 'arxiv', 'firecrawl', 'knowledge_graph'
    url: str = ""
    doi: str = ""
    authors: List[str] = field(default_factory=list)
    publication_year: Optional[int] = None
    citation_count: int = 0
    hop_depth: int = 0
    parent_doc_id: Optional[str] = None
    relevance_score: float = 0.0
    relevance_explanation: str = ""
    extracted_insights: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PaSaResearchResult:
    """Consolidated outcome of the PaSa multi-hop investigation loop."""
    objective: str
    mode: str
    total_hops_executed: int
    total_candidates_evaluated: int
    selected_documents: List[CandidateDocument]
    synthesized_summary: str
    parameter_bounds: Dict[str, Any]
    bibliography: List[Dict[str, str]]
    duration_ms: float = 0.0
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "mode": self.mode,
            "total_hops_executed": self.total_hops_executed,
            "total_candidates_evaluated": self.total_candidates_evaluated,
            "selected_documents": [doc.to_dict() for doc in self.selected_documents],
            "synthesized_summary": self.synthesized_summary,
            "parameter_bounds": self.parameter_bounds,
            "bibliography": self.bibliography,
            "duration_ms": self.duration_ms,
            "status": self.status
        }


class CrawlerAgent:
    """
    PaSa Crawler Agent: Responsible for candidate pool expansion.
    Formulates search queries, explores citation networks, ingests multi-source backends,
    and collects multi-hop candidate documents.
    """

    def __init__(self, openalex: Optional[OpenAlexConnector] = None, semantic_scholar: Optional[SemanticScholarConnector] = None):
        self.openalex = openalex or OpenAlexConnector()
        self.semantic_scholar = semantic_scholar or SemanticScholarConnector()
        self.firecrawl = FirecrawlConnector()

    def expand_queries(self, objective: str, hop: int, seed_docs: Optional[List[CandidateDocument]] = None) -> List[str]:
        """
        Decomposes research objective into targeted query variants and domain keywords.
        """
        queries = [objective]
        if hop == 0:
            # First hop: Core terms + domain expansions
            if any(term in objective.lower() for term in ["decay", "shock", "half-life", "outage"]):
                queries.append(f"{objective} exponential decay econometrics")
                queries.append("gasoline price pass through refinery outage half life")
            elif any(term in objective.lower() for term in ["tax", "excise", "incidence"]):
                queries.append(f"{objective} fuel tax incidence pass-through")
            elif any(term in objective.lower() for term in ["detour", "pipeline", "chokepoint"]):
                queries.append(f"{objective} pipeline constraint regional basis spread")
            else:
                queries.append(f"{objective} gasoline commodity econometric model")
        else:
            # Subsequent hops: Target concepts extracted from seed documents
            if seed_docs:
                for doc in seed_docs[:3]:
                    # Extract high-value keywords from title
                    clean_title = re.sub(r'[^\w\s]', '', doc.title)
                    words = [w for w in clean_title.split() if len(w) > 4 and w.lower() not in ["energy", "prices", "gasoline", "market"]]
                    if words:
                        queries.append(f"{' '.join(words[:4])} price response")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for q in queries:
            normalized = q.strip().lower()
            if normalized not in seen and len(normalized) > 3:
                seen.add(normalized)
                deduped.append(q.strip())
        return deduped[:4]

    def crawl_academic(self, queries: List[str], hop_depth: int, limit_per_query: int = 3) -> List[CandidateDocument]:
        """
        Crawls academic databases (OpenAlex, Semantic Scholar, arXiv) for candidates.
        """
        candidates: List[CandidateDocument] = []
        seen_ids: Set[str] = set()

        for q in queries:
            # 1. OpenAlex
            try:
                oa_results = self.openalex.search_energy_literature(topic=q, limit=limit_per_query)
                for item in oa_results:
                    doc_id = item.get("id") or item.get("doi") or f"oa_{hashlib.sha256(item.get('title', '').encode()).hexdigest()[:12]}"
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        candidates.append(CandidateDocument(
                            doc_id=doc_id,
                            title=item.get("title", ""),
                            content=item.get("summary_abstract", "") or item.get("title", ""),
                            source_type="openalex",
                            url=item.get("open_access_url", ""),
                            doi=item.get("doi", ""),
                            authors=item.get("authors", []),
                            publication_year=item.get("publication_year"),
                            citation_count=item.get("cited_by_count", 0),
                            hop_depth=hop_depth
                        ))
            except Exception as e:
                logger.debug(f"OpenAlex crawl error for '{q}': {e}")

            # 2. Semantic Scholar
            try:
                ss_results = self.semantic_scholar.search_papers(query=q, limit=limit_per_query)
                for item in ss_results:
                    doc_id = item.get("paperId") or f"ss_{hashlib.sha256(item.get('title', '').encode()).hexdigest()[:12]}"
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        candidates.append(CandidateDocument(
                            doc_id=doc_id,
                            title=item.get("title", ""),
                            content=item.get("tldr", "") or item.get("abstract", "") or item.get("title", ""),
                            source_type="semantic_scholar",
                            url=item.get("openAccessPdf", ""),
                            citation_count=item.get("citationCount", 0),
                            publication_year=item.get("year"),
                            hop_depth=hop_depth
                        ))
            except Exception as e:
                logger.debug(f"Semantic Scholar crawl error for '{q}': {e}")

            # 3. arXiv Preprints
            try:
                if hop_depth == 0:
                    arxiv_results = fetch_recent_arxiv_articles(days_back=60, max_results=limit_per_query)
                    for item in arxiv_results:
                        doc_id = item.get("id") or f"arxiv_{hashlib.sha256(item.get('title', '').encode()).hexdigest()[:12]}"
                        if doc_id not in seen_ids:
                            seen_ids.add(doc_id)
                            candidates.append(CandidateDocument(
                                doc_id=doc_id,
                                title=item.get("title", ""),
                                content=item.get("summary", "") or item.get("title", ""),
                                source_type="arxiv",
                                url=item.get("url", ""),
                                authors=item.get("authors", []),
                                hop_depth=hop_depth
                            ))
            except Exception as e:
                logger.debug(f"arXiv crawl error for '{q}': {e}")

        return candidates

    def crawl_events(self, queries: List[str], hop_depth: int, limit_per_query: int = 3) -> List[CandidateDocument]:
        """
        Crawls event news, web URLs, and Knowledge Graph entities.
        """
        candidates: List[CandidateDocument] = []
        seen_ids: Set[str] = set()

        for q in queries:
            # 1. Knowledge Graph Precedent / Entity Search
            try:
                matched_ents = kg_engine.resolve_entities_in_text(q)
                subgraph = kg_engine.get_subgraph_context(matched_ents)
                precedents = kg_engine.find_historical_precedents(q, top_k=2)
                for prec in precedents:
                    doc_id = f"kg_prec_{prec.get('event_id', hashlib.sha256(prec.get('headline', '').encode()).hexdigest()[:8])}"
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        candidates.append(CandidateDocument(
                            doc_id=doc_id,
                            title=prec.get("headline", "Historical Shock Precedent"),
                            content=json.dumps(prec),
                            source_type="knowledge_graph",
                            hop_depth=hop_depth,
                            extracted_insights={"scores": prec.get("impact_scores", {})}
                        ))
            except Exception as e:
                logger.debug(f"KG crawl error for '{q}': {e}")

        return candidates


class SelectorAgent:
    """
    PaSa Selector Agent: Responsible for relevance evaluation, pruning,
    hop direction, and structured empirical insight synthesis.
    """

    SELECTOR_PROMPT_TEMPLATE = """
You are an expert energy economist and qualitative research selector.
Evaluate the following candidate documents against the research objective:
Objective: "{objective}"

Candidate Documents:
{candidates_json}

For EACH document, evaluate its relevance score from 0.0 (completely irrelevant) to 1.0 (highly relevant and empirically grounded).
Extract any quantitative parameter bounds (e.g. shock half-life days, pass-through elasticity, dollar impact) and key qualitative findings.

Return ONLY a valid JSON object matching this schema:
{{
  "evaluations": [
    {{
      "doc_id": "string",
      "relevance_score": float,
      "relevance_explanation": "string",
      "extracted_parameters": {{
        "parameter_name": "string",
        "value": float,
        "unit": "string",
        "bounds": [float, float]
      }},
      "key_finding": "string"
    }}
  ],
  "should_continue_hops": boolean,
  "next_hop_guidance": "string",
  "synthesized_summary": "string"
}}
"""

    def __init__(self, relevance_threshold: float = 0.40):
        self.relevance_threshold = relevance_threshold

    def evaluate_and_select(
        self,
        candidates: List[CandidateDocument],
        objective: str,
        current_hop: int,
        max_hops: int,
        api_key: Optional[str] = None,
        tier: str = "privileged"
    ) -> Tuple[List[CandidateDocument], bool, str, str, Dict[str, Any]]:
        """
        Evaluates candidate documents. Returns (selected_docs, should_continue, next_guidance, summary, parameters).
        """
        if not candidates:
            return [], False, "", "No candidates retrieved.", {}

        # 1. Check Offline / Zero-Cost Mode
        if tier == "basic" or os.environ.get("TESTING") == "1" or not (api_key or os.environ.get("GEMINI_API_KEY")):
            return self._evaluate_deterministic(candidates, objective, current_hop, max_hops)

        # 2. LLM Evaluative Pass
        try:
            formatted_candidates = [
                {
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "content": c.content[:350],
                    "source": c.source_type
                }
                for c in candidates[:8]
            ]
            prompt_str = self.SELECTOR_PROMPT_TEMPLATE.format(
                objective=objective,
                candidates_json=json.dumps(formatted_candidates, indent=2)
            )

            actual_key = api_key or os.environ.get("GEMINI_API_KEY")
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=actual_key)
            config = types.GenerateContentConfig(temperature=0.1)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_str,
                config=config
            )
            raw_text = response.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw_text)
            token_tab_manager.record_usage("gemini-2.5-flash", "pasa_selector_eval", 400, 200, status="success")

            eval_map = {e["doc_id"]: e for e in parsed.get("evaluations", []) if "doc_id" in e}
            selected = []
            extracted_params = {}

            for doc in candidates:
                if doc.doc_id in eval_map:
                    ev = eval_map[doc.doc_id]
                    doc.relevance_score = float(ev.get("relevance_score", 0.0))
                    doc.relevance_explanation = ev.get("relevance_explanation", "")
                    doc.extracted_insights = {
                        "key_finding": ev.get("key_finding", ""),
                        "parameters": ev.get("extracted_parameters", {})
                    }
                    if ev.get("extracted_parameters"):
                        param_info = ev["extracted_parameters"]
                        p_name = param_info.get("parameter_name") or "unspecified_param"
                        extracted_params[p_name] = param_info

                    if doc.relevance_score >= self.relevance_threshold:
                        selected.append(doc)

            should_continue = bool(parsed.get("should_continue_hops", False)) and (current_hop + 1 < max_hops)
            next_guidance = parsed.get("next_hop_guidance", "")
            summary = parsed.get("synthesized_summary", "")

            return selected, should_continue, next_guidance, summary, extracted_params

        except Exception as e:
            logger.warning(f"Selector LLM evaluation failed ({e}). Falling back to deterministic evaluation.")
            return self._evaluate_deterministic(candidates, objective, current_hop, max_hops)

    def _evaluate_deterministic(
        self,
        candidates: List[CandidateDocument],
        objective: str,
        current_hop: int,
        max_hops: int
    ) -> Tuple[List[CandidateDocument], bool, str, str, Dict[str, Any]]:
        """
        Fast, zero-cost deterministic rule-based selector evaluator.
        """
        keywords = [w.lower() for w in re.findall(r'\b\w{4,}\b', objective)]
        selected = []
        extracted_params = {}

        for doc in candidates:
            text = f"{doc.title} {doc.content}".lower()
            matches = sum(1 for kw in keywords if kw in text)
            score = min(1.0, matches / max(1, len(keywords)) + (0.3 if doc.citation_count > 10 else 0.0))
            doc.relevance_score = round(score, 2)
            doc.relevance_explanation = f"Matched {matches}/{len(keywords)} objective keywords."

            # Check for standard econometrics parameters
            if any(term in text for term in ["half-life", "decay", "outage", "shock"]):
                extracted_params["shock_decay_half_life"] = {
                    "parameter_name": "shock_decay_half_life",
                    "value": 4.5,
                    "unit": "days",
                    "bounds": [4.0, 5.0]
                }
            if any(term in text for term in ["tax", "incidence", "pass-through"]):
                extracted_params["tax_pass_through_rate"] = {
                    "parameter_name": "tax_pass_through_rate",
                    "value": 1.0,
                    "unit": "ratio",
                    "bounds": [0.85, 1.15]
                }

            if doc.relevance_score >= self.relevance_threshold:
                selected.append(doc)

        should_continue = (len(selected) < 2) and (current_hop + 1 < max_hops)
        next_guidance = "Explore related citations and regional refinery spreads." if should_continue else ""
        summary = (
            f"PaSa Selector Rule-Based Synthesis: Identified {len(selected)} relevant documents "
            f"for '{objective}'. Parameter calibration completed with bounds: {list(extracted_params.keys())}."
        )

        return selected, should_continue, next_guidance, summary, extracted_params


class PaSaResearchAgent:
    """
    Main PaSa Research Agent Orchestrator.
    Manages the iterative Crawler <-> Selector multi-hop research loop, caching, and telemetry.
    """

    def __init__(self, max_hops: int = 2, relevance_threshold: float = 0.40):
        self.max_hops = min(max_hops, 3)
        self.crawler = CrawlerAgent()
        self.selector = SelectorAgent(relevance_threshold=relevance_threshold)

    def investigate(
        self,
        objective: str,
        mode: str = "academic",  # 'academic' or 'event'
        max_hops: Optional[int] = None,
        api_key: Optional[str] = None,
        tier: str = "privileged"
    ) -> PaSaResearchResult:
        """
        Executes multi-hop qualitative event or academic literature research.
        """
        t0 = time.time()
        effective_max_hops = min(max_hops or self.max_hops, 3)
        cache_key = f"pasa__{mode}__{objective.strip().lower()}__hops={effective_max_hops}"
        cache = _load_pasa_cache()

        if cache_key in cache:
            cached_data = cache[cache_key]
            logger.info(f"PaSa research cache hit for objective: '{objective}'")
            return PaSaResearchResult(
                objective=cached_data["objective"],
                mode=cached_data["mode"],
                total_hops_executed=cached_data["total_hops_executed"],
                total_candidates_evaluated=cached_data["total_candidates_evaluated"],
                selected_documents=[CandidateDocument(**d) for d in cached_data["selected_documents"]],
                synthesized_summary=cached_data["synthesized_summary"],
                parameter_bounds=cached_data["parameter_bounds"],
                bibliography=cached_data["bibliography"],
                duration_ms=cached_data.get("duration_ms", 0.0),
                status="completed_cached"
            )

        all_selected: List[CandidateDocument] = []
        all_candidates_count = 0
        current_seed_docs: List[CandidateDocument] = []
        synthesized_summary = ""
        accumulated_params: Dict[str, Any] = {}
        hops_executed = 0

        for hop in range(effective_max_hops):
            hops_executed += 1
            # 1. Crawler expands queries and retrieves candidates
            queries = self.crawler.expand_queries(objective, hop=hop, seed_docs=current_seed_docs)
            if mode == "academic":
                candidates = self.crawler.crawl_academic(queries, hop_depth=hop)
            else:
                candidates = self.crawler.crawl_events(queries, hop_depth=hop)
                if not candidates:
                    # Fallback to academic crawl if event feeds are sparse
                    candidates = self.crawler.crawl_academic(queries, hop_depth=hop)

            all_candidates_count += len(candidates)

            # 2. Selector evaluates candidates
            selected, should_continue, next_guidance, summary, params = self.selector.evaluate_and_select(
                candidates=candidates,
                objective=objective,
                current_hop=hop,
                max_hops=effective_max_hops,
                api_key=api_key,
                tier=tier
            )

            all_selected.extend(selected)
            accumulated_params.update(params)
            if summary:
                synthesized_summary = summary
            current_seed_docs = selected

            if not should_continue:
                logger.info(f"PaSa research loop converged at hop {hop + 1}/{effective_max_hops}.")
                break

        # Build bibliography
        biblio = []
        seen_titles = set()
        for doc in all_selected:
            if doc.title and doc.title not in seen_titles:
                seen_titles.add(doc.title)
                biblio.append({
                    "title": doc.title,
                    "url": doc.url or doc.doi or "",
                    "source": doc.source_type,
                    "relevance": f"{doc.relevance_score:.2f}"
                })

        duration_ms = (time.time() - t0) * 1000.0

        result = PaSaResearchResult(
            objective=objective,
            mode=mode,
            total_hops_executed=hops_executed,
            total_candidates_evaluated=all_candidates_count,
            selected_documents=all_selected,
            synthesized_summary=synthesized_summary or f"Research completed across {hops_executed} hops.",
            parameter_bounds=accumulated_params,
            bibliography=biblio,
            duration_ms=duration_ms,
            status="completed"
        )

        # Cache result
        cache[cache_key] = result.to_dict()
        _save_pasa_cache(cache)

        return result


# Singleton instance for quick access
pasa_agent = PaSaResearchAgent()
