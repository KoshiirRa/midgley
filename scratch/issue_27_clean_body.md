## Summary
Restructure the Midgley public web dashboard (`docs/`) to improve navigation and detail hierarchy across multiple target forecast locales:

1. **Main Overview Page (`/` / `index.html`)**: General overview of Midgley architecture, listing current and projected 5-day forecasts for each active locale (National Wholesale RBOB & Tulsa Retail Gas), accuracy progression, and core feature pillars.
2. **National Wholesale RBOB Locale Page (`/national` / `national.html`)**: Move full details for National Wholesale RBOB (commodity futures, crack spreads, time-series prediction graph, out-of-time error metrics, global maritime shock scenarios) to a dedicated page.
3. **Tulsa Retail Gas Locale Page (`/tulsa` / `tulsa.html`)**: Move full details for Tulsa Metro Retail Gas (live pump price anchor $3.89/gal, Cushing WTI hub dynamics, West Tulsa HF Sinclair refinery, localized tornado/freeze shock scenarios) to a dedicated page.
4. **Educational Math Guide (`/math` / `math.html`)**: Retain separate educational guide detailing all 9 feature layers & equations.
