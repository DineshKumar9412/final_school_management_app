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


# # api/upload_image.py
# from fastapi import APIRouter, UploadFile, File, Depends
# from response.result import Result
# from security.valid_session import valid_session
# from datetime import datetime
# import os

# upload_router = APIRouter(
#     tags=["UPLOAD"],
#     dependencies=[Depends(valid_session)],
# )

# UPLOAD_DIR  = "/var/www/html/images/"
# MEDIA_URL   = "/images/"
# ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}

# os.makedirs(UPLOAD_DIR, exist_ok=True)


# # ══════════════════════════════════════════════
# # UPLOAD
# # ══════════════════════════════════════════════

# @upload_router.post(
#     "/upload/image",
#     summary="Upload an image file",
#     responses={
#         201: {"content": {"application/json": {"example": {"code": 201, "message": "Image uploaded successfully.", "result": {"file_name": "20240101120000_photo.png", "url": "/images/20240101120000_photo.png", "size_kb": 128.5}}}}},
#         400: {"content": {"application/json": {"example": {"code": 400, "message": "Only .png, .jpg, .jpeg, .webp files are allowed.", "result": {}}}}},
#     },
# )
# async def upload_image(file: UploadFile = File(...)):
#     if not file.filename:
#         return Result(code=400, message="File name is missing.", extra={}).http_response()

#     ext = os.path.splitext(file.filename)[-1].lower()
#     if ext not in ALLOWED_EXT:
#         return Result(
#             code=400,
#             message=f"Only {', '.join(ALLOWED_EXT)} files are allowed.",
#             extra={},
#         ).http_response()

#     timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#     file_name = f"{timestamp}_{file.filename}"
#     file_path = os.path.join(UPLOAD_DIR, file_name)

#     content = await file.read()
#     with open(file_path, "wb") as buffer:
#         buffer.write(content)

#     size_kb = round(len(content) / 1024, 2)

#     return Result(code=201, message="Image uploaded successfully.", extra={
#         "file_name": file_name,
#         "file_path": file_path,
#         "url":       f"{MEDIA_URL}{file_name}",
#         "size_kb":   size_kb,
#     }).http_response()


# # ══════════════════════════════════════════════
# # GET IMAGE BY FILE NAME
# # ══════════════════════════════════════════════

# @upload_router.get(
#     "/upload/image/{file_name}",
#     summary="Get image info by file name",
#     responses={
#         200: {"content": {"application/json": {"example": {"code": 200, "message": "Image found.", "result": {"file_name": "20240101120000_photo.png", "url": "/images/20240101120000_photo.png", "size_kb": 128.5, "uploaded_at": "20240101120000"}}}}},
#         404: {"content": {"application/json": {"example": {"code": 404, "message": "Image not found.", "result": {}}}}},
#     },
# )
# async def get_image(file_name: str):
#     file_path = os.path.join(UPLOAD_DIR, file_name)

#     if not os.path.isfile(file_path):
#         return Result(code=404, message="Image not found.", extra={}).http_response()

#     ext = os.path.splitext(file_name)[-1].lower()
#     if ext not in ALLOWED_EXT:
#         return Result(code=400, message="Not a valid image file.", extra={}).http_response()

#     stat        = os.stat(file_path)
#     size_kb     = round(stat.st_size / 1024, 2)
#     uploaded_at = file_name[:14] if len(file_name) >= 14 else ""

#     return Result(code=200, message="Image found.", extra={
#         "file_name":   file_name,
#         "file_path":   file_path,
#         "url":         f"{MEDIA_URL}{file_name}",
#         "size_kb":     size_kb,
#         "uploaded_at": uploaded_at,
#     }).http_response()


# # ══════════════════════════════════════════════
# # LIST ALL IMAGES
# # ══════════════════════════════════════════════

# @upload_router.get(
#     "/upload/images",
#     summary="List all uploaded images",
#     responses={
#         200: {"content": {"application/json": {"example": {"code": 200, "message": "Images fetched successfully.", "result": {"total": 2, "data": [{"file_name": "20240101120000_photo.png", "url": "/images/20240101120000_photo.png", "size_kb": 128.5, "uploaded_at": "20240101120000"}]}}}}},
#     },
# )
# async def list_images():
#     if not os.path.isdir(UPLOAD_DIR):
#         return Result(code=200, message="Images fetched successfully.", extra={"total": 0, "data": []}).http_response()

#     files = []
#     for file_name in sorted(os.listdir(UPLOAD_DIR), reverse=True):
#         ext = os.path.splitext(file_name)[-1].lower()
#         if ext not in ALLOWED_EXT:
#             continue

#         file_path   = os.path.join(UPLOAD_DIR, file_name)
#         stat        = os.stat(file_path)
#         size_kb     = round(stat.st_size / 1024, 2)
#         uploaded_at = file_name[:14] if len(file_name) >= 14 else ""

#         files.append({
#             "file_name":   file_name,
#             "url":         f"{MEDIA_URL}{file_name}",
#             "size_kb":     size_kb,
#             "uploaded_at": uploaded_at,
#         })

#     return Result(code=200, message="Images fetched successfully.", extra={
#         "total": len(files),
#         "data":  files,
#     }).http_response()
