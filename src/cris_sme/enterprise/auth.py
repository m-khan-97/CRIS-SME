"""Validate access tokens against explicitly configured issuer and signing keys."""
from dataclasses import dataclass
import threading
import time
from urllib.parse import urlsplit

import httpx
import jwt


@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: str


class AccessTokenVerifier:
    def __init__(self, issuer: str, audience: str, jwks_url: str,
                 required_scope: str = "cris.api", *, jwks: dict | None = None):
        for url in (issuer, jwks_url):
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError("OIDC issuer and JWKS URL must be operator-configured HTTPS URLs")
        if not audience or not required_scope:
            raise ValueError("Audience and API scope are required")
        self.issuer, self.audience, self.url, self.scope = issuer, audience, jwks_url, required_scope
        self._jwks, self._loaded = jwks, time.monotonic() if jwks is not None else 0.0
        self._static = jwks is not None
        self._retry_after = 0.0
        self._lock = threading.Lock()

    def _keys(self) -> dict:
        with self._lock:
            if self._jwks is None or (not self._static and time.monotonic() - self._loaded > 60):
                if time.monotonic() < self._retry_after:
                    raise ValueError("Signing keys temporarily unavailable")
                self._retry_after = time.monotonic() + 5
                with httpx.stream("GET", self.url, timeout=5, follow_redirects=False, trust_env=False) as response:
                    response.raise_for_status()
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        if len(data) + len(chunk) > 262144:
                            raise ValueError("Oversized JWKS")
                        data.extend(chunk)
                import json
                keys = json.loads(data)
                if not isinstance(keys, dict) or not isinstance(keys.get("keys"), list) or len(keys["keys"]) > 32:
                    raise ValueError("Invalid JWKS")
                self._jwks, self._loaded = keys, time.monotonic()
            return self._jwks

    def verify(self, token: str) -> Principal:
        if not token or len(token) > 16384:
            raise ValueError("Invalid access token")
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if header.get("alg") != "RS256" or not isinstance(kid, str) or not 1 <= len(kid) <= 128:
            raise ValueError("Unsupported access token")
        matches = [key for key in self._keys().get("keys", [])
                   if key.get("kid") == kid and key.get("kty") == "RSA"
                   and key.get("use", "sig") == "sig" and key.get("alg", "RS256") == "RS256"]
        if len(matches) != 1:
            raise ValueError("Unknown signing key")
        key = jwt.PyJWK.from_dict(matches[0], algorithm="RS256").key
        if key.key_size < 2048 or "verify" not in matches[0].get("key_ops", ["verify"]):
            raise ValueError("Unsupported signing key")
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=self.issuer, audience=self.audience,
                            options={"require": ["exp", "iat", "iss", "sub", "aud"], "strict_aud": True})
        if any(type(claims[name]) not in (int, float) for name in ("exp", "iat")):
            raise ValueError("Invalid token timestamps")
        if claims["exp"] - claims["iat"] > 3600 or claims["exp"] <= claims["iat"]:
            raise ValueError("Unsupported token lifetime")
        scope = claims.get("scope", claims.get("scp", ""))
        if not isinstance(scope, str) or self.scope not in scope.split():
            raise ValueError("API access scope required")
        subject = claims["sub"]
        if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
            raise ValueError("Invalid subject")
        return Principal(self.issuer, subject)
