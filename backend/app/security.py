import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    expected_api_key = os.environ.get("API_KEY")
    if not expected_api_key:
        # If no API key is configured on the backend, allow anonymous access
        return api_key
        
    if api_key == expected_api_key:
        return api_key
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key"
    )
