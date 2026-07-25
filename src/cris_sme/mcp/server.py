# MCP server exposing CRIS-SME assessment data as deterministic-ID tools.
from __future__ import annotations

from typing import Any

from cris_sme.mcp import tools

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only without the optional dependency
    FastMCP = None


def build_server() -> "FastMCP":
    """Build the CRIS-SME MCP server with assessment query tools registered."""
    if FastMCP is None:
        raise RuntimeError(
            "The 'mcp' package is required to run the CRIS-SME MCP server. "
            "Install it with: pip install mcp"
        )

    server = FastMCP("cris-sme")

    @server.tool()
    def get_assessment_summary() -> dict[str, Any]:
        """Return headline risk scores and identifiers for the latest assessment."""
        return tools.get_assessment_summary(tools.load_report())

    @server.tool()
    def list_assessment_history() -> list[dict[str, Any]]:
        """List previously archived assessment runs with their snapshot IDs."""
        return tools.list_assessment_history()

    @server.tool()
    def list_findings(
        severity: str | None = None,
        category: str | None = None,
        organization: str | None = None,
        control_id: str | None = None,
        lifecycle_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List prioritized findings, optionally filtered by severity/category/organization/control_id/lifecycle_status."""
        return tools.list_findings(
            tools.load_report(),
            severity=severity,
            category=category,
            organization=organization,
            control_id=control_id,
            lifecycle_status=lifecycle_status,
        )

    @server.tool()
    def get_finding(finding_id: str) -> dict[str, Any] | None:
        """Return the full record for one finding by its deterministic finding_id."""
        return tools.get_finding(tools.load_report(), finding_id)

    @server.tool()
    def list_evidence(
        finding_id: str | None = None,
        control_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List evidence records, optionally filtered by finding_id or control_id."""
        return tools.list_evidence(
            tools.load_report(),
            finding_id=finding_id,
            control_id=control_id,
        )

    @server.tool()
    def list_claims(
        claim_type: str | None = None,
        verification_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List assurance claims, optionally filtered by claim_type or verification_status."""
        return tools.list_claims(
            tools.load_report(),
            claim_type=claim_type,
            verification_status=verification_status,
        )

    @server.tool()
    def list_exceptions() -> list[dict[str, Any]]:
        """List approved finding exceptions from the governance registry."""
        return tools.list_exceptions()

    @server.tool()
    def list_mute_rules() -> list[dict[str, Any]]:
        """List operational mute rules from the governance registry."""
        return tools.list_mute_rules()

    @server.tool()
    def list_action_plan(phase_id: str | None = None) -> list[dict[str, Any]]:
        """List 30-day action plan items, optionally filtered by phase_id."""
        return tools.list_action_plan(tools.load_report(), phase_id=phase_id)

    return server


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
