# Remediation Simulator

The CRIS-SME Remediation Simulator is a deterministic what-if layer for planning risk reduction.

It answers:

- what happens to the overall risk score if selected findings are fixed?
- which low-cost actions reduce the most modeled risk?
- how much risk reduction is expected from common SME budget bands?
- which domains improve under a remediation scenario?

## Method

The simulator does not predict incidents.

It uses the existing CRIS-SME scoring model:

1. start from the current scored findings
2. select a remediation scenario
3. treat selected findings as remediated
4. remove them from the active non-compliant set
5. recompute category scores from remaining findings
6. recompute overall score using existing category weights
7. report the before/after delta

This keeps the simulator deterministic, explainable, and consistent with the rest of the engine.

## Default Scenarios

CRIS-SME currently generates four scenarios:

- `fix_free_this_week`: top free actions ranked by remediation value score
- `fix_under_200_month`: top free and low-cost actions
- `fix_under_750_month`: top free, low, and medium-cost actions
- `fix_top_5_risks`: five highest-scoring findings regardless of cost

## Output

The report includes:

- `remediation_simulation.simulation_model`
- `remediation_simulation.method_summary`
- `remediation_simulation.scenarios`

Each scenario includes:

- selected actions
- current overall score
- simulated overall score
- expected risk reduction
- expected risk reduction percent
- current and simulated non-compliant finding counts
- category score deltas

## Custom Simulations

Custom simulations can select findings by:

- `finding_id`
- `control_id`
- category

From an existing report:

```bash
PYTHONPATH=src python3 scripts/simulate_remediation.py \
  --report outputs/reports/cris_sme_report.json \
  --scenario-id fix_public_admin \
  --label "Fix public admin exposure" \
  --control-id NET-001
```

Multiple selectors can be combined:

```bash
PYTHONPATH=src python3 scripts/simulate_remediation.py \
  --report outputs/reports/cris_sme_report.json \
  --scenario-id fix_identity_and_public_access \
  --label "Fix IAM and public access" \
  --category IAM \
  --control-id NET-001
```

This is the API-ready path for a future dashboard workflow where a user selects findings and immediately sees the deterministic score impact.

## Product And Research Value

This is a key CRIS-SME transformation feature because it moves the system from static reporting to deterministic risk-decision planning.

For UKRI-style innovation, it supports the claim that CRIS-SME converts evidence into explainable decisions and action simulations without relying on opaque AI or unsupported probability claims.
