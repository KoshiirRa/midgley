"""
Milestone Checker & Model Version Auto-Promoter Module (src/milestone_checker.py)

Monitors GitHub milestones for the Midgley project. When all component issues of a model
milestone are closed (open_issues == 0 and closed_issues > 0), this module:
1. Closes the completed milestone on GitHub.
2. Auto-promotes the active model version string across src/__init__.py, src/api_server.py,
   src/prediction_logger.py, and AGENTS.md.
3. Outputs promotion details for integration with nightly dev release workflows.
"""

import os
import re
import json
import logging
import subprocess
from typing import Optional, Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO = os.environ.get("GITHUB_REPOSITORY", "KoshiirRa/midgley")

def get_milestones(repo: str = REPO) -> List[Dict[str, Any]]:
    """Fetch all open and closed milestones for the repository."""
    cmd = ["gh", "api", f"repos/{repo}/milestones?state=all"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
        return json.loads(res.stdout)
    except Exception as e:
        logger.error(f"Failed to fetch milestones for {repo}: {e}")
        return []

def close_milestone(repo: str, milestone_number: int) -> bool:
    """Closes a completed milestone on GitHub."""
    cmd = ["gh", "api", "-X", "PATCH", f"repos/{repo}/milestones/{milestone_number}", "-f", "state=closed"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
        logger.info(f"Successfully closed GitHub Milestone #{milestone_number} on {repo}.")
        return True
    except Exception as e:
        logger.error(f"Failed to close Milestone #{milestone_number}: {e}")
        return False

def update_codebase_model_version(old_version_str: str, new_version_str: str, new_codename: str) -> List[str]:
    """
    Updates model version references in codebase files.
    Returns list of modified file paths.
    """
    modified_files = []
    
    files_to_check = [
        "src/__init__.py",
        "src/api_server.py",
        "src/prediction_logger.py",
        "AGENTS.md"
    ]
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        new_content = content
        
        if file_path == "src/__init__.py":
            new_content = re.sub(
                r'__model_version__\s*=\s*".*?"',
                f'__model_version__ = "{new_version_str} {new_codename}"',
                new_content
            )
            new_content = re.sub(
                r'Model Engine Version:\s*.*',
                f'Model Engine Version: {new_version_str} {new_codename}',
                new_content
            )
        elif file_path == "src/api_server.py":
            new_content = re.sub(
                r'"model_version":\s*".*?"',
                f'"model_version": "{new_version_str} {new_codename}"',
                new_content
            )
        elif file_path == "src/prediction_logger.py":
            new_content = re.sub(
                r'model_version:\s*str\s*=\s*".*?"',
                f'model_version: str = "{new_version_str}-{new_codename}"',
                new_content
            )
        elif file_path == "AGENTS.md":
            new_content = re.sub(
                r'Model v\d+\.\d+.*?(Finlight-LLM|Engine)?',
                f'{new_version_str} "{new_codename}" Engine',
                new_content,
                count=1
            )
            
        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            modified_files.append(file_path)
            logger.info(f"Updated model version in {file_path}")
            
    return modified_files

def check_and_promote_model(repo: str = REPO) -> Optional[Dict[str, Any]]:
    """
    Checks if any open model milestone has 0 open issues and > 0 closed issues.
    If found, promotes the model version and closes the milestone.
    """
    milestones = get_milestones(repo)
    if not milestones:
        logger.info("No milestones returned from GitHub API.")
        return None
        
    promoted_info = None
    
    # Filter and sort model milestones (e.g. title starts with 'Regular Model' or 'Diesel Model')
    model_milestones = []
    for m in milestones:
        title = m.get("title", "")
        match = re.search(r'(Regular\s+Model|Diesel\s+Model|Gasoline\s+Model|Unleaded\s+Model|Model)\s+(v\d+\.\d+)\s+["\']?([^"\']+)["\']?', title)
        if match:
            lineage_name = match.group(1) # e.g. "Regular Model"
            version_str = match.group(2)  # e.g. "v1.5"
            codename = match.group(3)     # e.g. "Houdry"
            model_milestones.append({
                "number": m["number"],
                "title": title,
                "lineage": lineage_name,
                "version": version_str,
                "codename": codename,
                "open_issues": m.get("open_issues", 0),
                "closed_issues": m.get("closed_issues", 0),
                "state": m.get("state", "open")
            })
            
    # Sort by version number (v1.5, v1.6, v2.0)
    model_milestones.sort(key=lambda x: [int(p) for p in x["version"].lstrip('v').split('.')])
    
    for m in model_milestones:
        logger.info(f"Evaluating Milestone #{m['number']} '{m['title']}': {m['open_issues']} open, {m['closed_issues']} closed (State: {m['state']}).")
        
        # Check completion criteria: 0 open issues and > 0 closed issues
        if m["open_issues"] == 0 and m["closed_issues"] > 0:
            logger.info(f"Milestone '{m['title']}' is 100% COMPLETE ({m['closed_issues']} component issues closed)!")
            
            # Close milestone on GitHub if still open
            if m["state"] == "open":
                close_milestone(repo, m["number"])
                
            # Perform codebase update
            old_ver = "v1.4"
            new_ver = m["version"]
            codename = m["codename"]
            
            modified = update_codebase_model_version(old_ver, new_ver, codename)
            
            promoted_info = {
                "milestone_number": m["number"],
                "title": m["title"],
                "version": new_ver,
                "codename": codename,
                "closed_issues": m["closed_issues"],
                "modified_files": modified
            }
            break

    return promoted_info

if __name__ == "__main__":
    result = check_and_promote_model()
    if result:
        print(f"PROMOTED:{json.dumps(result)}")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output and os.path.exists(github_output):
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"model_promoted=true\n")
                f.write(f"promoted_version={result['version']}\n")
                f.write(f"promoted_codename={result['codename']}\n")
                f.write(f"promoted_title={result['title']}\n")
    else:
        print("NO_PROMOTION")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output and os.path.exists(github_output):
            with open(github_output, "a", encoding="utf-8") as f:
                f.write("model_promoted=false\n")
