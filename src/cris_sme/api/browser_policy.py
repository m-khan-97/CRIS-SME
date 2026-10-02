"""Browser request restrictions for the single-operator local API, not authentication."""

from __future__ import annotations

from email.message import Message
from urllib.parse import urlsplit


DEFAULT_ALLOWED_HOSTS = ("127.0.0.1", "localhost", "[::1]")
DEFAULT_ALLOWED_ORIGINS = tuple(
    f"http://{host}:{port}"
    for host in DEFAULT_ALLOWED_HOSTS
    for port in (5173, 8080, 8787)
)


def _host(value: str) -> str:
    if not value or not value.isascii() or any(char.isspace() for char in value):
        raise ValueError("invalid host")
    if any(char in value for char in "/\\@?#%*") or value.endswith(":"):
        raise ValueError("invalid host")
    parsed = urlsplit(f"http://{value}")
    if not parsed.hostname or (parsed.port is not None and not 1 <= parsed.port <= 65535):
        raise ValueError("invalid host")
    authority = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    if parsed.port is not None:
        authority += f":{parsed.port}"
    if value.lower() != authority:
        raise ValueError("invalid host")
    return parsed.hostname


class BrowserRequestPolicy:
    def __init__(
        self, *, allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
        allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS,
    ) -> None:
        hosts = set()
        for host in allowed_hosts:
            name = _host(host)
            if urlsplit(f"http://{host}").port is not None:
                raise ValueError("allowed hosts must not contain ports")
            hosts.add(name)
        for origin in allowed_origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or parsed.path or parsed.query
                    or parsed.fragment or origin != f"{parsed.scheme}://{parsed.netloc}"):
                raise ValueError("allowed origins must be explicit HTTP(S) origins without a path")
            _host(parsed.netloc)
        self.allowed_hosts = frozenset(hosts)
        self.allowed_origins = frozenset(allowed_origins)

    def rejection(self, headers: Message) -> tuple[int, str] | None:
        hosts = headers.get_all("Host", [])
        if len(hosts) != 1:
            return 400, "exactly one Host header is required"
        try:
            name = _host(hosts[0])
        except ValueError:
            return 400, "invalid Host header"
        if name not in self.allowed_hosts:
            return 403, "Host is not allowed"
        origins = headers.get_all("Origin", [])
        if len(origins) > 1:
            return 400, "at most one Origin header is allowed"
        if origins and origins[0] not in self.allowed_origins:
            return 403, "Origin is not allowed"
        if not origins and headers.get("Sec-Fetch-Site") == "cross-site":
            return 403, "cross-site browser request is not allowed"
        return None
