# Release Report: Phase 0 Release Candidate

**Date**: 2026-01-12
**Status**: PASS

## Key Achievements
- **Zero Time Bug**: RESOLVED. Solver uses Centiminute (x100) precision.
- **Wait Time Physics**: VERIFIED. Early arrivals force wait time logic.
- **Drop Penalty**: VERIFIED. High penalties force service; low penalties allow drops.
- **P3 Multi-Trip**: VERIFIED. Deterministic success with `fix_start_cumul=False` and Anchor logic.
- **Objective Divergence**: VERIFIED. Deterministic selection of vehicles based on cost model (Distance vs Time vs Money).
- **Fixed Cost Isolation**: VERIFIED. Fixed costs only apply to MONEY objective, preventing unit-mixing artifacts.

## Verification Summary
Command: `python tests/verify_all.py`

| Script | Status | Notes |
| :--- | :--- | :--- |
| `verify_p0.py` | **PASS** | Core sanity, vehicle limits, wait time check. |
| `verify_p1_p2.py` | **PASS** | Physics (Mass) and Green (CO2) logic. |
| `verify_p3.py` | **PASS** | Multi-trip sequencing N=2. |
| `certify_phase0.py` | **PASS** | Objective Truth validated. Distance/Time/Money models diverge correctly. Strict fatal checks enforced. |

## CI & Documentation
- **CI Workflow**: `.github/workflows/ci.yml` created.
- **User Guide**: `HOW_TO_USE.md` updated with Carbon Analytics.
- **In-App Guide**: Created at `/how-to-use` with click-flows.

## Installation / Verification
```powershell
cd solver-py
.\.venv\Scripts\activate
python tests/verify_all.py
```

## Phase 0 Contract
The solver baseline is frozen.
- **Objective Truth**: Fixed costs apply ONLY to `MONEY`.
- **Determinism**: `certify_phase0.py` acts as the gatekeeper for any semantic changes.
- **CI**: `verify_all.py` is the single source of truth for branch protection.

## Known Limitations
1. **Interactive Map**: Customers CRUD actions are placeholders.
2. **P3 Default**: Multi-trip is OFF by default (Safe).
