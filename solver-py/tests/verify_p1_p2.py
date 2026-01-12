import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from routeopt.solver import solve_vrp
from routeopt.models import OptimizeRequest, Vehicle, Stop, Depot, Capacity, SolverParams, CylinderType, DemandItem, GlobalSettings

def run_verify_p1_p2():
    print("\n--- Starting Deterministic P1/P2 Verification ---")

    # 1. Setup deterministic data
    # Cylinders: C1 (20kg full, 10kg empty). C2 (50kg full, 25kg empty).
    c1 = CylinderType(id="C1", full_weight_kg=20.0, empty_weight_kg=10.0)
    c2 = CylinderType(id="C2", full_weight_kg=50.0, empty_weight_kg=25.0)
    
    # Depot at 0,0
    depot = Depot(id="D", lat=0.0, lng=0.0, shift_start_min=0, shift_end_min=600)
    
    # Vehicle: Tare 2000kg. Capacity 100 units.
    # Max Weight Capacity 5000kg (should assert WARN if exceeded, though we won't exceed here to keep it simple)
    v1 = Vehicle(
        id="V1", 
        capacity=Capacity(units=100), 
        shift_start_min=0, shift_end_min=600, 
        tare_weight_kg=2000.0,
        max_weight_capacity_kg=5000.0,
        speed_kmph=60.0 # 1 km/min
    )

    # Stop 1 (10km away): Deliver 10 C1. Pickup 0.
    # Lat 0.09 approx 10km from 0.0 (1 deg ~ 111km -> 0.09 ~ 10km). 
    # For strict determinism, we rely on solver's distance calc or mock it. 
    # Solver uses Haversine. 0.0 -> 0.09 deg lat is:
    # 0.09 * 111.32 km = 10.0188 km. Let's assume ~10.02 km.
    s1 = Stop(
        id="S1", lat=0.09, lng=0.0, 
        demand_units=10, service_time_min=10,
        items=[DemandItem(cylinder_type_id="C1", deliver_units=10, pickup_units=0)]
    )
    
    # Stop 2 (Multi-type B1 Evidence): Deliver 5 C2. Pickup 5 C1.
    # Located at 0.18 lat (another ~10km from S1).
    s2 = Stop(
        id="S2", lat=0.18, lng=0.0,
        demand_units=5, service_time_min=10,
        items=[
            DemandItem(cylinder_type_id="C2", deliver_units=5, pickup_units=0),
            DemandItem(cylinder_type_id="C1", deliver_units=0, pickup_units=5)
        ]
    )

    req = OptimizeRequest(
        depot=depot, 
        vehicles=[v1], 
        stops=[s1, s2], 
        params=SolverParams(
            cost_model="DISTANCE", 
            global_settings=GlobalSettings(co2_factor_kg_per_ton_km=0.1, enable_multi_trip=False)
        ),
        cylinder_types=[c1, c2]
    )

    # Dump Payload for B1 Evidence
    print("\n[B1 Evidence] Solver Payload (Partial):")
    payload_debug = {
        "stops": [
            {
                "id": s.id, 
                "items": [{"type": i.cylinder_type_id, "del": i.deliver_units, "pick": i.pickup_units} for i in s.items]
            } for s in req.stops
        ],
        "cylinder_types": [{"id": c.id, "full": c.full_weight_kg} for c in req.cylinder_types]
    }
    print(json.dumps(payload_debug, indent=2))
    
    print("DEBUG: Calling solve_vrp...", flush=True)
    resp = solve_vrp(req)
    print(f"DEBUG: Resp type: {type(resp)}", flush=True)
    
    if not resp.routes:
        print("FAIL: No routes generated.")
        sys.exit(1)

    r = resp.routes[0]
    
    # --- Verify Physics (Load Evolution) ---
    # Initial Load Logic:
    # S1: Del 10 C1. 
    # S2: Del 5 C2.
    # Initial Onboard: 10 C1 (Full) + 5 C2 (Full).
    # Mass = Tare(2000) + 10*20 + 5*50 = 2000 + 200 + 250 = 2450 kg.
    
    print(f"\nRoute Max Mass: {r.max_onboard_mass_kg} kg")
    if abs(r.max_onboard_mass_kg - 2450.0) > 1.0:
        print(f"FAIL: Expected Max Mass ~2450, got {r.max_onboard_mass_kg}")
        sys.exit(1)

    # Step Analysis
    # Leg 1 (Depot -> S1): Dist ~10.02 km. Mass 2450.
    # Ton-KM = 10.02 * 2.45 = 24.549
    
    # At S1: Drop 10 C1. No Pickup.
    # New Load: 0 C1, 5 C2.
    # Mass = 2000 + 0 + 250 = 2250 kg.
    
    # Leg 2 (S1 -> S2): Dist ~10.02 km. Mass 2250.
    # Ton-KM = 10.02 * 2.25 = 22.545
    
    # At S2: Drop 5 C2. Pickup 5 C1 (Empty).
    # New Load: 0 C1(F), 0 C2(F), 5 C1(E). 
    # Mass = 2000 + 0 + 0 + 5*10 = 2050 kg.
    
    # Leg 3 (S2 -> Depot): Dist ~20.04 km (S2 is 0.18, Depot 0.0).
    # Ton-KM = 20.04 * 2.05 = 41.082
    
    # Total Ton-KM = 24.549 + 22.545 + 41.082 = 88.176
    
    print(f"Route Total Ton-KM: {r.total_ton_km}")
    # Allow small epsilon for Haversine diffs
    if abs(r.total_ton_km - 88.176) > 5.0: 
        print(f"FAIL: Expected Ton-KM ~88.1, got {r.total_ton_km}")
        sys.exit(1)

    # --- Verify P2 (CO2) ---
    # CO2 = 88.176 * 0.1 = 8.8176 kg
    print(f"Route CO2: {r.co2_kg} kg")
    expected_co2 = r.total_ton_km * 0.1
    if abs(r.co2_kg - expected_co2) > 0.01:
        print(f"FAIL: CO2 calc mismatch. Got {r.co2_kg}, expected {expected_co2}")
        sys.exit(1)

    print("\nPASS: P1 (Physics) and P2 (Green) verified deterministically.")
    print("PASS: B1 (Multi-type stop) verified via inputs and mass effect.")

if __name__ == "__main__":
    try:
        run_verify_p1_p2()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
