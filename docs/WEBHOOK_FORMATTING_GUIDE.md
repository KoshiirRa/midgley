# Strategy 4 Incoming Webhook Call Formatting & Setup Guide

This guide details how to format, sign, and push real-time breaking news, social media posts, and market alerts to the **Midgley API Gateway** (`POST /api/v1/events/webhook`).

---

## 1. Overview & Gateway Endpoint

* **Endpoint URL:** `POST /api/v1/events/webhook`
* **Content-Type:** `application/json`
* **Authentication Header:** `X-Midgley-Signature: sha256=<hmac_hex_digest>` (Optional in local dev, mandatory in production when `MIDGLEY_WEBHOOK_SECRET` is set).

Strategy 4 serves as an event-driven ingestion hub that evaluates incoming payloads in real time, extracts factor impact vectors via tiered LLM scoring, triggers dynamic 15-minute response cache invalidation, logs intraday prediction revisions, and updates affected regional metro web app dashboards.

---

## 2. Payload Schema & Flexible Field Alias Matrix

The Midgley Webhook Gateway includes an automatic **Payload Transformer** (`WebhookRequest` schema in `src/api_server.py`) that accepts standard JSON payloads from third-party automation tools (Zapier, IFTTT, Make.com, TradingView, Google Alerts) without requiring custom pre-processing.

### Field Alias Resolution Matrix

| Standard Parameter | Field Fallback Resolution Order | Default / Fallback | Description |
| :--- | :--- | :--- | :--- |
| **`headline`** | `headline` → `title` → `text` → `summary` → `tweet_content` → `article_title` → `content` → `message` | *Required (non-empty)* | Breaking news or post text to score. |
| **`url`** | `url` → `link` → `article_url` → `web_url` → `href` → `source_url` | `""` | Source article or alert URL. |
| **`source`** | `source` → `origin` → `provider` → `channel` → `service` → `sender` | `"Webhook_Push"` | Origin identifier string. |

---

## 3. HMAC-SHA256 Signature Verification

To prevent unauthorized payload injection, production instances enforce HMAC-SHA256 signature verification via the `X-Midgley-Signature` header when `MIDGLEY_WEBHOOK_SECRET` is defined in the environment.

### Calculating the Signature
1. Compute the HMAC-SHA256 digest over the raw JSON payload bytes using your shared secret:
   $$\text{Signature} = \text{HMAC-SHA256}(\text{MIDGLEY\_WEBHOOK\_SECRET}, \text{RawBodyBytes})$$
2. Send the resulting 64-character lowercase hex string in the header:
   ```http
   X-Midgley-Signature: sha256=a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0
   ```

### IPASIS IP Gateway Security & Threat Filtering (Issue #87)
In addition to HMAC signatures, incoming client IP addresses are inspected by the **IPASIS Security Verifier** (`src/ipasis_security.py`).
- **IP Extraction**: Client IP is extracted from proxy headers (`CF-Connecting-IP` → `X-Forwarded-For` → `X-Real-IP` → `request.client.host`).
- **Tor & Abuse Filtering**: Incoming requests originating from Tor exit nodes (`privacy.Tor == True`) or malicious proxy/abuse subnets are blocked immediately with **HTTP 403 Forbidden**:
  ```json
  {
    "detail": "Forbidden: Incoming request origin IP '87.118.116.103' flagged as high-risk by IPASIS security filter."
  }
  ```
- **Local & Private IP Bypasses**: Local loopback and RFC 1918 private subnets (`127.0.0.1`, `10.x.x.x`, `192.168.x.x`, `testclient`) bypass external calls automatically with $0.00 cost.
- **Fail-Open Resilience**: If the external IPASIS API is unreachable or times out (2.0s timeout), the gateway safely fails open and processes legitimate webhooks with zero downtime.
- **Telemetry Accounting**: Daily API request accounting (used / 100 allowance) and security stats are exposed at `GET /api/v1/security/ip-status` and rendered on `docs/telemetry.html`.

---

