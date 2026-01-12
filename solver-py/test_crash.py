from routeopt.solver import solve_vrp
from routeopt.models import OptimizeRequest, Vehicle, Stop, Depot, Capacity, SolverParams, CylinderType, DemandItem, GlobalSettings
import sys

print("DEBUG: crash test start", flush=True)

ctype = CylinderType(id="C1", full_weight_kg=20, empty_weight_kg=10)
depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=1000)
vehicles = [
    Vehicle(id="V1", capacity=Capacity(units=100), shift_start_min=0, shift_end_min=1000, tare_weight_kg=2000, max_weight_capacity_kg=5000)
]
stops = [
    Stop(id="S1", lat=0.09, lng=0, demand_units=10, service_time_min=10, items=[DemandItem(cylinder_type_id="C1", deliver_units=10, pickup_units=10)])
]
req = OptimizeRequest(
    depot=depot, vehicles=vehicles, stops=stops,
    params=SolverParams(cost_model="DISTANCE", global_settings=GlobalSettings(co2_factor_kg_per_ton_km=0.1)),
    cylinder_types=[ctype]
)

print("DEBUG: Calling solve_vrp", flush=True)
solve_vrp(req)
print("DEBUG: Returned", flush=True)
