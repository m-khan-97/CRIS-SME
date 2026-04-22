# Provider Capability Matrix

This matrix reflects **actual implementation status**, not aspirational parity.

| Capability | Azure | AWS | GCP |
| --- | --- | --- | --- |
| Adapter class present | Yes | Yes (placeholder) | Yes (placeholder) |
| Adapter registered for active runs | Yes | No | No |
| Mock profile normalization path | Yes | Not active | Not active |
| Live collector path | Yes | No | No |
| Control evaluation support in core engine | Yes (provider-neutral core) | Core ready, provider path not active | Core ready, provider path not active |
| Compliance mapping | Yes | Provider-neutral mapping model, no active collector | Provider-neutral mapping model, no active collector |
| Dashboard/report integration | Yes | Follows core schema when activated | Follows core schema when activated |

## Notes

- CRIS-SME is Azure-first by active runtime support.
- AWS/GCP are intentionally represented as planned/partial to avoid overclaiming.
- Provider support should only be upgraded in this matrix after collector + tests + docs are in place.
