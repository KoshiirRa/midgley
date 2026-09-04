import json
import subprocess
import time
import sys

# Ensure UTF-8 output encoding for Windows host
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ID = "PVT_kwHOAVnZGM4BhxKn"

FIELDS = {
    "status": "PVTSSF_lAHOAVnZGM4BhxKnzhgrsx0",
    "priority": "PVTSSF_lAHOAVnZGM4BhxKnzhgrsyk",
    "workstream": "PVTSSF_lAHOAVnZGM4BhxKnzhgrsyo",
    "effort": "PVTSSF_lAHOAVnZGM4BhxKnzhgrsys",
    "target": "PVTSSF_lAHOAVnZGM4BhxKnzhgrsyw",
    "risk": "PVTSSF_lAHOAVnZGM4BhxKnzhgrsy0"
}

OPTIONS = {
    "status": {
        "Ready": "54857b6b",
        "Done": "3e1df50f"
    },
    "priority": {
        "Critical": "d564b7e5",
        "High": "f4f3f23c",
        "Medium": "d61d91c0",
        "Low": "b93a2b79",
        "Super Low": "235e1887"
    },
    "workstream": {
        "Trading Safety": "1a6877fb",
        "Data & Providers": "ba4b3da1",
        "Research & Quant": "35d00039",
        "Reporting & Tax": "a367eb22",
        "Automation & Operations": "e415ad37",
        "Security & Infrastructure": "cc4d99a6",
        "Design": "3e388094",
        "UI & UX": "e5a74c4b"
    },
    "effort": {
        "Small": "dd20762c",
        "Medium": "43e0d54e",
        "Large": "fff9fbc4"
    },
    "target": {
        "Now": "cc65545a",
        "Next": "19ed62c8",
        "Later": "65d302e5"
    },
    "risk": {
        "Low": "29db45fd",
        "Medium": "d6614df7",
        "High": "0400aed9"
    }
}

