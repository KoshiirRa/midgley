"""
Unit tests for Model Context Protocol (MCP) Server (src/mcp_server.py)
Verifies listing tools, calling tools, reading resources, and resolving prompt templates.
"""

import json
import asyncio
import unittest

from src.mcp_server import (
    list_tools,
    call_tool,
    list_resources,
    read_resource,
    list_prompts,
    get_prompt
)


class TestMCPServer(unittest.TestCase):

    def test_list_tools(self):
        tools = asyncio.run(list_tools())
        self.assertGreater(len(tools), 0)
        tool_names = [t.name for t in tools]
        self.assertIn("get_live_gas_prices", tool_names)
        self.assertIn("get_gas_price_prediction", tool_names)
        self.assertIn("get_live_and_forecast", tool_names)
        self.assertIn("simulate_fuel_market_shock", tool_names)

    def test_call_tool_get_live_gas_prices(self):
        res = asyncio.run(call_tool("get_live_gas_prices", {"locale": "oakland"}))
        self.assertEqual(len(res), 1)
        data = json.loads(res[0].text)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["locale"]["code"], "oakland")

    def test_call_tool_get_gas_price_prediction(self):
        res = asyncio.run(call_tool("get_gas_price_prediction", {"locale": "tulsa", "days": 5}))
        self.assertEqual(len(res), 1)
        data = json.loads(res[0].text)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["forecast"]["forecast_horizon_days"], 5)

    def test_call_tool_get_live_and_forecast(self):
        res = asyncio.run(call_tool("get_live_and_forecast", {"locale": "cincinnati"}))
        self.assertEqual(len(res), 1)
        data = json.loads(res[0].text)
        self.assertEqual(data["status"], "success")
        self.assertIn("live_lookup", data)
        self.assertIn("forecast", data)

    def test_call_tool_simulate_shock(self):
        res = asyncio.run(call_tool("simulate_fuel_market_shock", {"locale": "oakland", "scenario_id": "hayward_quake"}))
        self.assertEqual(len(res), 1)
        data = json.loads(res[0].text)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scenario"]["id"], "hayward_quake")

    def test_list_and_read_resources(self):
        resources = asyncio.run(list_resources())
        self.assertGreater(len(resources), 0)
        uri = resources[0].uri
        self.assertTrue(uri.startswith("resource://midgley/locales/"))
        
        content = asyncio.run(read_resource(uri))
        data = json.loads(content)
        self.assertEqual(data["status"], "success")

    def test_list_and_get_prompts(self):
        prompts = asyncio.run(list_prompts())
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0].name, "market_summary")

        prompt_res = asyncio.run(get_prompt("market_summary", {"locale": "tulsa"}))
        self.assertIsNotNone(prompt_res)
        self.assertEqual(len(prompt_res.messages), 1)
        self.assertIn("TULSA", prompt_res.messages[0].content.text)


if __name__ == "__main__":
    unittest.main()
