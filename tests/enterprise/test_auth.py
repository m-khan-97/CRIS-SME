import json
import time

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from cris_sme.enterprise.auth import AccessTokenVerifier


def test_signed_access_token(verifier, token):
    assert verifier.verify(token()).subject == "owner"


@pytest.mark.parametrize("claim,value", [("iss", "https://wrong.example"), ("aud", "other-api"),
    ("aud", ["cris-api", "other-api"]), ("exp", 1), ("iat", 9999999999), ("sub", ""),
    ("scope", "openid"), ("scope", ["cris.api"]), ("exp", str(int(time.time()) + 300)), ("iat", True)])
def test_wrong_claims_fail_closed(verifier, token, claim, value):
    with pytest.raises(Exception):
        verifier.verify(token(claims={claim: value}))


@pytest.mark.parametrize("name", ["exp", "iat", "sub", "iss", "aud"])
def test_required_claims(verifier, token, name):
    with pytest.raises(Exception):
        verifier.verify(token(remove=[name]))


def test_key_confusion_and_bad_signature(verifier, token):
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for encoded in (token(key=wrong_key), token(headers={"kid": "unknown"}),
                    jwt.encode({"sub": "owner"}, "x" * 32, algorithm="HS256", headers={"kid": "fixture-key"}), "x" * 16385):
        with pytest.raises(Exception):
            verifier.verify(encoded)


def test_id_token_without_api_scope_is_rejected(verifier, token):
    with pytest.raises(ValueError):
        verifier.verify(token(remove=["scope"]))


def test_entra_scp_api_scope_is_supported(verifier, token):
    assert verifier.verify(token(claims={"scp": "cris.api"}, remove=["scope"])).subject == "owner"


def test_long_lived_token_rejected(verifier, token):
    with pytest.raises(ValueError):
        verifier.verify(token(claims={"exp": int(time.time()) + 7200}))


@pytest.mark.parametrize("url", ["http://identity.example", "https://user:pass@identity.example", "https://identity.example/#frag"])
def test_issuer_configuration_validation(url):
    with pytest.raises(ValueError):
        AccessTokenVerifier(url, "api", "https://identity.example/keys")


def test_jwks_fetch_is_bounded_and_cached(monkeypatch, signing, token):
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_bytes(self): yield json.dumps(signing[1]).encode()
    def stream(*args, **kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        calls.append(1)
        return Response()
    monkeypatch.setattr("cris_sme.enterprise.auth.httpx.stream", stream)
    verifier = AccessTokenVerifier("https://identity.example", "cris-api", "https://identity.example/keys")
    verifier.verify(token())
    verifier.verify(token())
    assert len(calls) == 1
    class Oversize(Response):
        def iter_bytes(self): yield b"x" * 262145
    monkeypatch.setattr("cris_sme.enterprise.auth.httpx.stream", lambda *args, **kwargs: Oversize())
    with pytest.raises(ValueError):
        AccessTokenVerifier("https://identity.example", "cris-api", "https://identity.example/keys").verify(token())


def test_jwks_outage_has_retry_backoff(monkeypatch, token):
    import httpx
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(1)
        raise httpx.ConnectError("fixture outage")
    monkeypatch.setattr("cris_sme.enterprise.auth.httpx.stream", unavailable)
    verifier = AccessTokenVerifier("https://identity.example", "cris-api", "https://identity.example/keys")
    for _ in range(2):
        with pytest.raises(Exception):
            verifier.verify(token())
    assert len(calls) == 1
