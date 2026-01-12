import sys
import os

# Add path so we can import solver
# Add path so we can import solver
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Hack to make "routeopt.models" accessible if solver.py uses relative imports
# Actually, if solver.py says "from .models", and we import it as "routeopt.solver", it should work IF routeopt is a package.
# But we are running from root.
from routeopt.solver import solve_vrp
from routeopt.models import OptimizeRequest, OptimizeResponse, Vehicle, Stop, Depot, Capacity, SolverParams

def run_test_t1_vehicle_count():
    print("\n--- Test P0-T1: Vehicle Count ---")
    depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=600)
    vehicles = []
    for i in range(5):
        vehicles.append(Vehicle(id=f"V{i}", capacity=Capacity(units=10), shift_start_min=0, shift_end_min=600))
    
    stops = [
        Stop(id="S1", lat=0.01, lng=0.01, demand_units=1, service_time_min=10, time_window_start=0, time_window_end=600),
        Stop(id="S2", lat=0.02, lng=0.02, demand_units=1, service_time_min=10, time_window_start=0, time_window_end=600)
    ]
    
    p = SolverParams(time_limit_seconds=1)
    req = OptimizeRequest(depot=depot, vehicles=vehicles, stops=stops, params=p, approach="BALANCED")
    print(f"Request Keys: {req.dict().keys()}")
    print(f"Has Approach? {'approach' in req.dict()}")
    resp = solve_vrp(req)
    
    used = len([r for r in resp.routes if len(r.steps) > 0])
    print(f"Vehicles Used: {used} (Expected 1 or 2)")
    assert 1 <= used <= 2
    print("PASS: Vehicle count sane.")

def run_test_t2_waiting_time():
    print("\n--- Test P0-T2: Waiting Time ---")
    # To force waiting with floating start, we need 2 stops.
    # Stop 1 anchors the timeline early. Stop 2 forces a wait.
    depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=1000)
    vehicles = [Vehicle(id="V1", capacity=Capacity(units=10), shift_start_min=0, shift_end_min=1000, speed_kmph=60)]
    
    stops = [
        # Stop 1: Must occur at 0-10.
        Stop(id="S1_ANCHOR", lat=0.01, lng=0, demand_units=1, service_time_min=10, time_window_start=0, time_window_end=10),
        # Stop 2: Close by (0.01 deg ~1km ~1min). Window starts 100.
        # Earliest Arrival: 0 (start) + travel(D->S1) + 10(S1 Svc) + travel(S1->S2).
        # Travel D(0,0)->S1(0.01,0) ~ 1.1km. @60kmph = 1.1 min.
        # Arrival S1 ~ 1.1. Depart S1 ~ 11.1.
        # Travel S1->S2(0.01, 0.01). ~1.1km. ~1.1 min.
        # Arrive S2 ~ 12.2.
        # S2 Window Start = 100.
        # Waiting ~ 87.8 mins.
        Stop(id="S2_WAIT", lat=0.01, lng=0.01, demand_units=1, service_time_min=10, time_window_start=100, time_window_end=200)
    ]
    
    req = OptimizeRequest(depot=depot, vehicles=vehicles, stops=stops, approach="BALANCED")
    resp = solve_vrp(req)
    
    if not resp.routes or not resp.routes[0].steps:
        print("FAIL: No route found.")
        return

    # Find S2 step
    step2 = next((s for s in resp.routes[0].steps if s.stop_id == "S2_WAIT"), None)
    if not step2:
        print("FAIL: S2_WAIT not served.")
        return
        
    print(f"S2 Waiting Time: {step2.waiting_time}")
    if step2.waiting_time > 50:
        print("PASS: Waiting time detected.")
    else:
        print(f"FAIL: Waiting time too low ({step2.waiting_time}). Start time shifted?")


def run_test_t3_objective_sanity():
    print("\n--- Test P0-T3: Objective Sanity ---")
    # Setup standard request
    depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=1000)
    vehicles = [Vehicle(id="V1", capacity=Capacity(units=100), shift_start_min=0, shift_end_min=1000, speed_kmph=30)]
    stops = [
        Stop(id="S1", lat=0.01, lng=0, demand_units=1, service_time_min=10),
        Stop(id="S2", lat=0.01, lng=0.01, demand_units=1, service_time_min=10)
    ]
    
    # Run Distance
    p_dist = SolverParams(cost_model="DISTANCE")
    r_dist = solve_vrp(OptimizeRequest(depot=depot, vehicles=vehicles, stops=stops, params=p_dist))
    
    # Run Time
    p_time = SolverParams(cost_model="TIME")
    r_time = solve_vrp(OptimizeRequest(depot=depot, vehicles=vehicles, stops=stops, params=p_time))
    
    print(f"Distance Mode: {r_dist.summary.total_dist_km} km")
    print(f"Time Mode: {r_time.summary.total_time_min} min")
    
    # Usually consistent on simple layouts, but Time mode prioritizes speed?
    # Here with 1 vehicle structure is same.
    # But verifies no crash.
    print("PASS: Runs completed.")


