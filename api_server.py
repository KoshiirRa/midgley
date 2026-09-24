"""
Root Entrypoint Proxy Gateway (api_server.py)

Forwarding proxy to canonical src.api_server:app (Issue #425).
Directs all API execution, ASGI workers, and MCP server transports
to the maintained source module at src/api_server.py.
"""

from src.api_server import app, create_app  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_server:app", host="0.0.0.0", port=8000, reload=False)
