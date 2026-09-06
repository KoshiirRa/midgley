# Release Notes - v0.4.5

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. GeoPandas Spatial Refinery Distance Buffering Engine for Metro Agents (Issue #95)
- **Core Spatial Buffering Engine (`src/spatial_refinery.py`):** Built `SpatialRefineryEngine` containing WGS84 (`EPSG:4326`) point locations, capacities, PADD regions, and primary locales for 11 key refining hubs, pipelines, and marine terminals (`HF_Sinclair_West_Tulsa`, `PBF_Delaware_City`, `Marathon_Catlettsburg`, `Chevron_Richmond`, `Valero_Benicia`, `Shell_PBF_Martinez`, `Colonial_Pipeline_Selma`, `Colonial_Pipeline_Paw_Creek`, `Port_Everglades_Terminal`, `Port_Canaveral_Terminal`, `Wood_River_Refinery`).
- **Web Mercator Projection & Multi-Ring Buffer Polygons (`EPSG:3857`):** Generates spatial buffer polygon rings across 5 radii (`25mi`, `50mi`, `100mi`, `250mi`, `500mi`) around refining infrastructure and computes projected spatial distances in miles.
- **Exponential Spatial Attenuation & Shock Multipliers:** Computes exponential spatial decay weight $w(d) = \exp(-d / 150.0)$, attenuating refinery outage shock impacts as distance increases from fence-line rack proximity out to inter-state pipeline boundaries. Scales price shock adjustments ($\Delta P_{\text{shock}}$) by refinery nameplate capacity ($\text{bpd}$), outage severity, and spatial distance-decay weight.
- **Spherical Haversine Fallback Engine:** Features an automatic fallback to mathematical spherical Haversine distance calculations when GeoPandas is uninstalled in lightweight container environments, ensuring 100% test pass rate and zero runtime exceptions.
- **Regional Metro Agent Integration:** Updated `DynamicRegionRunner.run_pipeline()` in `src/dynamic_region.py` and exported spatial decay helpers across all 7 regional metro calibration modules (`tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `port_st_lucie`).

---

## 🧪 Verification & Test Suite Results

- **Unit Test Suite Execution (`pytest tests/test_spatial_refinery.py`):**
  ```bash
  pytest tests/test_spatial_refinery.py -v
  ```
  **Result:** `11 passed` (100% pass rate in 1.27s on `dev-vm`).
- **Full Repository Test Suite Execution:**
  ```bash
  pytest
  ```
  **Result:** `314 passed` (100% pass rate across all 314 test items).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #95**: `[Feature Request] Implement GeoPandas Spatial Refinery Distance Buffering for Metro Agents` (Closed as completed)
