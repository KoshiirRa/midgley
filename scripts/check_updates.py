#!/usr/bin/env python3
"""
Upstream Compatibility & Upgrade Reconciler CLI (scripts/check_updates.py)
Inspects upstream release manifests, detects breaking schema/model feature drifts,
and performs automated self-hosted reconciliation (Issue #299).
"""

import os
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.version import get_version, get_model_engine_version
from src.release_manifest import generate_release_manifest, MANIFEST_SCHEMA_VERSION

ALLOWLISTED_ACTIONS: Dict[str, List[str]] = {
    "retrain_regional_models": [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "manage_regions.py"), "retrain", "--all"],
    "check_regions": [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "manage_regions.py"), "check"],
    "sync_features": [sys.executable, os.path.join(PROJECT_ROOT, "main.py"), "--features"],
}


def fetch_upstream_manifest(endpoint_url: Optional[str] = None) -> Dict[str, Any]:
    """Fetches manifest from remote endpoint or compiles local definition."""
    if endpoint_url:
        try:
            parsed = urllib.parse.urlparse(endpoint_url)
            if parsed.scheme not in ("https", "http") or (parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1")):
                print(f"[!] Refusing insecure or non-HTTP(S) manifest URL: {endpoint_url}. Falling back to local manifest.")
                return generate_release_manifest()

            req = urllib.request.Request(endpoint_url, headers={"User-Agent": "Midgley-Reconciler/1.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[!] Remote manifest fetch failed ({e}); evaluating local release manifest definition.")

    # Fallback to local release manifest generator
    return generate_release_manifest()


def check_environment_variables(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Inspects local environment against manifest environment_changes."""
    env_changes = manifest.get("environment_changes", {})
    added = env_changes.get("added", [])
    missing = []
    configured = []

    for item in added:
        var_name = item["name"]
        val = os.environ.get(var_name)
        if val is None:
            missing.append(item)
        else:
            configured.append(var_name)

    return {
        "missing": missing,
        "configured": configured
    }


def reconcile_upgrades(manifest: Dict[str, Any], dry_run: bool = True) -> bool:
    """
    Evaluates drift between current local instance and upstream release manifest.
    Optionally executes auto-reconciliation actions.
    """
    current_ver = get_version()
    current_model = get_model_engine_version()

    upstream_ver = manifest.get("version", current_ver)
    upstream_model = manifest.get("model_version", current_model)
    compat = manifest.get("compatibility", {})
    env_audit = check_environment_variables(manifest)

    print("================================================================================")
    print("[*] Midgley Upstream Release & Schema Compatibility Reconciler (Issue #299)")
    print("================================================================================")
    print(f"* Local Package Version:       v{current_ver}")
    print(f"* Upstream Manifest Version:   v{upstream_ver}")
    print(f"* Local Model Engine:          {current_model}")
    print(f"* Upstream Model Engine:       {upstream_model}")
    print(f"* Breaking Changes Flag:       {compat.get('breaking_changes', False)}")
    print(f"* Retraining Required:         {compat.get('requires_regional_retraining', False)}")
    print("--------------------------------------------------------------------------------")

    # 1. Environment Variable Audit
    print("[+] Environment Variable Status:")
    if env_audit["missing"]:
        for item in env_audit["missing"]:
            req_str = "REQUIRED" if item.get("required") else f"Optional (Default: '{item.get('default', '')}')"
            print(f"  [-] Missing: {item['name']} [{req_str}] - {item.get('description', '')}")
    else:
        print("  [+] All required and recommended environment variables are present.")

    # 2. Database Migrations Audit
    migrations = manifest.get("database_migrations", [])
    print(f"\n[+] Database Migrations ({len(migrations)} registered):")
    for mig in migrations:
        print(f"  * [{mig['id']}] {mig['description']} (auto: {mig.get('automatic', True)})")

    # 3. Model Engine Feature Matrix
    model_engine = manifest.get("model_engine", {})
    features = model_engine.get("feature_matrix_columns", [])
    print(f"\n[+] Model Engine Feature Columns ({len(features)} active):")
    print(f"  {', '.join(features)}")

    # 4. Agent Action Items
    actions = manifest.get("agent_action_items", [])
    print("\n[+] AI Agent Action Items:")
    for idx, act in enumerate(actions, 1):
        print(f"  {idx}. {act}")

    print("================================================================================")

    if dry_run:
        print("[i] Dry-run complete. Run with `--auto-reconcile` to apply migrations & retraining.")
        return True

    print("\n[*] Executing automated reconciliation (--auto-reconcile)...")
    # Execute allowlisted action if specified and required
    retrain_action = model_engine.get("retrain_action")
    retrain_cmd = model_engine.get("retrain_command")

    if compat.get("requires_regional_retraining"):
        action_key = retrain_action
        if not action_key and retrain_cmd:
            if "manage_regions.py retrain --all" in retrain_cmd:
                action_key = "retrain_regional_models"
            elif "manage_regions.py check" in retrain_cmd:
                action_key = "check_regions"

        if action_key and action_key in ALLOWLISTED_ACTIONS:
            cmd_args = ALLOWLISTED_ACTIONS[action_key]
            print(f"Running allowlisted action '{action_key}': {' '.join(cmd_args)}")
            subprocess.run(cmd_args, shell=False, check=False)
        else:
            if retrain_cmd or retrain_action:
                print(f"[!] Skipping unallowlisted or unsafe retrain command: {retrain_cmd or retrain_action}")

    print("[+] Auto-reconciliation complete.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Midgley Upstream Upgrade & Compatibility Reconciler")
    parser.add_argument("--url", type=str, default=None, help="URL of upstream manifest endpoint (optional)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate reconciliation check without modifying state")
    parser.add_argument("--auto-reconcile", action="store_true", help="Automatically execute migrations and regional retraining")
    args = parser.parse_args()

    manifest = fetch_upstream_manifest(args.url)
    is_dry_run = not args.auto_reconcile

    reconcile_upgrades(manifest, dry_run=is_dry_run)


if __name__ == "__main__":
    main()
