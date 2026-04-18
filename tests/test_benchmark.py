# Unit tests for CRIS-SME benchmark dataset scaffolding.
from cris_sme.engine.benchmark import (
    BenchmarkObservation,
    build_benchmark_comparison,
    build_benchmark_observation,
)


def make_report() -> dict[str, object]:
    """Create a compact report shape for benchmark tests."""
    return {
        "generated_at": "2026-04-18T00:00:00Z",
        "collector_mode": "azure",
        "overall_risk_score": 33.2,
        "category_scores": {"IAM": 14.64, "Network": 47.42},
        "organizations": [
            {
                "organization_name": "Azure SME Tenant",
                "provider": "azure",
                "sector": "SME",
                "collection_details": {"profile_source": "azure_live"},
            }
        ],
    }


def test_build_benchmark_observation_normalizes_report_metadata() -> None:
    observation = build_benchmark_observation(make_report())

    assert observation.provider == "azure"
    assert observation.collector_mode == "azure"
    assert observation.organization_count == 1


def test_build_benchmark_comparison_reports_insufficient_dataset_when_peer_count_is_small() -> None:
    report = make_report()
    dataset = [
        BenchmarkObservation(
            observation_id="azure-a",
            generated_at="2026-04-16T00:00:00Z",
            organization_label="Azure A",
            provider="azure",
            sector="SME",
            collector_mode="azure",
            sample_source="live",
            organization_count=1,
            overall_risk_score=30.0,
            category_scores={"IAM": 10.0},
        )
    ]

    comparison = build_benchmark_comparison(report, dataset)

    assert comparison["status"] == "insufficient_dataset"
    assert comparison["peer_count"] == 1
