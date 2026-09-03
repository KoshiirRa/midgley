"""
Model Context Protocol (MCP) Server (src/mcp_server.py)
Exposes Midgley unleaded gas price forecasting tools, resources, and prompt templates
for external LLMs, AI agents (Claude Desktop, Antigravity, ChatGPT), and chatbots.
"""

import os
import json
import asyncio
import logging
from typing import Any, Sequence

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from src.api_server import (
    _get_live_prices_impl,
    _get_forecast_impl,
    _get_combined_impl,
    SCENARIOS_CATALOG,
    SimulateRequest,
    simulate_shock
)

logger = logging.getLogger(__name__)

# Initialize MCP Server instance
app = Server("midgley-gas-prices")


async def list_tools() -> list[types.Tool]:
    """Exposes MCP tools available for agent function calling."""
    return [
        types.Tool(
            name="get_live_gas_prices",
            description="Fetches real-time unleaded gasoline pump prices by locale (national, tulsa, newark, cincinnati, oakland) or US zip code from GasBuddy GraphQL / AAA scraper feeds.",
            inputSchema={
                "type": "object",
                "properties": {
                    "locale": {
                        "type": "string",
                        "description": "Locale identifier (national, tulsa, newark, cincinnati, oakland, bayarea)",
                        "default": "national"
                    },
                    "zip_code": {
                        "type": "string",
                        "description": "Optional 5-digit US zip code for station-level GasBuddy search"
                    }
                }
            }
        ),
        types.Tool(
            name="get_gas_price_prediction",
            description="Returns Midgley 5-day out-of-time quantitative gasoline price forecast, expected dollar delta, projected direction (UP/DOWN/FLAT), and historical hit rate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "locale": {
                        "type": "string",
                        "description": "Target locale code (national, tulsa, newark, cincinnati, oakland)",
                        "default": "national"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Forecast horizon in days (default 5)",
                        "default": 5
                    }
                }
            }
        ),
        types.Tool(
            name="get_live_and_forecast",
            description="Unified tool returning current live pump price, predicted 5-day target forecast, regional rack margin, and top news/weather drivers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "locale": {
                        "type": "string",
                        "description": "Target locale code (national, tulsa, newark, cincinnati, oakland)",
                        "default": "national"
                    }
                }
            }
        ),
        types.Tool(
            name="simulate_fuel_market_shock",
            description="Simulates counterfactual physical refinery outages, weather disasters, or geopolitical chokepoints (e.g. hormuz_blockade, suez_rerouting, tulsa_tornado, hayward_quake, pge_psps_shutoff).",
            inputSchema={
                "type": "object",
                "properties": {
                    "locale": {
                        "type": "string",
                        "description": "Target locale code (national, tulsa, newark, cincinnati, oakland)",
                        "default": "national"
                    },
                    "scenario_id": {
                        "type": "string",
                        "description": "Scenario ID to simulate",
                        "default": "hormuz_blockade",
                        "enum": list(SCENARIOS_CATALOG.keys())
                    },
                    "custom_shock_pct": {
                        "type": "number",
                        "description": "Optional custom shock percentage override (e.g. 0.05 for +5%)"
                    }
                },
                "required": ["scenario_id"]
            }
        ),
        types.Tool(
            name="get_live_diesel_prices",
            description="Fetches live Ultra-Low Sulfur Diesel (ULSD HO=F) futures, distillate crack spreads, 3-2-1 refining margins, and retail diesel prices across metro areas.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_diesel_forecast",
            description="Generates 5-day out-of-time ULSD wholesale commodity forecasts ($/gal) and regional retail calibrations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "rbob": {"type": "number", "default": 2.450, "description": "Base RBOB futures price"},
                    "ulsd": {"type": "number", "default": 2.850, "description": "Base ULSD futures price"},
                    "wti": {"type": "number", "default": 75.00, "description": "Base WTI crude price"}
                }
            }
        ),
        types.Tool(
            name="simulate_diesel_market_shock",
            description="Simulates counterfactual physical, weather, and geopolitical diesel shock scenarios (Colonial Line 2 outage, Northeast polar vortex, Midwest harvest surge).",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "default": "colonial_line2_outage",
                        "description": "Scenario key: colonial_line2_outage, northeast_polar_vortex, midwest_harvest_surge, imo_2020_marine_fuel_spike, winter_grid_emergency_backup"
                    },
                    "base_ulsd": {"type": "number", "default": 2.850, "description": "Base ULSD futures price"}
                }
            }
        )
    ]


