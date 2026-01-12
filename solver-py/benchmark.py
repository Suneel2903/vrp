
import sys
import os
import random
import time
import json
from datetime import datetime

# Enhance path to ensure we can import routeopt
sys.path.append(os.getcwd())

from routeopt.models import OptimizeRequest, Depot, Vehicle, Stop, Capacity, SolverParams
from routeopt.solver import solve_vrp

def generate_random_request(num_stops, num_vehicles, enable_local_search=False):
    # Center (Bangalore approx)
    center_lat = 12.9716
    center_lng = 77.5946
    
    # Depot
    depot = Depot(
        id="depot_main",
        lat=center_lat,
        lng=center_lng,
        shift_start_min=480, # 8 AM
        shift_end_min=1200   # 8 PM
    )
    
    # Vehicles
    vehicles = []
    for i in range(num_vehicles):
        vehicles.append(Vehicle(
            id=f"v_{i}",
            capacity=Capacity(units=100), # Ample capacity
            shift_start_min=480,
            shift_end_min=1200,
            speed_kmph=30.0,
            depot_id="depot_main"
        ))
        
    # Stops
    stops = []
    for i in range(num_stops):
        # vary by ~0.1 deg (approx 10km)
        lat = center_lat + random.uniform(-0.1, 0.1)
        lng = center_lng + random.uniform(-0.1, 0.1)
        stops.append(Stop(
            id=f"s_{i}",
            lat=lat,
            lng=lng,
            demand_units=5,
            service_time_min=10,
            time_window_start=480,
            time_window_end=1200
        ))
        
    # Params
    # We will pass extra fields in dict if model doesn't support them yet, 
    # but initially we run baseline which ignore them or we modify model first.
    # For now, we assume we will add 'local_search' in params or it's ignored.
    params = SolverParams(
        time_limit_seconds=30 if num_stops > 80 else 10 # 30s for large, 10s for others
    )
    
    # Hack to inject the flag if we haven't updated the model definition yet
    # But Pydantic might strip it.
    # We will assume we update the model before running the 'After' test.
    # For the script, we can attach it to params if we modify the class at runtime or just pass it to generator
    # but the solver needs to read it.
    
    if enable_local_search:
        setattr(params, 'local_search_metaheuristic', 'GUIDED_LOCAL_SEARCH') 
    
    return OptimizeRequest(
        depot=depot,
        depots=[depot],
        vehicles=vehicles,
        stops=stops,
        params=params
    )

def run_benchmark(name, num_stops, num_vehicles, enable_local_search):
    print(f"--- Running {name} (stops={num_stops}, vehicles={num_vehicles}, local_search={enable_local_search}) ---")
    req = generate_random_request(num_stops, num_vehicles, enable_local_search)
    
    start_time = time.time()
    try:
        resp = solve_vrp(req)
        duration = time.time() - start_time
        
        print(f"Status: {resp.summary.status}")
        print(f"Solve Time: {duration:.4f}s")
        print(f"Total Dist: {resp.summary.total_dist_km} km")
        print(f"Total Time: {resp.summary.total_time_min} min")
        print(f"Unserved: {len(resp.summary.unserved_stop_ids)}")
        return {
            "scenario": name,
            "stops": num_stops,
            "vehicles": num_vehicles,
            "local_search": enable_local_search,
            "solve_time": duration,
            "dist": resp.summary.total_dist_km,
            "total_time": resp.summary.total_time_min,
            "unserved": len(resp.summary.unserved_stop_ids)
        }
    except Exception as e:
        print(f"Failed: {e}")
        return None

if __name__ == "__main__":
    results = []
    
    # Baseline
    results.append(run_benchmark("Small Baseline", 15, 2, False))
    results.append(run_benchmark("Medium Baseline", 50, 5, False))
    results.append(run_benchmark("Large Baseline", 120, 10, False))

    # Guided Local Search (P0 Improvement)
    results.append(run_benchmark("Small Guided", 15, 2, True))
    results.append(run_benchmark("Medium Guided", 50, 5, True))
    results.append(run_benchmark("Large Guided", 120, 10, True))
    
    # Print Table
    print("\n--- Summary ---")
    print(f"{'Scenario':<20} | {'Stop/Veh':<10} | {'Time(s)':<8} | {'Dist(km)':<10} | {'Unserved':<8}")
    print("-" * 70)
    for r in results:
        if r:
            s_v = f"{r['stops']}/{r['vehicles']}"
            print(f"{r['scenario']:<20} | {s_v:<10} | {r['solve_time']:<8.4f} | {r['dist']:<10.2f} | {r['unserved']:<8}")

    
