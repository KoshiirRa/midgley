#!/usr/bin/env python3
"""
Key Management CLI Utility (scripts/manage_keys.py) - Method A
Admin tool for creating, listing, inspecting, revoking, and verifying
API keys for Midgley REST API Gateway & MCP Server.

Usage:
  python scripts/manage_keys.py create --user "alice" --tier privileged --env prod --rpm 30
  python scripts/manage_keys.py list --env prod
  python scripts/manage_keys.py revoke --prefix mg_prod_a1b2c3d4
  python scripts/manage_keys.py verify --token mg_dev_12345678_...
"""

import sys
import os
import argparse

# Force UTF-8 encoding for stdout on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.key_manager import KeyManager, DEFAULT_DB_PATH, DEFAULT_RPM


def main():
    parser = argparse.ArgumentParser(
        description="Midgley API Key Management Utility (Method A CLI)"
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database file (default: {DEFAULT_DB_PATH})"
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-command")

    # Command: create
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("--user", required=True, help="User or client identifier")
    create_parser.add_argument(
        "--tier",
        choices=["privileged", "basic"],
        default="basic",
        help="Access tier: 'privileged' (full multi-agent LLM) or 'basic' (zero-cost fallbacks). Default: basic"
    )
    create_parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default="dev",
        help="Target environment prefix ('dev' or 'prod'). Default: dev"
    )
    create_parser.add_argument(
        "--rpm",
        type=int,
        default=DEFAULT_RPM,
        help=f"Rate limit in requests per minute (default: {DEFAULT_RPM})"
    )
    create_parser.add_argument(
        "--expires-days",
        type=int,
        default=None,
        help="Optional key lifespan in days (default: None / never)"
    )

    # Command: list
    list_parser = subparsers.add_parser("list", help="List active and revoked API keys")
    list_parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default=None,
        help="Filter keys by environment ('dev' or 'prod')"
    )

    # Command: revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key by prefix")
    revoke_parser.add_argument("--prefix", required=True, help="Key prefix to revoke (e.g., mg_dev_a1b2c3d4)")

    # Command: verify
    verify_parser = subparsers.add_parser("verify", help="Verify a raw API token string")
    verify_parser.add_argument("--token", required=True, help="Full raw API key token string to verify")

    args = parser.parse_args()
    km = KeyManager(db_path=args.db_path)

    if args.command == "create":
        res = km.create_key(
            user_id=args.user,
            tier=args.tier,
            rate_limit_rpm=args.rpm,
            environment=args.env,
            expires_days=args.expires_days
        )
        print("\n=======================================================")
        print("  [KEY] MIDGLEY API KEY PROVISIONED SUCCESSFULLY")
        print("=======================================================")
        print(f"  User ID        : {res['user_id']}")
        print(f"  Tier           : {res['tier'].upper()}")
        print(f"  Environment    : {res['environment'].upper()}")
        print(f"  Rate Limit     : {res['rate_limit_rpm']} RPM")
        print(f"  Key Prefix     : {res['key_prefix']}")
        print(f"  Created At     : {res['created_at']}")
        print(f"  Expires At     : {res['expires_at'] or 'Never'}")
        print("-------------------------------------------------------")
        print(f"  PLAINTEXT TOKEN: {res['token']}")
        print("  [!] SAVE THIS TOKEN NOW! It will not be shown again.")
        print("=======================================================\n")

    elif args.command == "list":
        keys = km.list_keys(environment=args.env)
        print("\n=======================================================")
        print(f"  [LIST] REGISTERED MIDGLEY API KEYS ({len(keys)} Total)")
        print("=======================================================")
        if not keys:
            print("  No API keys registered.")
        else:
            for k in keys:
                status = "ACTIVE" if k["active"] else "REVOKED"
                print(f"  Prefix: {k['key_prefix']} | User: {k['user_id']} | Tier: {k['tier'].upper()} | Env: {k['environment'].upper()} | Status: {status}")
                print(f"          Rate Limit: {k['rate_limit_rpm']} RPM | Created: {k['created_at']}")
                print("  -----------------------------------------------------")
        print()

    elif args.command == "revoke":
        success = km.revoke_key(args.prefix)
        if success:
            print(f"\n[OK] API key with prefix [{args.prefix}] revoked successfully.\n")
        else:
            print(f"\n[ERROR] Failed to revoke API key prefix [{args.prefix}]. Prefix not found.\n")

    elif args.command == "verify":
        is_valid, key_info, err = km.verify_key(args.token)
        if is_valid:
            print("\n=======================================================")
            print("  [OK] API TOKEN VERIFIED & VALID")
            print("=======================================================")
            print(f"  User ID    : {key_info['user_id']}")
            print(f"  Tier       : {key_info['tier'].upper()}")
            print(f"  Environment: {key_info['environment'].upper()}")
            print(f"  Rate Limit : {key_info['rate_limit_rpm']} RPM")
            print("=======================================================\n")
        else:
            print(f"\n[ERROR] INVALID TOKEN: {err}\n")


if __name__ == "__main__":
    main()
