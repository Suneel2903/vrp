import sys
import json
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from routeopt.models import OptimizeRequest, Stop, Vehicle, Depot, DemandItem, CylinderType, GlobalSettings, Capacity
from routeopt.solver import solve_vrp

def run_verify_p3():
    print("\n--- Starting Deterministic P3 (Multi-Trip) Verification ---", flush=True)

    # SCENARIO: 
    # Vehicle Capacity: 50 units.
    # Total Demand: 80 units (Requires 2 trips).
    # Stops: S1 (40), S2 (40).
    # All close to Depot.
    
    depot = Depot(id="DEPOT", lat=12.9716, lng=77.5946, shift_start_min=0, shift_end_min=1000) # 8am-4:40pm relative
    
    # 2 Big Stops
    stops = [
        Stop(id="S1", lat=12.9750, lng=77.5950, demand_units=40, service_time_min=10, 
             items=[DemandItem(cylinder_type_id="C1", deliver_units=40, pickup_units=0)]),
        Stop(id="S2", lat=12.9650, lng=77.5940, demand_units=40, service_time_min=10,
             items=[DemandItem(cylinder_type_id="C1", deliver_units=40, pickup_units=0)])
    ]
    
    # 1 Vehicle (Cap 50)
    vehicles = [
        Vehicle(id="V1", 
                capacity=Capacity(units=50), # Corrected
                lat=12.9716, lng=77.5946, 
                tare_weight_kg=2000, speed_kmph=30.0,
                shift_start_min=0, shift_end_min=1000) # Corrected
    ]
    
    cyl_types = [
        CylinderType(id="C1", full_weight_kg=20.0, empty_weight_kg=10.0)
    ]
    
    # ENABLE P3
    settings = GlobalSettings(
        enable_multi_trip=True,
        max_trips_per_vehicle=2,
        reload_time_min=30,
        co2_factor_kg_per_ton_km=0.1
    )
    
    req = OptimizeRequest(
        depot=depot, stops=stops, vehicles=vehicles, cylinder_types=cyl_types,
        params={"cost_model": "DISTANCE", "global_settings": settings}
    )
    
    try:
        print("DEBUG: Calling solve_vrp with P3 ENABLED (N=2)...", flush=True)
        resp = solve_vrp(req)
        
        print(f"DEBUG: Resp status: {resp.summary.status}", flush=True)
        print(f"DEBUG: Routes count: {len(resp.routes)}", flush=True)
        
        multi_trip_found = False
        for r in resp.routes:
            print(f"Route {r.vehicle_id}: Steps={len(r.steps)}, Dist={r.total_dist_km}km")
            if "#trip" in r.vehicle_id:
                multi_trip_found = True
                print(f"  -> Found Multi-Trip Segment: {r.vehicle_id}")
        
        if resp.summary.unserved_stop_ids:
            print(f"FAIL: Unserved Stops: {resp.summary.unserved_stop_ids}")
            sys.exit(1)
            
        if not multi_trip_found:
            # Maybe V1 served one, and missed other?
            # Or solver did 2 trips but named them V1 and V1#trip2.
            # R.vehicle_id will be "V1#trip2".
            # If "V1" (trip 1) and "V1#trip2" (trip 2) are separate routes in list.
            pass

        # We need AT LEAST ONE trip labeled with #trip2 or #trip1?
        # Actually logic is f"{orig_v.id}" then f"{orig_v.id}#trip{trip_idx+1}".
        # trip_idx 0 -> V1. trip_idx 1 -> V1#trip2.
        
        if not multi_trip_found and len(resp.routes) < 2:
            print("FAIL: Expected multiple trips/routes for over-capacity load.")
            sys.exit(1)
            
        print("\nPASS: P3 (Multi-Trip) verified. Solver handled N=2 expansion and returned trip segments.")
        
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_verify_p3()
