# middleware/decryption.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from security.helper import ENCRYPTED_PATHS
import json
from security.crypto import decrypt_json
import base64
import os

# Base64-encoded AES-256 key (32 bytes) and IV (16 bytes)
key_b64 = os.getenv("KEY", "")
iv_b64  = os.getenv("IV", "")
key = base64.b64decode(key_b64)
iv  = base64.b64decode(iv_b64)

class DecryptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        if request.url.path not in ENCRYPTED_PATHS:
            return await call_next(request)

        if request.url.path == "/metrics":
            return await call_next(request)

        body = await request.body()

        encrypted_payload = json.loads(body).get("payload")
        decrypted_dict = decrypt_json(encrypted_payload, key, iv)
        decrypted_body = json.dumps(decrypted_dict).encode("utf-8")

        async def receive():
            return {
                "type": "http.request",
                "body": decrypted_body,
                "more_body": False,
            }

        request._receive = receive
        request._body = decrypted_body

        return await call_next(request)