async def call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Executes requested tool and returns JSON formatted text response."""
    args = arguments or {}

    try:
        if name == "get_live_gas_prices":
            locale = args.get("locale", "national")
            zip_code = args.get("zip_code")
            res = _get_live_prices_impl(locale=locale, zip_code=zip_code)
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

        elif name == "get_gas_price_prediction":
            locale = args.get("locale", "national")
            days = int(args.get("days", 5))
            res = _get_forecast_impl(locale=locale, days=days)
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

        elif name == "get_live_and_forecast":
            locale = args.get("locale", "national")
            res = _get_combined_impl(locale=locale)
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

        elif name == "simulate_fuel_market_shock":
            locale = args.get("locale", "national")
            scenario_id = args.get("scenario_id", "hormuz_blockade")
            custom_shock_pct = args.get("custom_shock_pct")
            req = SimulateRequest(scenario_id=scenario_id, locale=locale, custom_shock_pct=custom_shock_pct)
            res = simulate_shock(req)
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

        elif name == "get_live_diesel_prices":
            from src.api_server import get_diesel_live_prices
            res = get_diesel_live_prices()
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

        elif name == "get_diesel_forecast":
            from src.api_server import get_diesel_forecast
            rbob = float(args.get("rbob", 2.450))
            ulsd = float(args.get("ulsd", 2.850))
            wti = float(args.get("wti", 75.00))
            res = get_diesel_forecast(rbob=rbob, ulsd=ulsd, wti=wti)
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

        elif name == "simulate_diesel_market_shock":
            from src.api_server import simulate_diesel_shock_endpoint
            scenario = args.get("scenario", "colonial_line2_outage")
            base_ulsd = float(args.get("base_ulsd", 2.850))
            res = simulate_diesel_shock_endpoint(scenario=scenario, base_ulsd=base_ulsd)
            return [types.TextContent(type="text", text=json.dumps(res, indent=2))]

        else:
            raise ValueError(f"Unknown tool name: {name}")

    except Exception as e:
        logger.error(f"Error executing MCP tool '{name}': {e}")
        err_res = {"status": "error", "tool": name, "message": str(e)}
        return [types.TextContent(type="text", text=json.dumps(err_res, indent=2))]


async def list_resources() -> list[types.Resource]:
    """Exposes static context resources for Midgley supported locales."""
    locales = ["national", "tulsa", "newark", "cincinnati", "greenville", "charlotte", "oakland", "bayarea"]
    resources = []
    for loc in locales:
        resources.append(
            types.Resource(
                uri=f"resource://midgley/locales/{loc}",
                name=f"Midgley Market & Forecast Snapshot ({loc.upper()})",
                description=f"Complete baseline snapshot, 5-day forecast, error metrics, and key drivers for {loc}.",
                mimeType="application/json"
            )
        )
    return resources


async def read_resource(uri: str) -> str:
    """Reads snapshot data for requested resource URI."""
    if uri.startswith("resource://midgley/locales/"):
        locale = uri.replace("resource://midgley/locales/", "")
        res = _get_combined_impl(locale=locale)
        return json.dumps(res, indent=2)
    raise ValueError(f"Resource not found: {uri}")


async def list_prompts() -> list[types.Prompt]:
    """Exposes prompt templates for financial executive summaries."""
    return [
        types.Prompt(
            name="market_summary",
            description="System prompt helper instructing an LLM to generate an unleaded gas price intelligence summary.",
            arguments=[
                types.PromptArgument(
                    name="locale",
                    description="Target locale for intelligence summary (national, tulsa, newark, cincinnati, oakland)",
                    required=False
                )
            ]
        )
    ]


async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Generates structured prompt template."""
    if name == "market_summary":
        args = arguments or {}
        locale = args.get("locale", "national")
        snapshot = _get_combined_impl(locale=locale)

        prompt_text = (
            f"You are Antigravity Energy & Commodity Analyst. Analyze the following real-time gas price "
            f"and 5-day forecast snapshot for '{locale.upper()}':\n\n"
            f"```json\n{json.dumps(snapshot, indent=2)}\n```\n\n"
            f"Provide a concise, professional executive briefing covering:\n"
            f"1. Current Retail / Wholesale Pump Price & Source Data\n"
            f"2. 5-Day Projected Forecast Target & Expected Directional Hit Confidence\n"
            f"3. Key Geopolitical, Weather, Refining, and Regulatory Drivers\n"
            f"4. Operational Risk Advice for Fleet & Fuel Buyers."
        )

        return types.GetPromptResult(
            description=f"Midgley Gas Price Intelligence Brief for {locale.upper()}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt_text)
                )
            ]
        )
    raise ValueError(f"Prompt not found: {name}")


# Register request handlers on low-level Server instance
async def _handle_list_tools(req: types.PaginatedRequestParams) -> types.ListToolsResult:
    tools = await list_tools()
    return types.ListToolsResult(tools=tools)

async def _handle_call_tool(req: types.CallToolRequestParams) -> types.CallToolResult:
    res = await call_tool(req.name, req.arguments)
    return types.CallToolResult(content=res)

async def _handle_list_resources(req: types.PaginatedRequestParams) -> types.ListResourcesResult:
    resources = await list_resources()
    return types.ListResourcesResult(resources=resources)

async def _handle_read_resource(req: types.ReadResourceRequestParams) -> types.ReadResourceResult:
    content = await read_resource(req.uri)
    return types.ReadResourceResult(
        contents=[
            types.TextResourceContents(
                uri=req.uri,
                mimeType="application/json",
                text=content
            )
        ]
    )

async def _handle_list_prompts(req: types.PaginatedRequestParams) -> types.ListPromptsResult:
    prompts = await list_prompts()
    return types.ListPromptsResult(prompts=prompts)

async def _handle_get_prompt(req: types.GetPromptRequestParams) -> types.GetPromptResult:
    return await get_prompt(req.name, req.arguments)


app.add_request_handler("tools/list", types.PaginatedRequestParams, _handle_list_tools)
app.add_request_handler("tools/call", types.CallToolRequestParams, _handle_call_tool)
app.add_request_handler("resources/list", types.PaginatedRequestParams, _handle_list_resources)
app.add_request_handler("resources/read", types.ReadResourceRequestParams, _handle_read_resource)
app.add_request_handler("prompts/list", types.PaginatedRequestParams, _handle_list_prompts)
app.add_request_handler("prompts/get", types.GetPromptRequestParams, _handle_get_prompt)


async def main():
    """Runs stdio server loop when executed directly."""
    logger.info("Starting Midgley MCP Server in stdio mode...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
