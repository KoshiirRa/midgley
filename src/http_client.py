"""
Unified HTTP Client & Resilient Session Factory (src/http_client.py)

Provides a standardized requests.Session factory with:
- Connection pooling and urllib3 exponential retry backoff on HTTP 429 and 5xx responses.
- Automatic handling of 'Retry-After' headers.
- Default connection (3.05s) and read (20.0s) timeouts preventing hanging sockets.
- Standardized User-Agent across all external data connectors.
"""

import os
import logging
from typing import Optional, Tuple, Union, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT = 3.05
DEFAULT_READ_TIMEOUT = 20.0
DEFAULT_TIMEOUT: Tuple[float, float] = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT)

DEFAULT_USER_AGENT = os.getenv(
    "MIDGLEY_USER_AGENT",
    "Midgley-Energy-Analytics/0.8.5 (+https://github.com/KoshiirRa/midgley)"
)

DEFAULT_RETRY_STATUSES = (429, 500, 502, 503, 504)


class TimeoutHTTPAdapter(HTTPAdapter):
    """
    Custom HTTPAdapter that enforces default connect/read timeouts
    if none are explicitly supplied to session.get() or session.post().
    """
    def __init__(self, *args, timeout: Optional[Union[float, Tuple[float, float]]] = None, **kwargs):
        self.timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def get_retry_strategy(
    total: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: Tuple[int, ...] = DEFAULT_RETRY_STATUSES,
    raise_on_status: bool = False
) -> Retry:
    """Creates a urllib3 Retry instance with exponential backoff and Retry-After support."""
    return Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=raise_on_status,
        respect_retry_after_header=True,
        allowed_methods=["GET", "POST", "HEAD", "OPTIONS"]
    )


def get_session(
    timeout: Union[float, Tuple[float, float]] = DEFAULT_TIMEOUT,
    retries: int = 3,
    backoff_factor: float = 0.5,
    pool_connections: int = 10,
    pool_maxsize: int = 20,
    user_agent: Optional[str] = None
) -> requests.Session:
    """
    Creates and returns a configured requests.Session with connection pooling,
    exponential retry backoff, and default timeout enforcement.
    """
    session = requests.Session()
    retry_strategy = get_retry_strategy(total=retries, backoff_factor=backoff_factor)
    adapter = TimeoutHTTPAdapter(
        timeout=timeout,
        max_retries=retry_strategy,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    ua = user_agent or DEFAULT_USER_AGENT
    session.headers.update({"User-Agent": ua})
    return session


_GLOBAL_HTTP_SESSION: Optional[requests.Session] = None


def get_global_session() -> requests.Session:
    """Returns a shared global requests.Session singleton."""
    global _GLOBAL_HTTP_SESSION
    if _GLOBAL_HTTP_SESSION is None:
        _GLOBAL_HTTP_SESSION = get_session()
    return _GLOBAL_HTTP_SESSION


def http_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[Union[float, Tuple[float, float]]] = None,
    session: Optional[requests.Session] = None,
    **kwargs
) -> requests.Response:
    """Convenience wrapper for performant GET requests using unified session."""
    s = session or get_global_session()
    req_headers = dict(headers or {})
    return s.get(url, params=params, headers=req_headers, timeout=timeout or DEFAULT_TIMEOUT, **kwargs)


def http_post(
    url: str,
    data: Optional[Any] = None,
    json: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[Union[float, Tuple[float, float]]] = None,
    session: Optional[requests.Session] = None,
    **kwargs
) -> requests.Response:
    """Convenience wrapper for performant POST requests using unified session."""
    s = session or get_global_session()
    req_headers = dict(headers or {})
    return s.post(url, data=data, json=json, headers=req_headers, timeout=timeout or DEFAULT_TIMEOUT, **kwargs)
