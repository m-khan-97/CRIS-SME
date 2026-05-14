# Public endpoint exposure assessment for explicitly authorised CRIS-SME targets.
from __future__ import annotations

import ipaddress
import json
import shutil
import socket
import ssl
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib import error, parse, request


Resolver = Callable[[str], list[str]]
HttpProbe = Callable[[str, float], dict[str, Any]]
TlsProbe = Callable[[str, int, float], dict[str, Any]]
DnsRecordLookup = Callable[[str, str, float], dict[str, Any]]

SECURITY_HEADERS = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-frame-options": "Clickjacking protection",
    "x-content-type-options": "MIME sniffing protection",
}


@dataclass(frozen=True)
class PublicExposureSettings:
    """Runtime settings for public exposure assessment."""

    timeout_seconds: float = 5.0
    allow_private_targets: bool = False
    max_targets: int = 10


@dataclass
class PublicExposureScanner:
    """Assess public DNS, HTTP, and TLS exposure for authorised targets."""

    settings: PublicExposureSettings = field(default_factory=PublicExposureSettings)
    resolver: Resolver | None = None
    http_probe: HttpProbe | None = None
    tls_probe: TlsProbe | None = None
    dns_record_lookup: DnsRecordLookup | None = None

    def assess(self, targets: list[str], *, authorization_confirmed: bool) -> dict[str, Any]:
        """Return a deterministic public exposure report for the supplied targets."""
        if not authorization_confirmed:
            raise ValueError("authorization_confirmed must be true before public exposure assessment can run.")
        normalized = normalize_targets(targets, max_targets=self.settings.max_targets)
        if not normalized:
            raise ValueError("At least one target is required.")

        assessed = [self._assess_target(target) for target in normalized]
        findings = [finding for item in assessed for finding in item["findings"]]
        summary = {
            "target_count": len(assessed),
            "resolved_target_count": sum(1 for item in assessed if item["dns"]["addresses"]),
            "https_available_count": sum(1 for item in assessed if item["https"].get("reachable")),
            "finding_count": len(findings),
            "high_finding_count": sum(1 for item in findings if item["severity"] == "high"),
            "medium_finding_count": sum(1 for item in findings if item["severity"] == "medium"),
            "low_finding_count": sum(1 for item in findings if item["severity"] == "low"),
        }
        return {
            "assessment_type": "public_exposure",
            "generated_at": _utc_now(),
            "authorization_model": "explicit_user_confirmed_target_authorization",
            "scope_note": (
                "This assessment uses DNS, HTTPS, HTTP, and TLS metadata for user-authorised "
                "targets only. It is not a vulnerability exploit, authentication bypass, or "
                "internet-wide scan."
            ),
            "summary": summary,
            "targets": assessed,
            "findings": findings,
        }

    def _assess_target(self, target: dict[str, str]) -> dict[str, Any]:
        host = target["host"]
        dns = self._resolve(host)
        private_addresses = [address for address in dns["addresses"] if is_private_address(address)]
        findings: list[dict[str, Any]] = []
        if private_addresses and not self.settings.allow_private_targets:
            findings.append(
                build_finding(
                    "PE-000",
                    "Private or local target excluded",
                    "low",
                    host,
                    "The target resolves to private, loopback, link-local, or reserved address space.",
                    "Use only owned public targets, or enable private-target mode for internal lab testing.",
                    evidence={"addresses": private_addresses},
                )
            )
            return {
                **target,
                "dns": dns,
                "https": {"reachable": False, "skipped": True},
                "http": {"reachable": False, "skipped": True},
                "tls": {"available": False, "skipped": True},
                "findings": findings,
            }

        https_url = f"https://{host}"
        http_url = f"http://{host}"
        https = self._http(https_url)
        http = self._http(http_url)
        tls = self._tls(host, 443)
        dns_records = self._dns_records(host)
        security_txt = self._http(f"https://{host}/.well-known/security.txt")

        if not dns["addresses"]:
            findings.append(
                build_finding(
                    "PE-001",
                    "Target did not resolve",
                    "medium",
                    host,
                    "No DNS A or AAAA records were resolved from this environment.",
                    "Confirm DNS publication and whether this target should be reachable publicly.",
                    evidence={"dns_error": dns.get("error", "")},
                )
            )
        if http.get("reachable") and not https.get("reachable"):
            findings.append(
                build_finding(
                    "PE-002",
                    "HTTP reachable but HTTPS unavailable",
                    "high",
                    host,
                    "The target responded over HTTP while HTTPS did not return a successful response.",
                    "Enable HTTPS and redirect HTTP traffic to HTTPS for public-facing services.",
                    evidence={"http": http, "https": https},
                )
            )
        if https.get("reachable"):
            missing_headers = [
                label
                for header, label in SECURITY_HEADERS.items()
                if header not in https.get("headers", {})
            ]
            if missing_headers:
                findings.append(
                    build_finding(
                        "PE-003",
                        "Security headers missing on HTTPS response",
                        "medium",
                        host,
                        "The HTTPS response is missing one or more common browser security headers.",
                        "Review HSTS, Content-Security-Policy, X-Frame-Options, and X-Content-Type-Options.",
                        evidence={"missing_headers": missing_headers, "status": https.get("status")},
                    )
                )
        if tls.get("available") and tls.get("days_until_expiry") is not None and tls["days_until_expiry"] < 30:
            findings.append(
                build_finding(
                    "PE-004",
                    "TLS certificate expires within 30 days",
                    "medium",
                    host,
                    "The public TLS certificate is close to expiry.",
                    "Renew the certificate or confirm automated certificate renewal is operating.",
                    evidence={"not_after": tls.get("not_after"), "days_until_expiry": tls.get("days_until_expiry")},
                )
            )
        if http.get("reachable") and not _redirects_to_https(http):
            findings.append(
                build_finding(
                    "PE-005",
                    "HTTP does not redirect to HTTPS",
                    "medium",
                    host,
                    "The HTTP endpoint did not present a clear redirect to HTTPS.",
                    "Redirect plaintext HTTP requests to HTTPS where the service is intended to be web-accessible.",
                    evidence={"status": http.get("status"), "location": http.get("location", "")},
                )
            )
        if not dns_records["dmarc"]["records"]:
            findings.append(
                build_finding(
                    "PE-006",
                    "DMARC record not observed",
                    "medium",
                    host,
                    "No DMARC TXT record was observed at _dmarc for the authorised target.",
                    "Publish a DMARC policy and align it with the organisation's email sending posture.",
                    evidence=dns_records["dmarc"],
                )
            )
        if not dns_records["spf"]["records"]:
            findings.append(
                build_finding(
                    "PE-007",
                    "SPF record not observed",
                    "low",
                    host,
                    "No SPF TXT record was observed for the authorised target.",
                    "Publish SPF for domains that send mail, or document why the domain is non-sending.",
                    evidence=dns_records["spf"],
                )
            )
        if not dns_records["caa"]["records"]:
            findings.append(
                build_finding(
                    "PE-008",
                    "CAA record not observed",
                    "low",
                    host,
                    "No CAA record was observed for the authorised target.",
                    "Consider CAA records to restrict which certificate authorities may issue certificates.",
                    evidence=dns_records["caa"],
                )
            )
        if not security_txt.get("reachable") or int(security_txt.get("status") or 0) >= 400:
            findings.append(
                build_finding(
                    "PE-009",
                    "security.txt not observed",
                    "low",
                    host,
                    "No reachable security.txt file was observed at the standard well-known path.",
                    "Publish /.well-known/security.txt for public vulnerability reporting contacts where appropriate.",
                    evidence=security_txt,
                )
            )

        return {
            **target,
            "dns": dns,
            "dns_records": dns_records,
            "https": https,
            "http": http,
            "tls": tls,
            "security_txt": security_txt,
            "findings": findings,
        }

    def _resolve(self, host: str) -> dict[str, Any]:
        resolver = self.resolver or resolve_host
        try:
            addresses = sorted(set(resolver(host)))
            return {"addresses": addresses, "error": ""}
        except Exception as exc:
            return {"addresses": [], "error": str(exc)}

    def _http(self, url: str) -> dict[str, Any]:
        probe = self.http_probe or probe_http
        try:
            return probe(url, self.settings.timeout_seconds)
        except Exception as exc:
            return {"url": url, "reachable": False, "error": str(exc), "headers": {}}

    def _tls(self, host: str, port: int) -> dict[str, Any]:
        probe = self.tls_probe or probe_tls
        try:
            return probe(host, port, self.settings.timeout_seconds)
        except Exception as exc:
            return {"host": host, "port": port, "available": False, "error": str(exc)}

    def _dns_records(self, host: str) -> dict[str, Any]:
        lookup = self.dns_record_lookup or lookup_dns_records
        return {
            "spf": _lookup_named_record(lookup, host, "TXT", self.settings.timeout_seconds, predicate="v=spf1"),
            "dmarc": _lookup_named_record(lookup, f"_dmarc.{host}", "TXT", self.settings.timeout_seconds, predicate="v=dmarc1"),
            "mta_sts": _lookup_named_record(lookup, f"_mta-sts.{host}", "TXT", self.settings.timeout_seconds, predicate="v=stsv1"),
            "tls_rpt": _lookup_named_record(lookup, f"_smtp._tls.{host}", "TXT", self.settings.timeout_seconds, predicate="v=tlsrptv1"),
            "caa": _lookup_named_record(lookup, host, "CAA", self.settings.timeout_seconds),
            "dkim": {
                "status": "selector_required",
                "records": [],
                "note": "DKIM discovery requires one or more selector names and is not guessed by the safe public exposure mode.",
            },
        }


