# Control modules for domain-specific governance and compliance checks.
#
# Imports are intentionally deferred to avoid package-level circular import issues
# when governance metadata modules import `cris_sme.controls.catalog`.


def evaluate_compute_controls(*args, **kwargs):
    from .compute_controls import evaluate_compute_controls as _impl

    return _impl(*args, **kwargs)


def evaluate_data_controls(*args, **kwargs):
    from .data_controls import evaluate_data_controls as _impl

    return _impl(*args, **kwargs)


def evaluate_governance_controls(*args, **kwargs):
    from .governance_controls import evaluate_governance_controls as _impl

    return _impl(*args, **kwargs)


def evaluate_iam_controls(*args, **kwargs):
    from .iam_controls import evaluate_iam_controls as _impl

    return _impl(*args, **kwargs)


def evaluate_monitoring_controls(*args, **kwargs):
    from .monitoring_controls import evaluate_monitoring_controls as _impl

    return _impl(*args, **kwargs)


def evaluate_network_controls(*args, **kwargs):
    from .network_controls import evaluate_network_controls as _impl

    return _impl(*args, **kwargs)

__all__ = [
    "evaluate_compute_controls",
    "evaluate_data_controls",
    "evaluate_governance_controls",
    "evaluate_iam_controls",
    "evaluate_monitoring_controls",
    "evaluate_network_controls",
]
