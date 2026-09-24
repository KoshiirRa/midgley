# Security Policy

## Supported Versions

| Version | Supported | Security Maintenance |
| :--- | :---: | :--- |
| `0.7.x` | :white_check_mark: | Active production & vulnerability patches |
| `< 0.7.0` | :x: | End of life. Please upgrade to v0.7.0+ |

## Reporting a Vulnerability

We take the security of Midgley seriously. If you discover a potential vulnerability or security weakness in our models, API services, database integrations, or edge workers:

1. **Do NOT open a public GitHub issue.**
2. Send a confidential report to **m.cubed.3@gmail.com** with details on the vulnerability, steps to reproduce, and affected modules.
3. We will acknowledge receipt within 48 hours and work with you to test and deploy a patched release.

## Security Practices

* **Fail-Closed Administration:** Administrative endpoints fail closed with `HTTP 401 Unauthorized` if secrets are unset or invalid.
* **No Inline Tokens:** Sensitive API keys and tokens must never be passed in plain text in CLI arguments, process strings, or committed git artifacts.
* **Advisory File Locking:** All disk state mutations use atomic write engines and cross-platform advisory locking (`flock`/`msvcrt`) to prevent file corruption.
* **Webhook Replay Protection:** Webhook signatures enforce HMAC-SHA256 timestamp verification within a $\pm 300$-second tolerance window.
