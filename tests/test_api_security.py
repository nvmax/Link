import pytest
from fastapi.testclient import TestClient
from src.api.server import app
from src.core.config import Config

client = TestClient(app)

def test_health_always_public():
    """Verify that the health check endpoint remains fully public and unblocked."""
    # Reset API_KEY config
    original_key = Config.API_KEY
    try:
        Config.API_KEY = "test_secret_key"
        response = client.get("/health")
        # Should be successful or service unavailable (503) if bot not initialized, but NOT 401 Unauthorized
        assert response.status_code != 401
    finally:
        Config.API_KEY = original_key

def test_api_unlocked_when_no_key():
    """Verify that if no API_KEY environment variable is configured, the security layer is bypassed."""
    original_key = Config.API_KEY
    try:
        Config.API_KEY = None
        # /api/models/progress should execute cleanly (or return empty dict)
        response = client.get("/api/models/progress")
        assert response.status_code == 200
        assert response.json() == {}
    finally:
        Config.API_KEY = original_key

def test_api_locked_with_key():
    """Verify that api endpoints are blocked when an API_KEY is defined and header is missing/incorrect."""
    original_key = Config.API_KEY
    try:
        Config.API_KEY = "super_secure_key"
        
        # Case 1: Missing Header
        response = client.get("/api/models/progress")
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
        
        # Case 2: Incorrect Header
        response = client.get("/api/models/progress", headers={"X-API-Key": "wrong_key"})
        assert response.status_code == 401
        
        # Case 3: Correct Header
        response = client.get("/api/models/progress", headers={"X-API-Key": "super_secure_key"})
        assert response.status_code == 200
        
        # Case 4: Correct Query Parameter
        response = client.get("/api/models/progress?api_key=super_secure_key")
        assert response.status_code == 200
    finally:
        Config.API_KEY = original_key

def test_options_preflight_bypassed():
    """Verify that browser CORS preflight OPTIONS requests bypass the authentication checks."""
    original_key = Config.API_KEY
    try:
        Config.API_KEY = "super_secure_key"
        response = client.options("/api/models/progress")
        # OPTIONS response is handled by CORS or returns successfully, but MUST not be 401
        assert response.status_code != 401
    finally:
        Config.API_KEY = original_key
