# VRP Solver (Python)

Optimization engine for Saral Ravaana.

### Setup
1. `python -m venv .venv`
2. `.\.venv\Scripts\activate`
3. `pip install -r requirements.txt`

### Verification
To verify the solver implementation (Phase 0/1/2/3):
1. Activate venv.
2. Run harness: `python tests/verify_all.py`
3. Output should start with "=== Verification Harness ===" and end with "ALL TESTS PASSED".
Logs are saved in `artifacts/verification/`.
