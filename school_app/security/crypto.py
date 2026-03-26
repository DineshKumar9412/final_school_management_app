# security/crypto.py
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import json

def encrypt_json(data: dict, key: bytes, iv: bytes) -> str:
    """
    Encrypts a Python dictionary and returns Base64 string.
    """
    plaintext = json.dumps(data).encode('utf-8')
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode('utf-8')

def decrypt_json(ciphertext_b64: str, key: bytes, iv: bytes) -> dict:
    """
    Decrypts Base64 AES string and returns Python dictionary.
    """
    ciphertext = base64.b64decode(ciphertext_b64)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()
    plaintext_str = plaintext_bytes.decode('utf-8')
    return json.loads(plaintext_str)
