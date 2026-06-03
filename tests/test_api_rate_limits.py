import pytest
from fastapi.testclient import TestClient
from src.api.server import app, request_history
from src.core.config import Config
import time

client = TestClient(app)

def test_api_rate_limiting_enhance():
    # Save original API key and disable it for the test
    original_key = Config.API_KEY
    Config.API_KEY = None
    
    try:
        # Reset request history for the test to ensure clean state
        request_history.clear()
        
        # The limit for /api/ai/enhance is 10 requests per minute.
        # Send 10 successful requests (they will return 400 since payload is empty/invalid, 
        # but the rate limiting middleware runs before route logic and counts them).
        for i in range(10):
            response = client.post("/api/ai/enhance", json={})
            # Rate limiter passed, so it reached route validation and returned 400 Bad Request
            assert response.status_code == 400
            
        # The 11th request should be blocked by the rate limiter and return 429 Too Many Requests
        response = client.post("/api/ai/enhance", json={})
        assert response.status_code == 429
        assert response.json()["detail"] == "Too many requests. Please try again later."
    finally:
        Config.API_KEY = original_key
