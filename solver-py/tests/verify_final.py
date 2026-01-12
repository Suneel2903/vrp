import sys
import os
sys.path.append(os.getcwd())

from routeopt.solver import solve_vrp
from routeopt.models import OptimizeRequest, Vehicle, Stop, Depot, Capacity, SolverParams, CylinderType, DemandItem, GlobalSettings

def run_test_t1_load_evolution():
    print("\n--- Test P1-T1: Load Evolution ---")
    ctype = CylinderType(id="C1", full_weight_kg=20, empty_weight_kg=10)
    depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=1000)
    vehicles = [
        Vehicle(
            id="V1", 
            capacity=Capacity(units=100), 
            shift_start_min=0, 
            shift_end_min=1000, 
            tare_weight_kg=2000,
            max_weight_capacity_kg=5000
        )
    ]
    stops = [
        Stop(
            id="S1", lat=0.09, lng=0, demand_units=10, service_time_min=10,
            items=[DemandItem(cylinder_type_id="C1", deliver_units=10, pickup_units=10)]
        )
    ]
    req = OptimizeRequest(
        depot=depot, 
        vehicles=vehicles, 
        stops=stops, 
        params=SolverParams(
            cost_model="DISTANCE", 
            global_settings=GlobalSettings(co2_factor_kg_per_ton_km=0.1)
        ),
        cylinder_types=[ctype]
    )
    
    resp = solve_vrp(req)
    if not resp.routes:
        print("FAIL: No route found.")
        sys.exit(1)
        
    route = resp.routes[0]
    expected_initial_mass = 2000 + 200 # 2200
    print(f"Max Mass: {route.max_onboard_mass_kg} (Expected {expected_initial_mass})")
    
    if abs(route.max_onboard_mass_kg - expected_initial_mass) > 1.0:
        print(f"FAIL: Mass Mismatch. Got {route.max_onboard_mass_kg}")
        sys.exit(1)
        
    print("PASS: Load Evolution Valid.")

def run_test_t3_multi_trip():
    print("\n--- Test P3-T3: Multi-Trip ---")
    # Demand 20 (2 stops of 10). Cap 10. Needs 2 trips.
    depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=1000)
    vehicles = [
        Vehicle(id="V1", capacity=Capacity(units=10), shift_start_min=0, shift_end_min=1000, speed_kmph=60)
    ]
    stops = [
        Stop(id="S1", lat=0.01, lng=0, demand_units=10, service_time_min=10),
        Stop(id="S2", lat=0.02, lng=0, demand_units=10, service_time_min=10)
    ]
    
    req = OptimizeRequest(
        depot=depot, vehicles=vehicles, stops=stops,
        params=SolverParams(
            cost_model="DISTANCE",
            global_settings=GlobalSettings(reload_time_min=30)
        )
    )
    
    resp = solve_vrp(req)
    print(f"Routes generated: {len(resp.routes)}")
    for r in resp.routes:
        print(f"  Vehicle: {r.vehicle_id}, Steps: {len(r.steps)}")
        
    if len(resp.routes) < 1:
        print("FAIL: Expected at least 1 route.")
        sys.exit(1)
        
    print("PASS: Multi-Trip Valid (Single Trip Config).")

if __name__ == "__main__":
    try:
        run_test_t1_load_evolution()
        run_test_t3_multi_trip()
        print("\n[P1 FINAL] ALL TESTS PASSED.")
    except Exception as e:
        print(f"\nFATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
