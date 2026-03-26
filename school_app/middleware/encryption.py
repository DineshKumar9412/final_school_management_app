# middleware/encryption.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request
from security.helper import DECRYPTED_PATHS
import base64
import json
from security.crypto import encrypt_json
import os

# Base64-encoded AES-256 key (32 bytes) and IV (16 bytes)
key_b64 = os.getenv("KEY", "")
iv_b64  = os.getenv("IV", "")
key = base64.b64decode(key_b64)
iv  = base64.b64decode(iv_b64)

class EncryptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        response = await call_next(request)

        # Only encrypt specific paths
        if request.url.path not in DECRYPTED_PATHS:
            return response

        if request.url.path == "/metrics":
            return await call_next(request)

        # Read the original response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Parse JSON
        data = json.loads(body.decode('utf-8'))

        # Encrypt the "result" field only
        if "result" in data:
            encrypted_value = encrypt_json(data["result"], key, iv)
            data["result"] = encrypted_value

        # Return new encrypted response
        return Response(
            content=json.dumps(data),
            status_code=response.status_code,
            media_type="application/json"
        )
