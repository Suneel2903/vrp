from fastapi import FastAPI, HTTPException
from .models import OptimizeRequest, OptimizeResponse, SolutionSummary
from .solver import solve_vrp

app = FastAPI(title="LPG Distribution Solver")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/health/solver")
def health_check_strict():
    # Could add deeper check like DB ping or scratch dir check
    return {"status": "ready", "service": "routeopt-solver"}

@app.post("/optimize", response_model=OptimizeResponse)
def optimize_route(request: OptimizeRequest):
    try:
        # Validate inputs (basic checks)
        if not request.vehicles:
            raise HTTPException(status_code=400, detail="No vehicles provided")
        if not request.stops:
            raise HTTPException(status_code=400, detail="No stops provided")
            
        # Call the solver
        response = solve_vrp(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
