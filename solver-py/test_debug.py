import sys
import traceback

print("DEBUG: Starting Sanity Check", flush=True)

try:
    print("DEBUG: Importing OR-Tools", flush=True)
    from ortools.constraint_solver import pywrapcp
    print("DEBUG: OR-Tools OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    print("DEBUG: Importing routeopt.solver", flush=True)
    from routeopt.solver import solve_vrp
    print("DEBUG: Solver Import OK", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

print("DEBUG: Sanity Check Passed")