## 4. Regional Metro Target Routing Matrix

Incoming headlines are automatically scanned by `resolve_target_locales()` in `src/intraday_event_monitor.py` to route shock revisions directly to affected regional metro agents:

| Regional Metro Locale | Trigger Keywords & Infrastructure Hubs | Affected Regional Models |
| :--- | :--- | :--- |
| **Tulsa** | `tulsa`, `cushing`, `sinclair`, `hf sinclair`, `west tulsa` | Tulsa OK Metro (Cushing WTI Hub) |
| **Newark** | `newark`, `delaware city`, `delaware`, `padd 1b`, `padd1b` | Newark DE / NYC Tri-State (PADD 1B) |
| **Cincinnati** | `cincinnati`, `catlettsburg`, `ohio river`, `markland lock`, `mcalpine lock` | Cincinnati Tri-State (Ohio River Logistics) |
| **Greenville & Charlotte** | `colonial pipeline`, `greenville`, `charlotte`, `selma`, `paw creek` | PADD 1C Colonial Pipeline Hubs |
| **Oakland** | `oakland`, `sf bay`, `san francisco`, `richmond refinery`, `carb`, `california` | Oakland / SF Bay Area (PADD 5 CARB) |
| **Port St. Lucie** | `port st. lucie`, `port st lucie`, `florida`, `waterborne freight` | Port St. Lucie (PADD 1C Freight Terminal) |
| **National** | *Default fallback for macroeconomic or multi-region events* | National RBOB Commodity Benchmark |

---

## 5. Integration Recipes by Provider

### Recipe 1: IFTTT / RSS Applet (Google Alerts)
* **URL:** `https://your-midgley-domain.com/api/v1/events/webhook`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Body:**
  ```json
  {
    "title": "{{EntryTitle}}",
    "link": "{{EntryUrl}}",
    "origin": "IFTTT_GoogleAlerts"
  }
  ```

### Recipe 2: Zapier Webhook Action (Executive Social Posts)
* **URL:** `https://your-midgley-domain.com/api/v1/events/webhook`
* **Payload Type:** `json`
* **Data:**
  ```json
  {
    "tweet_content": "OPEC must increase production immediately to lower retail gas prices!",
    "url": "https://x.com/post/123456789",
    "provider": "Zapier_X_Feed"
  }
  ```

### Recipe 3: TradingView Custom Alert (Crack Spread & Volatility Spikes)
* **Webhook URL:** `https://your-midgley-domain.com/api/v1/events/webhook`
* **Message Payload:**
  ```json
  {
    "text": "3-2-1 Crack Spread Spike Alert: NYMEX RBOB margin surges past $32.50/bbl",
    "url": "https://www.tradingview.com/chart",
    "source": "TradingView_AlertBot"
  }
  ```

### Recipe 4: cURL CLI Example with Python Signature Generator
```bash
# Set secret
SECRET="your_shared_webhook_secret"
PAYLOAD='{"title": "HF Sinclair West Tulsa Refinery Unit Outage Forces Flaring", "url": "https://news.google.com/articles/789", "source": "CLI_Tester"}'

# Compute HMAC signature
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

# Send HTTP POST request
curl -X POST "https://your-midgley-domain.com/api/v1/events/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Midgley-Signature: sha256=$SIG" \
  -d "$PAYLOAD"
```

---

## 6. API Response Example

```json
{
  "status": "success",
  "processed_at": "2026-09-03T18:35:00.123456",
  "result": {
    "timestamp": "2026-09-03T18:35:00.123456",
    "headline": "HF Sinclair West Tulsa Refinery Unit Outage Forces Flaring",
    "source": "CLI_Tester",
    "url": "https://news.google.com/articles/789",
    "is_anomaly": true,
    "target_locales": [
      "Tulsa"
    ],
    "scores": {
      "geopolitical_risk": 0.0,
      "supply_disruption": 0.65,
      "opec_action": 0.0,
      "demand_sentiment": 0.0,
      "overall_price_pressure": 0.45
    }
  }
}
```
