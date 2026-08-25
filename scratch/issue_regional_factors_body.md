## Overview & Feature Description

Enhance all localized regional public web dashboard pages (`/tulsa`, `/newark`, `/cincinnati`, `/oakland`, and `/bayarea`) to display dedicated visual cards detailing their unique regional econometric drivers, refining logistics, tax structures, delivery hub dynamics, and localized physical risk factors.

---

## Targeted Regional Pages & Local Driver Requirements

### 1. Tulsa Metro Retail (`/tulsa` & `docs/tulsa.html`)
- **Cushing WTI Hub Logistics**: Physical crude delivery hub interconnections and storage capacity utilization.
- **West Tulsa HF Sinclair Refinery**: Local refining dynamics (125,000 bpd capacity), EF-3 tornado risk alerts, and PADD 2 Group 3 spot rack margins.

### 2. Newark Delaware Metro Retail (`/newark` & `docs/newark.html`)
- **PBF Delaware City Refinery**: PADD 1B Central Atlantic refining dynamics (180,000 bpd capacity).
- **Delaware Bay Lightering**: Big Stone Anchorage deepwater tanker lightering advisories.
- **C&D Canal Detour Events**: 300 nm marine barge detour around Delmarva Peninsula (+$0.097/gal rack margin expansion).

### 3. Cincinnati OH / NKY Tri-State (`/cincinnati` & `docs/cincinnati.html`)
- **Dual-State Tax Differential**: Persistent cross-river retail price gap between Ohio state motor fuel tax ($0.385/gal) and Kentucky state motor fuel tax ($0.260/gal).
- **Ohio & Mississippi River Logistics**: Marathon Catlettsburg KY refinery dynamics (291,000 bpd capacity) and Lower Mississippi River low-water barge bottleneck restrictions (Cairo, IL confluence & Memphis draft limits).

### 4. Oakland CA Metro Retail (`/oakland` & `docs/oakland.html`)
- **CARB Regulatory Breakdown**: Explicit statutory breakdown card for California's $0.953/gal state tax/fee burden ($0.634 state excise, ~$0.250 Cap-and-Trade, ~$0.185 LCFS overhead, ~$0.150 local sales/UST fees).
- **Chevron Richmond Crack Spread**: PADD 5 refining crack spread (`oakland_retail - brent / 42`).
- **Physical Hazard Suite**: Dedicated risk cards for USGS Hayward fault quakes ($M \ge 6.0$), CAL FIRE & PG&E Public Safety Power Shutoff (PSPS) wildfire blackouts, and NOAA PTWC Pacific tsunami alerts.

### 5. SF Bay Area 9-County Region (`/bayarea` & `docs/bayarea.html`)
- **9-County Price Matrix**: Detailed price card comparing San Francisco ($5.120), San Jose / Silicon Valley ($4.980), Oakland ($4.950), and North Bay / Solano ($4.850).
- **PADD 5 Refining Island**: West Coast isolation (zero interstate product pipelines crossing Sierra Nevada) and Carquinez Strait crude tanker berth logistics.

---

## Implementation Tasks

- [ ] Create standardized modular CSS layout component for `Unique Regional Drivers & Infrastructure Matrix` card.
- [ ] Inject locale-specific data feeds and dynamic indicator badges into `src/dashboard_generator.py`.
- [ ] Verify responsive layout across mobile, tablet, and desktop viewports on GitHub Pages (`docs/`).
- [ ] Add unit tests in `tests/test_dashboard_generator.py` asserting presence of unique regional factor cards across all regional HTML pages.