# Master Triage Config for all 53 Issues
TRIAGE_DATA = {
    1: {"milestone": "v0.3.0", "labels": ["testing"], "status": "Done", "workstream": "Automation & Operations", "priority": "Super Low", "target": "Later", "effort": "Small", "risk": "Low"},
    2: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    7: {"milestone": "v0.6", "labels": ["enhancement", "integration"], "status": "Ready", "workstream": "UI & UX", "priority": "Medium", "target": "Next", "effort": "Large", "risk": "Medium"},
    16: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    20: {"milestone": "v0.6", "labels": ["enhancement", "integration"], "status": "Ready", "workstream": "UI & UX", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    21: {"milestone": "v0.6", "labels": ["enhancement", "integration"], "status": "Ready", "workstream": "UI & UX", "priority": "Medium", "target": "Next", "effort": "Large", "risk": "Low", "cross_link": true},
    22: {"milestone": "v0.6", "labels": ["enhancement", "integration"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    25: {"milestone": "v0.3.1", "labels": ["bug", "modeling"], "status": "Done", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    26: {"milestone": "v0.3.1", "labels": ["bug", "documentation"], "status": "Done", "workstream": "UI & UX", "priority": "Medium", "target": "Now", "effort": "Small", "risk": "Low"},
    27: {"milestone": "v0.3.1", "labels": ["documentation", "enhancement", "dashboard"], "status": "Done", "workstream": "UI & UX", "priority": "Medium", "target": "Now", "effort": "Medium", "risk": "Low"},
    29: {"milestone": "v0.3.1", "labels": ["enhancement", "infrastructure"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "Medium", "target": "Now", "effort": "Small", "risk": "Low"},
    30: {"milestone": "v0.3.1", "labels": ["enhancement", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "Medium", "target": "Now", "effort": "Small", "risk": "Low"},
    31: {"milestone": "v0.3.1", "labels": ["enhancement", "modeling"], "status": "Done", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    32: {"milestone": "v0.3.1", "labels": ["enhancement", "modeling"], "status": "Done", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    33: {"milestone": "v0.3.1", "labels": ["documentation", "enhancement"], "status": "Done", "workstream": "Automation & Operations", "priority": "Low", "target": "Now", "effort": "Small", "risk": "Low"},
    36: {"milestone": "v0.3.1", "labels": ["enhancement", "data-ingestion"], "status": "Done", "workstream": "Data & Providers", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    38: {"milestone": "v0.4", "labels": ["documentation", "enhancement", "api"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    39: {"milestone": "v0.3.1", "labels": ["enhancement", "api", "token-efficiency"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    40: {"milestone": "v0.4", "labels": ["enhancement", "api", "security"], "status": "Ready", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    41: {"milestone": "Diesel Model v1.0 \"Diesel\"", "labels": ["enhancement", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Large", "risk": "Medium"},
    42: {"milestone": "v0.3.1", "labels": ["bug", "enhancement"], "status": "Done", "workstream": "Data & Providers", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    44: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "modeling"], "status": "Done", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low", "done_reason": "Implemented `compute_quantile_uncertainty_bands` in `src/models.py`."},
    45: {"milestone": "v0.4", "labels": ["bug", "enhancement", "infrastructure"], "status": "Ready", "workstream": "Security & Infrastructure", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    46: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    47: {"milestone": "v0.5", "labels": ["documentation", "enhancement", "dashboard", "api"], "status": "Ready", "workstream": "UI & UX", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    48: {"milestone": "v0.4", "labels": ["enhancement", "api"], "status": "Ready", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    49: {"milestone": "v0.4", "labels": ["enhancement", "integration", "api"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low", "done_reason": "Implemented `simulate_fuel_market_shock` tool in `src/mcp_server.py`."},
    50: {"milestone": "v0.4", "labels": ["enhancement", "integration", "api"], "status": "Ready", "workstream": "Data & Providers", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    51: {"milestone": "v0.3.1", "labels": ["enhancement", "data-ingestion"], "status": "Done", "workstream": "Data & Providers", "priority": "Low", "target": "Now", "effort": "Small", "risk": "Low"},
    52: {"milestone": "v0.5", "labels": ["documentation", "enhancement"], "status": "Ready", "workstream": "UI & UX", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    53: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["documentation", "enhancement", "data-ingestion"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    54: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    55: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    56: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    57: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    58: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    59: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    60: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    61: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    62: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    63: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    64: {"milestone": "v0.4", "labels": ["documentation", "enhancement"], "status": "Done", "workstream": "Automation & Operations", "priority": "Low", "target": "Now", "effort": "Small", "risk": "Low"},
    65: {"milestone": "v0.4", "labels": ["testing", "security"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "Low", "target": "Now", "effort": "Small", "risk": "Low"},
    66: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    67: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    68: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    69: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    70: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "modeling", "integration"], "status": "Ready", "workstream": "Research & Quant", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    71: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    73: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    74: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    75: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    77: {"milestone": "v0.4", "labels": ["enhancement", "integration", "api"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    78: {"milestone": "v0.4", "labels": ["enhancement", "integration", "api"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    79: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    80: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["enhancement", "infrastructure", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    81: {"milestone": "v0.7", "labels": ["enhancement", "infrastructure"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    82: {"milestone": "v0.4", "labels": ["enhancement", "infrastructure"], "status": "Ready", "workstream": "Security & Infrastructure", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    83: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    84: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    85: {"milestone": "v0.7", "labels": ["enhancement", "infrastructure", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "Low", "target": "Later", "effort": "Large", "risk": "Low"},
    86: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    87: {"milestone": "v0.4", "labels": ["enhancement", "api", "security"], "status": "Ready", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    88: {"milestone": "v0.7", "labels": ["enhancement", "infrastructure"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    89: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    90: {"milestone": "v0.7", "labels": ["enhancement", "infrastructure", "integration"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    93: {"milestone": "Regular Model v1.6 \"Ipatieff\"", "labels": ["enhancement", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Medium"},
    94: {"milestone": "Regular Model v1.6 \"Ipatieff\"", "labels": ["enhancement", "infrastructure", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "Low", "target": "Later", "effort": "Large", "risk": "Medium"},
    95: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    96: {"milestone": "v0.7", "labels": ["enhancement", "infrastructure"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    97: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["enhancement", "infrastructure", "data-ingestion"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    98: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["enhancement", "infrastructure", "api"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    99: {"milestone": "v0.7", "labels": ["enhancement", "infrastructure", "dashboard"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    110: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Done", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    111: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Done", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    121: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "infrastructure", "modeling"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    122: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Done", "workstream": "Data & Providers", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low", "done_reason": "Implemented `EIA930GridMonitorConnector` in `src/data_ingestion.py`."},
    125: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["bug", "dashboard", "api"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    129: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    135: {"milestone": "v0.4", "labels": ["enhancement", "dashboard"], "status": "Done", "workstream": "UI & UX", "priority": "Medium", "target": "Now", "effort": "Small", "risk": "Low"},
    136: {"milestone": "v0.4", "labels": ["enhancement", "infrastructure", "integration"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    137: {"milestone": "v0.4", "labels": ["dependencies", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "Low", "target": "Now", "effort": "Small", "risk": "Low"},
    138: {"milestone": "v0.4", "labels": ["dependencies", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "Low", "target": "Now", "effort": "Small", "risk": "Low"},
    139: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation", "modeling"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    140: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["weekly-review", "documentation", "modeling"], "status": "Done", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    141: {"milestone": "v0.4", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Done", "workstream": "Data & Providers", "priority": "High", "target": "Now", "effort": "Large", "risk": "Low"},
    142: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["documentation", "modeling", "infrastructure"], "status": "Ready", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    143: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    144: {"milestone": "Regular Model v2.0 \"Hubbert\"", "labels": ["enhancement", "modeling", "infrastructure"], "status": "Ready", "workstream": "Research & Quant", "priority": "Low", "target": "Later", "effort": "Large", "risk": "Medium"},
    145: {"milestone": "Regular Model v2.0 \"Hubbert\"", "labels": ["enhancement", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "Low", "target": "Later", "effort": "Large", "risk": "Medium"},
    146: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Medium", "risk": "Low"},
    148: {"milestone": "v0.4", "labels": ["enhancement", "infrastructure", "api"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    149: {"milestone": "v0.4", "labels": ["enhancement", "data-ingestion", "token-efficiency"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    150: {"milestone": "v0.4", "labels": ["enhancement", "data-ingestion", "infrastructure"], "status": "Done", "workstream": "Data & Providers", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    151: {"milestone": "v0.4", "labels": ["enhancement", "infrastructure", "security"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    152: {"milestone": "v0.4", "labels": ["bug", "infrastructure", "integration"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    153: {"milestone": "v0.4", "labels": ["release", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    159: {"milestone": "v0.4", "labels": ["release", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    160: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "infrastructure"], "status": "Done", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    161: {"milestone": "v0.7", "labels": ["enhancement", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low", "done_reason": "Implemented in `workers/cache_worker.ts` and `workers/intraday_monitor_worker.ts` (`logToAxiom`, Sentry, Cloudflare native observability)."},
    162: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "infrastructure"], "status": "Done", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    163: {"milestone": "v0.4", "labels": ["bug", "infrastructure"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "Medium", "target": "Now", "effort": "Small", "risk": "Low"},
    164: {"milestone": "v0.4", "labels": ["bug", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "Medium", "target": "Now", "effort": "Small", "risk": "Low"},
    166: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "infrastructure"], "status": "Done", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    167: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Done", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    168: {"milestone": "v0.4", "labels": ["enhancement", "modeling"], "status": "Done", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    169: {"milestone": "v0.4", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Done", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    170: {"milestone": "v0.4", "labels": ["enhancement", "modeling"], "status": "Done", "workstream": "Research & Quant", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    182: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["documentation", "modeling"], "status": "Ready", "workstream": "Reporting & Tax", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    184: {"milestone": "v0.7", "labels": ["enhancement", "data-ingestion"], "status": "Done", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    185: {"milestone": "Regular Model v2.0 \"Hubbert\"", "labels": ["enhancement", "modeling"], "status": "Ready", "workstream": "Research & Quant", "priority": "High", "target": "Next", "effort": "Large", "risk": "Medium"},
    186: {"milestone": "Regular Model v2.0 \"Hubbert\"", "labels": ["enhancement", "infrastructure", "modeling", "integration"], "status": "Ready", "workstream": "Research & Quant", "priority": "Medium", "target": "Later", "effort": "Large", "risk": "Medium"},
    187: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["enhancement", "data-ingestion", "infrastructure", "api"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    188: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["enhancement", "infrastructure", "modeling", "integration"], "status": "Ready", "workstream": "Research & Quant", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
    189: {"milestone": "v0.4", "labels": ["enhancement", "token-efficiency", "infrastructure", "dashboard"], "status": "Ready", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    190: {"milestone": "v0.7", "labels": ["enhancement", "token-efficiency", "infrastructure"], "status": "Ready", "workstream": "Security & Infrastructure", "priority": "Medium", "target": "Later", "effort": "Medium", "risk": "Low"},
    191: {"milestone": "v0.5", "labels": ["documentation", "enhancement", "dashboard"], "status": "Ready", "workstream": "UI & UX", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    192: {"milestone": "v0.4", "labels": ["enhancement", "data-ingestion", "infrastructure", "api", "security"], "status": "Ready", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    193: {"milestone": "v0.4", "labels": ["release", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    196: {"milestone": "v0.4", "labels": ["enhancement", "api", "token-efficiency", "security"], "status": "Done", "workstream": "Security & Infrastructure", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    197: {"milestone": "v0.4", "labels": ["release", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    198: {"milestone": "v0.4", "labels": ["dependencies", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "Low", "target": "Now", "effort": "Small", "risk": "Low"},
    199: {"milestone": "v0.7", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    200: {"milestone": "v0.7", "labels": ["enhancement", "data-ingestion"], "status": "Ready", "workstream": "Data & Providers", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    201: {"milestone": "v0.4", "labels": ["release", "infrastructure"], "status": "Done", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Small", "risk": "Low"},
    202: {"milestone": "v0.4", "labels": ["enhancement", "infrastructure"], "status": "Ready", "workstream": "Security & Infrastructure", "priority": "Low", "target": "Later", "effort": "Small", "risk": "Low"},
    203: {"milestone": "v0.4", "labels": ["bug", "infrastructure", "modeling"], "status": "Ready", "workstream": "Automation & Operations", "priority": "High", "target": "Now", "effort": "Medium", "risk": "Low"},
    204: {"milestone": "Weekly Review v1.0 \"Audit\"", "labels": ["enhancement", "infrastructure", "weekly-review"], "status": "Ready", "workstream": "Automation & Operations", "priority": "Medium", "target": "Next", "effort": "Small", "risk": "Low"},
    205: {"milestone": "Regular Model v1.5 \"Houdry\"", "labels": ["enhancement", "data-ingestion", "modeling"], "status": "Ready", "workstream": "Data & Providers", "priority": "Medium", "target": "Next", "effort": "Medium", "risk": "Low"},
}

def edit_project_field(item_id, field_key, option_name):
    field_id = FIELDS[field_key]
    option_id = OPTIONS[field_key][option_name]
    cmd = [
        "gh", "project", "item-edit",
        "--id", item_id,
        "--project-id", PROJECT_ID,
        "--field-id", field_id,
        "--single-select-option-id", option_id
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        print(f"Error editing project item {item_id} field {field_key}: {res.stderr}")

def edit_issue_metadata(num, milestone, labels):
    cmd = ["gh", "issue", "edit", str(num), "--milestone", milestone]
    for lbl in labels:
        cmd.extend(["--add-label", lbl])
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        print(f"Error editing issue #{num}: {res.stderr}")

def close_issue_completed(num, reason):
    comment_cmd = ["gh", "issue", "comment", str(num), "--body", f"Triaged & Resolved: {reason}"]
    subprocess.run(comment_cmd, capture_output=True, text=True, encoding='utf-8')
    close_cmd = ["gh", "issue", "close", str(num), "--reason", "completed"]
    res = subprocess.run(close_cmd, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        print(f"Error closing issue #{num}: {res.stderr}")

def add_android_auto_crosslink(num):
    comment_text = (
        "Triaged per Section 16 (Multi-Repository Issue Routing Directives for Client Applications):\n\n"
        "- This issue tracks the client application integration for Android Auto (`midgley-auto`).\n"
        "- Dedicated repository: [`KoshiirRa/midgley-auto`](https://github.com/KoshiirRa/midgley-auto).\n"
        "- Cross-linked main model endpoints: `/api/v1/advisor/recommendation` and `/api/v1/forecast` in `src/api_server.py`."
    )
    cmd = ["gh", "issue", "comment", str(num), "--body", comment_text]
    subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

def main():
    res = subprocess.run(['gh', 'project', 'item-list', '12', '--owner', 'KoshiirRa', '--format', 'json', '--limit', '200'], capture_output=True, encoding='utf-8')
    data = json.loads(res.stdout)
    items = data.get('items', [])
    inbox_items = [it for it in items if not it.get('status') or it.get('status') in ['Inbox', 'No Status']]

    print(f"Starting triage execution for remaining {len(inbox_items)} untriaged/inbox items...")

    success_count = 0
    for idx, item in enumerate(inbox_items, 1):
        content = item.get('content', {})
        num = content.get('number')
        item_id = item['id']
        title = content.get('title') or item.get('title', '')

        if num not in TRIAGE_DATA:
            print(f"WARNING: Issue #{num} ({title}) not found in TRIAGE_DATA dictionary!")
            continue

        cfg = TRIAGE_DATA[num]
        print(f"[{idx}/{len(inbox_items)}] Triaging #{num}...")

        # 1. Update GitHub issue milestone and labels
        edit_issue_metadata(num, cfg['milestone'], cfg['labels'])

        # 2. Update Project fields
        for fkey in ["status", "priority", "workstream", "effort", "target", "risk"]:
            val = cfg[fkey]
            edit_project_field(item_id, fkey, val)

        # 3. Special actions
        if cfg.get("cross_link"):
            add_android_auto_crosslink(num)

        if cfg["status"] == "Done" and cfg.get("done_reason"):
            close_issue_completed(num, cfg["done_reason"])

        success_count += 1
        time.sleep(0.2)

    print(f"\nSuccessfully triaged remaining {success_count} items!")

if __name__ == '__main__':
    main()
