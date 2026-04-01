## Sample check For Encryption and Decryption ##
# curl --location 'http://3.109.139.129:8000/api/users/decryption_check/?name=suhjn&email=3dinesh3%40gmail.com'
# curl --location 'http://3.109.139.129:8000/api/users/encryption_check/' \
# --header 'Content-Type: application/json' \
# --data '{
#     "payload": "Mf9n5AjdQ8Zyi96G0/o9vJ6ajb5OTTJd2pJogPh23P1aJSUGL8wRqnDDbz+plZrap1+Tsv5AY/eBDGjCfQ7bPQIyveHcvHAdb5FZQ5Ry6P4="
# }'


## ENCRYPT and DECRYPT
import os
from security.crypto import encrypt_json, decrypt_json

KEY = os.getenv("AES_KEY", "0123456789abcdef").encode("utf-8")   # 16 bytes
IV  = os.getenv("AES_IV",  "abcdef0123456789").encode("utf-8")   # 16 bytes


# ── ENCRYPT ────────────────────────────────────────────────────────────────────
data = {
    "mobile": "7771234567",
    "device_id": "device-abc-001"
}
encrypted = encrypt_json(data, KEY, IV)
print("Encrypted:", encrypted)

# ── DECRYPT ────────────────────────────────────────────────────────────────────
decrypted = decrypt_json(encrypted, KEY, IV)
print("Decrypted:", decrypted)

import json
payload_for_request = json.dumps({"payload": encrypted})
print("Request body:", payload_for_request)

## others 
## Example Call
# curl -X POST http://localhost:8000/api/auth/web/login/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "payload": "/+TwoXzRhbkruMbS8YhtEFG59Mgsh1GLNhX9WoWXwA4sV0vmQUJ52phuYw0d0XA8hMizA1pKO/VI+pxLsI48hg=="
#   }'