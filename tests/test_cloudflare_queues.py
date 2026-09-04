"""
Unit and Integration Test Suite for Cloudflare Queues Event Buffering & Batch Consumer Endpoint
(tests/test_cloudflare_queues.py - Issue #194)
"""

import os
import json
import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient

from src.api_server import app, QueueBatchRequest, WebhookRequest
from src.intraday_event_monitor import IntradayEventMonitor

client = TestClient(app)


def test_queue_batch_request_model():
    """Verifies Pydantic serialization and alias fallbacks for QueueBatchRequest."""
    payload = {
        "events": [
            {"title": "OPEC Emergency Production Cut Announced", "link": "https://energy.example.com/opec1"},
            {"headline": "Pipeline Halt Triggers Regional Gas Shortage", "url": "https://energy.example.com/pipe2", "source": "Zapier"}
        ],
        "batch_id": "batch_999",
        "queue_name": "intraday-event-queue"
    }
    req = QueueBatchRequest(**payload)
    assert len(req.events) == 2
    assert req.events[0].headline == "OPEC Emergency Production Cut Announced"
    assert req.events[0].url == "https://energy.example.com/opec1"
    assert req.events[1].headline == "Pipeline Halt Triggers Regional Gas Shortage"
    assert req.batch_id == "batch_999"


def test_queue_consumer_api_endpoint(monkeypatch):
    """Tests POST /api/v1/events/queue-consumer endpoint processing."""
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("MIDGLEY_ENV", "dev")
    
    payload = {
        "events": [
            {"headline": "Test Suite Tornado Risk Warning", "url": "https://weather.example.com/alert1", "source": "Test_Suite"},
            {"headline": "Test Suite Gasoline Import Tariff Spike", "url": "https://news.example.com/tariff1", "source": "Test_Suite"}
        ],
        "batch_id": "batch_test_101",
        "queue_name": "intraday-event-queue"
    }
    
    response = client.post("/api/v1/events/queue-consumer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["queue_name"] == "intraday-event-queue"
    assert data["batch_id"] == "batch_test_101"
    assert data["total_processed"] == 2
    assert len(data["events"]) == 2


def test_queue_consumer_signature_verification(monkeypatch):
    """Tests HMAC-SHA256 signature verification on queue consumer endpoint when MIDGLEY_WEBHOOK_SECRET is set."""
    secret = "test_queue_secret_123"
    monkeypatch.setenv("MIDGLEY_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("MIDGLEY_ENV", "prod")
    monkeypatch.delenv("TESTING", raising=False)

    payload = {
        "events": [
            {"headline": "Test Suite Unsigned Queue Event", "url": "https://example.com/1"}
        ]
    }
    raw_bytes = json.dumps(payload).encode("utf-8")

    # Unsigned request should fail with 401 Unauthorized
    resp_unauthorized = client.post("/api/v1/events/queue-consumer", content=raw_bytes, headers={"Content-Type": "application/json"})
    assert resp_unauthorized.status_code == 401

    # Signed request with valid HMAC signature should succeed with 200 OK
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
    resp_authorized = client.post(
        "/api/v1/events/queue-consumer",
        content=raw_bytes,
        headers={"Content-Type": "application/json", "X-Midgley-Signature": signature}
    )
    assert resp_authorized.status_code == 200
    assert resp_authorized.json()["status"] == "success"