def normalize_targets(targets: list[str], *, max_targets: int = 10) -> list[dict[str, str]]:
    """Normalize URL/domain/IP target input into host records."""
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in targets:
        value = str(raw or "").strip()
        if not value:
            continue
        parsed = parse.urlparse(value if "://" in value else f"https://{value}")
        host = (parsed.hostname or "").strip().lower().rstrip(".")
        if not host:
            continue
        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError(f"Invalid target host '{host}': {exc}") from exc
        if ascii_host in seen:
            continue
        seen.add(ascii_host)
        normalized.append(
            {
                "input": value,
                "host": ascii_host,
                "scheme_hint": parsed.scheme or "https",
            }
        )
        if len(normalized) >= max_targets:
            break
    return normalized


def resolve_host(host: str) -> list[str]:
    """Resolve A/AAAA records through the local resolver."""
    records = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return [record[4][0] for record in records]


def probe_http(url: str, timeout_seconds: float) -> dict[str, Any]:
    """Probe an HTTP(S) endpoint with a lightweight GET request."""
    req = request.Request(url, method="GET", headers={"User-Agent": "CRIS-SME-PublicExposure/0.1"})
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310 - explicit user-authorised URL probe
            headers = {key.lower(): value for key, value in response.headers.items()}
            return {
                "url": url,
                "reachable": True,
                "status": int(response.status),
                "final_url": response.geturl(),
                "location": headers.get("location", ""),
                "headers": headers,
            }
    except error.HTTPError as exc:
        headers = {key.lower(): value for key, value in exc.headers.items()}
        return {
            "url": url,
            "reachable": True,
            "status": int(exc.code),
            "final_url": url,
            "location": headers.get("location", ""),
            "headers": headers,
            "http_error": str(exc),
        }


