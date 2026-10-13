"""
Register Discord Application Slash Commands (scripts/register_discord_commands.py)

Registers or updates the `/midgley` application slash command suite (`subscribe`,
`unsubscribe`, `status`, `forecast`, `test-alert`) with Discord's HTTP Interactions API (Issue #235).
Supports both Global and Guild-scoped command registration, plus Guild-Install and User-Install
contexts so users can receive private Direct Message alerts without spamming shared server chat.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional


LOCALE_CHOICES = [
    {"name": "National (US Wholesale & Retail Benchmark)", "value": "National"},
    {"name": "Tulsa Metro, OK (PADD 2)", "value": "Tulsa"},
    {"name": "Newark Metro, DE (PADD 1B)", "value": "Newark"},
    {"name": "Cincinnati Tri-State, OH/KY (PADD 2)", "value": "Cincinnati"},
    {"name": "Greenville Metro, NC (PADD 1C)", "value": "Greenville"},
    {"name": "Charlotte Metro, NC (PADD 1C)", "value": "Charlotte"},
    {"name": "SF Bay Area / Oakland, CA (PADD 5)", "value": "Oakland"},
    {"name": "Port St. Lucie Metro, FL (PADD 1C)", "value": "Port_St_Lucie"},
    {"name": "Greater Chicago Metro, IL/IN (PADD 2)", "value": "Chicago"},
    {"name": "Houston Metro, TX (PADD 3)", "value": "Houston"},
    {"name": "Los Angeles Basin, CA (PADD 5)", "value": "Los_Angeles"},
]


def build_midgley_command_manifest() -> List[Dict[str, Any]]:
    """
    Constructs the Discord Application Command JSON manifest for `/midgley`.
    Includes `integration_types: [0, 1]` (GUILD_INSTALL, USER_INSTALL) and
    `contexts: [0, 1, 2]` (GUILD, BOT_DM, PRIVATE_CHANNEL).
    """
    return [
        {
            "name": "midgley",
            "type": 1,  # CHAT_INPUT
            "description": "Midgley gasoline forecast & private Direct Message shock alert commands",
            "integration_types": [0, 1],
            "contexts": [0, 1, 2],
            "options": [
                {
                    "name": "subscribe",
                    "description": "Subscribe to real-time intraday gasoline shock alerts via private Direct Message",
                    "type": 1,  # SUB_COMMAND
                    "options": [
                        {
                            "name": "locale",
                            "description": "Target regional metro hub or National wholesale benchmark",
                            "type": 3,  # STRING
                            "required": True,
                            "autocomplete": True,
                        },
                        {
                            "name": "min_shock",
                            "description": "Minimum price shock magnitude |ΔP| in $/gal to trigger an alert (default: 0.25)",
                            "type": 10,  # NUMBER (float)
                            "required": False,
                            "min_value": 0.05,
                            "max_value": 2.50,
                        },
                        {
                            "name": "direction",
                            "description": "Directional bias filter for price shocks",
                            "type": 3,  # STRING
                            "required": False,
                            "choices": [
                                {"name": "All Shocks (Spikes & Drops)", "value": "all_shocks"},
                                {"name": "Price Spikes Only (ΔP > 0)", "value": "spikes_only"},
                                {"name": "Price Drops Only (ΔP < 0)", "value": "drops_only"},
                            ],
                        },
                        {
                            "name": "delivery",
                            "description": "Preferred feedback delivery mode",
                            "type": 3,  # STRING
                            "required": False,
                            "choices": [
                                {"name": "Private Direct Message (DM)", "value": "dm"},
                                {"name": "Ephemeral In-Channel Only", "value": "channel_ephemeral"},
                            ],
                        },
                    ],
                },
                {
                    "name": "unsubscribe",
                    "description": "Unsubscribe from Midgley Direct Message gasoline shock alerts",
                    "type": 1,  # SUB_COMMAND
                    "options": [
                        {
                            "name": "locale",
                            "description": "Specific metro hub to remove, or 'all' to clear all subscriptions",
                            "type": 3,  # STRING
                            "required": False,
                            "autocomplete": True,
                        }
                    ],
                },
                {
                    "name": "status",
                    "description": "View your active Direct Message alert subscriptions and thresholds",
                    "type": 1,  # SUB_COMMAND
                },
                {
                    "name": "forecast",
                    "description": "Get the latest point-in-time gasoline price forecast & regime brief via DM",
                    "type": 1,  # SUB_COMMAND
                    "options": [
                        {
                            "name": "locale",
                            "description": "Target regional metro hub or National",
                            "type": 3,  # STRING
                            "required": True,
                            "autocomplete": True,
                        },
                        {
                            "name": "horizon",
                            "description": "Forecast horizon in days (1D to 5D, default: 5)",
                            "type": 4,  # INTEGER
                            "required": False,
                            "choices": [
                                {"name": "1-Day Ahead (1D)", "value": 1},
                                {"name": "2-Day Ahead (2D)", "value": 2},
                                {"name": "3-Day Ahead (3D)", "value": 3},
                                {"name": "4-Day Ahead (4D)", "value": 4},
                                {"name": "5-Day Full Trajectory (5D)", "value": 5},
                            ],
                        },
                    ],
                },
                {
                    "name": "test-alert",
                    "description": "Send a dry-run synthetic shock alert to your DMs to verify reachability",
                    "type": 1,  # SUB_COMMAND
                    "options": [
                        {
                            "name": "locale",
                            "description": "Sample metro hub for the synthetic alert card",
                            "type": 3,  # STRING
                            "required": False,
                            "autocomplete": True,
                        }
                    ],
                },
            ],
        }
    ]


def register_discord_commands(
    app_id: Optional[str] = None,
    bot_token: Optional[str] = None,
    guild_id: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Registers the `/midgley` command manifest with the Discord API v10.
    Suppresses network calls automatically when `TESTING=1` or `dry_run=True`.
    """
    commands = build_midgley_command_manifest()
    resolved_app_id = (app_id or os.environ.get("DISCORD_APP_ID") or "").strip()
    resolved_token = (bot_token or os.environ.get("DISCORD_BOT_TOKEN") or "").strip()

    if dry_run or os.environ.get("TESTING") == "1":
        return {
            "status": "dry_run",
            "app_id": resolved_app_id or "dry_run_app_id",
            "guild_id": guild_id,
            "commands_count": len(commands),
            "commands": commands,
        }

    if not resolved_app_id or not resolved_token:
        raise ValueError("Both DISCORD_APP_ID and DISCORD_BOT_TOKEN are required to register live Discord commands.")

    if guild_id:
        endpoint = f"https://discord.com/api/v10/applications/{resolved_app_id}/guilds/{guild_id.strip()}/commands"
    else:
        endpoint = f"https://discord.com/api/v10/applications/{resolved_app_id}/commands"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(commands).encode("utf-8"),
        headers={
            "Authorization": f"Bot {resolved_token}",
            "Content-Type": "application/json",
            "User-Agent": "Midgley-Discord-Command-Registrar/1.0",
        },
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp_data = json.loads(resp.read().decode("utf-8"))
        return {
            "status": "registered",
            "http_status": resp.status,
            "endpoint": endpoint,
            "registered_commands": resp_data,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Register /midgley Discord Application Slash Commands")
    parser.add_argument("--app-id", help="Discord Application ID (or set DISCORD_APP_ID)")
    parser.add_argument("--guild-id", help="Optional Discord Guild ID for instant server-scoped registration")
    parser.add_argument("--dry-run", action="store_true", help="Print command manifest JSON without calling Discord API")
    args = parser.parse_args()

    try:
        res = register_discord_commands(app_id=args.app_id, guild_id=args.guild_id, dry_run=args.dry_run)
        print(json.dumps(res, indent=2))
        return 0
    except Exception as exc:
        print(f"Error registering Discord commands: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