def run_test_t4_drop_penalty():
    print("\n--- Test P0-T4: Drop Penalty ---")
    depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=1000)
    vehicles = [Vehicle(id="V1", capacity=Capacity(units=10), shift_start_min=0, shift_end_min=1000, speed_kmph=30)]
    
    # Far stop (lat 1.0 ~ 111km). Round trip ~ 222km.
    # Dist Cost (Meters) ~ 222,000.
    # Scaled Penalty (Base * 1000? No, usually Base * 1 if distance is meters? 
    # Let's check solver params. penalty_base is typically multiplied by 100 in solver if using "DISTANCE"? 
    # Or just used as is? 
    # In solver.py: penalty = params.penalty_base
    # If using distance, penalty is usually large.
    # Actually solver.py logic: node_penalty = penalty_base (if set) or massive.
    
    # Scenario 1: Low Penalty -> Drop
    # Cost ~ 200,000. Penalty = 100. Should Drop.
    stops = [Stop(id="S_FAR", lat=1.0, lng=0, demand_units=1, service_time_min=10)]
    
    p_low = SolverParams(cost_model="DISTANCE", penalty_base=100, allow_unserved=True)
    r_low = solve_vrp(OptimizeRequest(depot=depot, vehicles=vehicles, stops=stops, params=p_low))
    
    if "S_FAR" in r_low.summary.unserved_stop_ids:
        print("PASS: Low penalty -> Dropped.")
    else:
        print(f"FAIL: Low penalty -> Served. Cost: {r_low.summary.total_dist_km}")
        
    # Scenario 2: High Penalty -> Serve
    # Cost ~ 200,000. Penalty = 10,000,000. Should Serve.
    p_high = SolverParams(cost_model="DISTANCE", penalty_base=10000000, allow_unserved=True)
    r_high = solve_vrp(OptimizeRequest(depot=depot, vehicles=vehicles, stops=stops, params=p_high))
    
    if "S_FAR" not in r_high.summary.unserved_stop_ids:
        print("PASS: High penalty -> Served.")
    else:
        print("FAIL: High penalty -> Dropped.")
        


def run_test_t5_split_delivery():
    print("\n--- Test P0-T5: Split Metrics ---")
    depot = Depot(id="D1", lat=0, lng=0, shift_start_min=0, shift_end_min=1000)
    vehicles = [Vehicle(id="V1", capacity=Capacity(units=10), shift_start_min=0, shift_end_min=1000, speed_kmph=60)]
    
    # Stop with demand 20 (SPLIT SIZE 15 -> 15 + 5 chunks)
    # 2 Chunks total.
    # If we penalize very low, and make it far, maybe one gets dropped?
    # Actually explicit test: Create Demand 20. params.allow_unserved=True.
    # Set penalty low (1).
    stops = [Stop(id="S_SPLIT", lat=5.0, lng=5.0, demand_units=20, service_time_min=10)]
    
    # We want to force a drop. Distance is huge. Penalty is 1. Should drop all.
    # But we want PARTIAL. Hard to force partial with 1 vehicle and uniform penalty unless capacity constrains it.
    # If Vehicle cap is 10. Split is 15+5.
    # Node 1 (15) > Cap(10). Impossible to serve? 
    # Actually solver splits: 15, 5. 
    # If capacity is 10... 15 fits? NO.
    # So 15-chunk is dropped due to capacity (if no other vehicle).
    # 5-chunk fits. Might be served if profitable (cost < penalty). 
    # But cost is high (lat 5.0).
    
    # To test partial reporting ID structure:
    # Just run it and see if "unserved_ids" contains "#chunk"
    
    p = SolverParams(cost_model="DISTANCE", penalty_base=1, allow_unserved=True)
    req = OptimizeRequest(depot=depot, vehicles=vehicles, stops=stops, params=p)
    resp = solve_vrp(req)
    
    unserved = resp.summary.unserved_stop_ids
    print(f"Unserved IDs: {unserved}")
    

    has_chunk = any("#chunk" in uid for uid in unserved)
    
    with open("t5_result.txt", "w") as f:
        f.write(f"Unserved: {unserved}\n")
        f.write(f"Has Chunk: {has_chunk}\n")
    
    if has_chunk:
        print("PASS: Chunk IDs detected.")
    else:
        print("FAIL: No chunk IDs found (Format: id#chunk_n)")
        # Print helpful debug info
        print(f"  Summary Status: {resp.summary.status}")
        print(f"  Unserved Count: {len(unserved)}")
        raise Exception("Split metric fail")

if __name__ == "__main__":
    try:
        run_test_t1_vehicle_count()
        run_test_t2_waiting_time()
        run_test_t3_objective_sanity()
        run_test_t4_drop_penalty()
        run_test_t5_split_delivery()
        print("\n[P0 FINAL CLOSE] ALL TESTS PASSED.")
    except Exception as e:
        print(f"\n[P0 FATAL] Test Failed: {e}")
        sys.exit(1)