def probe_tls(host: str, port: int, timeout_seconds: float) -> dict[str, Any]:
    """Collect public TLS certificate metadata without sending application payloads."""
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls_sock:
            cert = tls_sock.getpeercert()
            not_after = str(cert.get("notAfter", ""))
            days_until_expiry = None
            if not_after:
                expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
                days_until_expiry = (expires - datetime.now(UTC)).days
            return {
                "host": host,
                "port": port,
                "available": True,
                "protocol": tls_sock.version(),
                "cipher": tls_sock.cipher()[0] if tls_sock.cipher() else "",
                "not_after": not_after,
                "days_until_expiry": days_until_expiry,
                "subject": _name_tuple_to_dict(cert.get("subject", [])),
                "issuer": _name_tuple_to_dict(cert.get("issuer", [])),
            }


def lookup_dns_records(name: str, record_type: str, timeout_seconds: float) -> dict[str, Any]:
    """Lookup passive DNS records using local `dig` when available."""
    if not shutil.which("dig"):
        return {"name": name, "type": record_type, "records": [], "error": "dig command not available"}
    try:
        completed = subprocess.run(
            ["dig", "+short", record_type, name],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:
        return {"name": name, "type": record_type, "records": [], "error": str(exc)}
    records = [line.strip().strip('"') for line in completed.stdout.splitlines() if line.strip()]
    return {
        "name": name,
        "type": record_type,
        "records": records,
        "error": completed.stderr.strip(),
        "returncode": completed.returncode,
    }


def write_public_exposure_outputs(report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    """Persist public exposure JSON and Markdown artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "cris_sme_public_exposure.json"
    md_path = output_dir / "cris_sme_public_exposure.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(build_public_exposure_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def build_public_exposure_markdown(report: dict[str, Any]) -> str:
    """Build a compact Markdown report for public exposure results."""
    summary = report.get("summary", {})
    lines = [
        "# CRIS-SME Public Exposure Assessment",
        "",
        f"Generated: `{report.get('generated_at', '')}`",
        "",
        "## Scope Boundary",
        "",
        str(report.get("scope_note", "")),
        "",
        "## Summary",
        "",
        f"- Targets: `{summary.get('target_count', 0)}`",
        f"- Resolved targets: `{summary.get('resolved_target_count', 0)}`",
        f"- HTTPS available: `{summary.get('https_available_count', 0)}`",
        f"- Findings: `{summary.get('finding_count', 0)}`",
        "",
        "## Findings",
        "",
    ]
    findings = report.get("findings", [])
    if not findings:
        lines.append("No public exposure findings were generated for the authorised targets.")
    for finding in findings:
        lines.extend(
            [
                f"### {finding.get('id', '')}: {finding.get('title', '')}",
                "",
                f"- Target: `{finding.get('target', '')}`",
                f"- Severity: `{finding.get('severity', '')}`",
                f"- Evidence: {finding.get('evidence_summary', '')}",
                f"- Recommendation: {finding.get('recommendation', '')}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def build_finding(
    finding_id: str,
    title: str,
    severity: str,
    target: str,
    evidence_summary: str,
    recommendation: str,
    *,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Build a public exposure finding."""
    return {
        "id": finding_id,
        "title": title,
        "severity": severity,
        "target": target,
        "evidence_summary": evidence_summary,
        "recommendation": recommendation,
        "evidence": evidence,
    }


def is_private_address(address: str) -> bool:
    """Return whether an address is outside normal public internet scope."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _lookup_named_record(
    lookup: DnsRecordLookup,
    name: str,
    record_type: str,
    timeout_seconds: float,
    *,
    predicate: str | None = None,
) -> dict[str, Any]:
    result = lookup(name, record_type, timeout_seconds)
    records = result.get("records", [])
    if not isinstance(records, list):
        records = []
    if predicate:
        records = [
            str(record)
            for record in records
            if str(record).strip().lower().startswith(predicate.lower())
        ]
    return {
        **result,
        "name": name,
        "type": record_type,
        "records": records,
    }


def _redirects_to_https(http_result: dict[str, Any]) -> bool:
    final_url = str(http_result.get("final_url", ""))
    location = str(http_result.get("location", ""))
    return final_url.startswith("https://") or location.startswith("https://")


def _name_tuple_to_dict(value: object) -> dict[str, str]:
    result: dict[str, str] = {}
    if not isinstance(value, tuple):
        return result
    for group in value:
        if not isinstance(group, tuple):
            continue
        for item in group:
            if isinstance(item, tuple) and len(item) == 2:
                result[str(item[0])] = str(item[1])
    return result


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
