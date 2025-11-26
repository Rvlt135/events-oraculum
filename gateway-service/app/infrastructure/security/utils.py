import base64
import hashlib
import secrets


def generate_random_string(length_bytes: int) -> str:
    """Генерация криптослучайной строки в hex формате"""
    return secrets.token_hex(length_bytes)


def base64url_encode(data: bytes) -> str:
    """Base64URL кодирование без padding"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def generate_code_verifier() -> str:
    """Генерация PKCE code_verifier (43-128 символов)"""
    random_bytes = secrets.token_bytes(32)
    return base64url_encode(random_bytes)


def generate_code_challenge(code_verifier: str) -> str:
    """Генерация code_challenge из code_verifier"""
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64url_encode(digest)


def generate_oauth_params() -> dict:
    """Генерация всех OAuth параметров"""
    state = generate_random_string(32)
    
    nonce = generate_random_string(16)
    
    code_verifier = generate_code_verifier()
    
    code_challenge = generate_code_challenge(code_verifier)
    
    return {
        'state': state,
        'nonce': nonce,
        'code_verifier': code_verifier,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }