"""Protect documented defaults; these tests do not establish hosted security."""

import inspect
import ipaddress
from pathlib import Path

from cris_sme.api.local_runner import DEFAULT_HOST, run_server
from cris_sme.engine.public_exposure import PublicExposureSettings
from cris_sme.reporting.narrator import NarratorSettings
from scripts.check_docs import ENTRYPOINTS, validate_docs


def test_runner_default_is_explicit_loopback() -> None:
    assert ipaddress.ip_address(DEFAULT_HOST).is_loopback
    assert inspect.signature(run_server).parameters["host"].default == DEFAULT_HOST


def test_probes_do_not_default_to_private_targets_or_port_scans() -> None:
    settings = PublicExposureSettings()
    assert settings.allow_private_targets is False
    assert settings.scan_common_ports is False
    assert 0 < settings.max_targets <= 10


def test_narrator_requires_opt_in() -> None:
    settings = NarratorSettings()
    assert settings.enabled is False
    assert settings.api_key is None


def test_security_documents_are_checked_by_ci() -> None:
    documents = ("docs/threat-model.md", "docs/deployment-security.md")
    assert set(documents) <= set(ENTRYPOINTS)
    assert validate_docs(Path(__file__).resolve().parents[1], documents) == []
