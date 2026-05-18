from cris_sme.reporting.iomt_evidence_pack import (
    build_iomt_evidence_pack,
    build_iomt_evidence_pack_markdown,
)


def test_iomt_evidence_pack_extracts_findings_and_metadata() -> None:
    report = {
        "generated_at": "2026-05-19T00:00:00Z",
        "overall_risk_score": 27.2,
        "category_scores": {"Healthcare IoT": 26.64},
        "organizations": [
            {
                "collection_details": {
                    "iot_collection_mode": "azure_iot_hub_cli_inventory",
                    "evidence_counts": {
                        "iot_hub_count": 1,
                        "iot_public_network_hub_count": 1,
                    },
                }
            }
        ],
        "prioritized_risks": [
            {
                "finding_id": "fdg_iot_public",
                "control_id": "IOT-005",
                "category": "Healthcare IoT",
                "title": "IoT Hub public network access is not sufficiently constrained",
                "severity": "HIGH",
                "priority": "Fix Next",
                "score": 47.61,
                "evidence": ["1 IoT Hub allows public network access"],
                "evidence_quality": {"sufficiency": "unsupported"},
            },
            {
                "finding_id": "fdg_iam",
                "control_id": "IAM-005",
                "category": "IAM",
                "title": "Identity observability is partial",
                "score": 4.57,
            },
        ],
    }
    manifest = {
        "status": "completed",
        "run_id": "20260519",
        "resource_group": "cris-lab-iomt",
        "location": "uaenorth",
        "scenario": {
            "id": "iomt-clean-baseline",
            "title": "IoMT clean baseline",
            "dataset_source_type": "owned_lab",
            "dataset_use": "research_validation",
            "authorization_basis": "owned subscription",
        },
    }

    pack = build_iomt_evidence_pack(report, lab_manifest=manifest)
    markdown = build_iomt_evidence_pack_markdown(pack)

    assert pack["iomt_findings_total"] == 1
    assert pack["iomt_category_score"] == 26.64
    assert pack["iomt_controls_triggered"] == ["IOT-005"]
    assert pack["iot_collection_metadata"]["iot_collection_mode"] == (
        "azure_iot_hub_cli_inventory"
    )
    assert pack["iot_collection_metadata"]["iot_hub_count"] == 1
    assert pack["lab_context"]["scenario_id"] == "iomt-clean-baseline"
    assert "Certification Boundary" in markdown
    assert "IOT-005" in markdown
