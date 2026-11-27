---
name: midgley-region-onboarding
description: >-
  Guides adding or updating Midgley metro regions, RegionSpec definitions,
  regional metadata JSON profiles, tax/regulatory overrides, and webhook locale
  routing. Use when onboarding a new metro area, changing regional topology or
  aliases, or updating regional metadata and dashboard cards.
---

# Midgley Metro Region Onboarding & Topology Updates

Use this runbook when adding a new metro region, modifying `RegionSpec` or region aliases, or updating regional logistics, tax, or metadata schemas.

## 1. Verify Current Regional Registry

Do not rely on archived region counts from reference prose. Inspect the live registry first:

```sh
python scripts/manage_regions.py list
```

Also inspect:
- `src/locations/specs.py` (`RegionSpec`, `REGIONAL_SPECS`, `get_effective_tax_rate()`)
- `src/locations/runner.py`
- `src/regional_metadata.py`
- `data/regional_metadata/`

## 2. Core Code & Metadata Changes

1. **Declarative Spec (`src/locations/specs.py`)**:
   - Add or update the `RegionSpec` entry with accurate `region_key`, `slug`, `display_name`, `padd`, `wholesale_spot_col`, `eia_retail_series_id`, `diesel_series_id`, `baseline_tax_rate`, `sub_locales`, `primary_refinery`, `primary_pipeline`, coordinates, and `dedicated_page_url`.
   - Keep point-in-time tax suspension logic grounded in announcement provenance (`get_effective_tax_rate()` -> `src/rvp_regulations.py`).
2. **Regional Runner & Module**:
   - Confirm `src/locations/runner.py` and `src/locations/<slug>/` resolve the region cleanly without substituting national retail actuals for missing local actuals.
3. **Schema-Valid Metadata Profile (`data/regional_metadata/<region_id>.json`)**:
   - Scaffold or update the JSON profile (can bootstrap with `python scripts/manage_regions.py create --region-id <region_id> --name "<Display Name>" --zip <zip>`).
   - Ensure the profile includes all required structured sections:
     - `econometric_drivers`
     - `refining_logistics`
     - `tax_structure`
     - `infrastructure_delivery`
     - `shock_scenarios`
4. **Webhook & Event Scoping**:
   - Update locale resolution (`resolve_target_locales()` / `TRIGGER_KEYWORDS`) and applicable supplying-operator coverage so local disruptions are scoped to affected metros rather than broadcast nationally.

## 3. Dashboards, Static APIs, & Companion Docs

1. **Dashboard & Static API**:
   - Verify regional card rendering and dedicated page generation in `src/dashboard_generator.py` and static JSON export in `src/static_api_exporter.py` (`/api/v1/combined_<slug>.json`).
   - Regenerate affected pages only from a controlled valid-data state; never publish mocks or test fixtures.
2. **Documentation & Self-Hosting**:
   - Update affected regional/architecture documentation and `SELF_HOSTING.md`, then run `python scripts/verify_docs_parity.py --sync`.
   - When reconciling to the `self-hosted` branch during an authorized release, preserve its blank-slate national/default scope.

## 4. Verification

```sh
ruff check .
TESTING=1 pytest -v tests/test_docs_links.py
TESTING=1 pytest -v tests/test_dashboard_generator.py
```

Add or update a focused regional test (e.g., `tests/test_<slug>_regional.py`) verifying `RegionSpec` lookup, metadata schema completeness, and point-in-time tax resolution.
