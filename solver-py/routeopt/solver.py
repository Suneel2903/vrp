from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import List, Tuple
from .models import OptimizeRequest, OptimizeResponse, VehicleRoute, SolutionSummary, RouteStep, Stop, Vehicle, Depot
from .matrix import compute_time_matrix, compute_distance_matrix
import traceback

def create_data_model(request: OptimizeRequest):
    data = {}
    SPLIT_CHUNK_SIZE = 15 
    solver_nodes = []
    
    all_depots = [request.depot] + (request.depots or [])
    unique_depots = {d.id: d for d in all_depots}.values()
    depot_id_to_node_index = {}
    
    for i, depot in enumerate(unique_depots):
        solver_nodes.append({
            'lat': depot.lat, 'lng': depot.lng, 'demand': 0, 'service': 0, 'stop_ref': None,
            'start': depot.shift_start_min, 'end': depot.shift_end_min, 'type': 'depot', 'id': depot.id
        })
        depot_id_to_node_index[depot.id] = len(solver_nodes) - 1

    stops_start_index = len(solver_nodes)
    node_map = {}
    for i in range(stops_start_index): node_map[i] = None

    for stop in request.stops:
        demand = stop.demand_units
        if demand > SPLIT_CHUNK_SIZE:
             import math
             remaining = demand
             chunk_idx = 0
             service_per_unit = stop.service_time_min / demand if demand > 0 else 0
             while remaining > 0:
                 take = min(remaining, SPLIT_CHUNK_SIZE)
                 chunk_service = service_per_unit * take
                 chunk_id = f"{stop.id}#chunk_{chunk_idx}"
                 chunk_idx += 1
                 solver_nodes.append({
                    'lat': stop.lat, 'lng': stop.lng, 'demand': take, 'service': int(round(chunk_service)), 
                    'stop_ref': stop, 'chunk_id': chunk_id, 'start': stop.time_window_start, 'end': stop.time_window_end,
                    'type': 'stop', 'id': chunk_id
                 })
                 remaining -= take
        else:
            solver_nodes.append({
                'lat': stop.lat, 'lng': stop.lng, 'demand': demand, 'service': int(round(stop.service_time_min)),
                'stop_ref': stop, 'chunk_id': stop.id, 'start': stop.time_window_start, 'end': stop.time_window_end,
                'type': 'stop', 'id': stop.id 
            })

    for i in range(stops_start_index, len(solver_nodes)):
        node_map[i] = solver_nodes[i]

    data['node_map'] = node_map
    data['depot_map'] = depot_id_to_node_index
    
    locations = [(n['lat'], n['lng']) for n in solver_nodes]
    data['distance_matrix_km'] = compute_distance_matrix(locations)
    data['time_matrix_min'] = compute_time_matrix(locations, speed_kmh=1.0) 
    
    data['time_windows'] = []
    data['service_times'] = []
    data['demands'] = []
    
    default_start = request.depot.shift_start_min
    default_end = request.depot.shift_end_min
    
    for n in solver_nodes:
        s = n['start'] if n['start'] is not None else default_start
        e = n['end'] if n['end'] is not None else default_end
        # Convert Time Window to Centiminutes if needed?
        # If we scale Dimension, we must scale Windows too.
        # Yes.
        data['time_windows'].append((int(s * 100), int(e * 100)))
        data['service_times'].append(n['service'])
        data['demands'].append(n['demand'])

    # P3: Config via Feature Flags
    data['vehicle_capacities'] = []
    data['vehicle_starts'] = []
    data['vehicle_ends'] = []
    data['vehicle_speeds'] = []
    data['vehicle_fixed_costs'] = []
    data['vehicle_map'] = [] 
    
    multi_trip_n = 1 
    if request.params.global_settings and request.params.global_settings.enable_multi_trip:
         multi_trip_n = request.params.global_settings.max_trips_per_vehicle
    
    for v_idx, v in enumerate(request.vehicles):
        for t in range(multi_trip_n):
             data['vehicle_capacities'].append(v.capacity.units)
             data['vehicle_speeds'].append(v.speed_kmph or 30.0)
             d_id = v.depot_id or request.depot.id
             d_idx = depot_id_to_node_index.get(d_id, 0)
             data['vehicle_starts'].append(d_idx)
             data['vehicle_ends'].append(d_idx)
             fc = v.fixed_cost or 0.0
             data['vehicle_fixed_costs'].append(fc)
             data['vehicle_map'].append({'orig_v': v, 'trip_idx': t, 'orig_idx': v_idx})
    
    data['num_vehicles'] = len(data['vehicle_capacities'])
    data['multi_trip_n'] = multi_trip_n

    return data

def solve_vrp(request: OptimizeRequest) -> OptimizeResponse:
    try:
        data = create_data_model(request)
        
        c_model = (request.params.cost_model or "DISTANCE").upper()
        if c_model not in ["DISTANCE", "TIME", "MONEY"]: c_model = "DISTANCE" 
        request.params.cost_model = c_model
        
        manager = pywrapcp.RoutingIndexManager(
            len(data['time_matrix_min']),
            data['num_vehicles'],
            data['vehicle_starts'],
            data['vehicle_ends']
        )
        routing = pywrapcp.RoutingModel(manager)

        transit_callback_indices_for_time = []
        
        # Factory to prevent closure/GC issues
        def make_time_callback(manager, data, speed):
            s_val = speed
            # Return CENTIMINUTES (x100)
            def cb(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                dist_km = data['distance_matrix_km'][from_node][to_node]
                # (dist / speed) * 60 = Minutes
                # * 100 = Centiminutes
                travel_time_cmin = (dist_km / s_val) * 6000.0
                return int(round(travel_time_cmin + (data['service_times'][from_node] * 100)))
            return cb

        data['callbacks_keep_alive'] = []

        for vehicle_id in range(data['num_vehicles']):
            speed = float(data['vehicle_speeds'][vehicle_id] or 30.0)
            if speed <= 0: speed = 1.0
            
            cb = make_time_callback(manager, data, speed)
            data['callbacks_keep_alive'].append(cb)
            
            callback_index = routing.RegisterTransitCallback(cb)
            transit_callback_indices_for_time.append(callback_index)
            
        time_dimension_name = 'Time'
        # Slack 30 min -> 3000 cmin
        # Capacity 30 days -> 30 * 24 * 60 * 100 = 4320000 cmin
        routing.AddDimensionWithVehicleTransits(
            transit_callback_indices_for_time, 30 * 60 * 100, 30 * 24 * 60 * 100, False, time_dimension_name)
        time_dimension = routing.GetDimensionOrDie(time_dimension_name)
        
        for location_idx, (start, end) in enumerate(data['time_windows']):
            index = manager.NodeToIndex(location_idx)
            if index != -1: time_dimension.CumulVar(index).SetRange(start, end)

        # P3: Precedence (Only if N > 1)
        solver = routing.solver()
        reload_time = 30 * 100 # Centiminutes
        if request.params.global_settings:
            reload_time = int(request.params.global_settings.reload_time_min * 100)
            
        trips = data.get('multi_trip_n', 1)
        if trips > 1:
            orig_veh_count = len(request.vehicles)
            for v_orig_idx in range(orig_veh_count):
                for t in range(trips - 1):
                    idx_t1 = v_orig_idx * trips + t
                    idx_t2 = v_orig_idx * trips + t + 1
                    end_node_t1 = routing.End(idx_t1)
                    start_node_t2 = routing.Start(idx_t2)
                    solver.Add(time_dimension.CumulVar(start_node_t2) >= time_dimension.CumulVar(end_node_t1) + reload_time)

        # Capacity Dimension (Demand)
        def make_demand_callback(manager, data):
             def cb(from_index):
                 from_node = manager.IndexToNode(from_index)
                 return data['demands'][from_node]
             return cb
             
        demand_cb = make_demand_callback(manager, data)
        data['callbacks_keep_alive'].append(demand_cb)
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_cb)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

        cost_model = request.params.cost_model or "DISTANCE"
        
        # Apply Fixed Costs
        # Apply Fixed Costs (MONEY ONLY)
        if cost_model == "MONEY":
            for v in range(data['num_vehicles']):
                fc_val = data['vehicle_fixed_costs'][v]
                if fc_val > 0:
                    # Currency units (e.g. Rupee) -> Cents (x100)
                    routing.SetFixedCostOfVehicle(int(fc_val * 100), v)
        else:
            # For DISTANCE/TIME, ignore fixed cost to prevent unit mixing/swamping.
            pass

        previous_cost_model = cost_model # Just reference
        fuel_cost = request.params.fuel_cost_per_km
        driver_cost = request.params.driver_cost_per_hour
        
        dist_callback_indices = []
        for vehicle_id in range(data['num_vehicles']):
             def dist_callback(from_index, to_index):
                 from_node = manager.IndexToNode(from_index)
                 to_node = manager.IndexToNode(to_index)
                 return int(data['distance_matrix_km'][from_node][to_node] * 1000)
             idx = routing.RegisterTransitCallback(dist_callback)
             dist_callback_indices.append(idx)

        if cost_model == "DISTANCE":
            for v in range(data['num_vehicles']):
                routing.SetArcCostEvaluatorOfVehicle(dist_callback_indices[v], v)
        elif cost_model == "TIME":
            # Reuse Dimension Callbacks for Objective (Stability Test)
            for v in range(data['num_vehicles']):
                routing.SetArcCostEvaluatorOfVehicle(transit_callback_indices_for_time[v], v)
            
            # Set Span Cost (Objective) - Coefficient 1 (Minimize CMin)
            time_dimension.SetSpanCostCoefficientForAllVehicles(1)
                
        elif cost_model == "MONEY":
             safe_fuel = fuel_cost or 0.0
             safe_driver = driver_cost or 0.0
             # Driver Cost per Hour -> Per CMin?
             # cost = dist * fuel + time_hr * driver
             # time_hr = cmin / 6000
             # cost = dist * fuel + cmin * (driver / 6000)
             # Multiplier 100 -> Cents
             for v in range(data['num_vehicles']):
                 speed = float(data['vehicle_speeds'][v] or 30.0)
                 def cost_callback(from_index, to_index, v_idx=v, s_val=speed):
                      from_node = manager.IndexToNode(from_index)
                      to_node = manager.IndexToNode(to_index)
                      dist_km = data['distance_matrix_km'][from_node][to_node]
                      
                      travel_cmin = (dist_km / s_val) * 6000.0
                      cmin_total = travel_cmin + (data['service_times'][from_node] * 100)
                      
                      cost_cents = (dist_km * safe_fuel * 100) + (cmin_total / 6000.0 * safe_driver * 100)
                      return int(cost_cents)
                 c_idx = routing.RegisterTransitCallback(cost_callback)
                 routing.SetArcCostEvaluatorOfVehicle(c_idx, v)
        else:
             for v in range(data['num_vehicles']):
                routing.SetArcCostEvaluatorOfVehicle(dist_callback_indices[v], v)
        
        def get_drop_penalty(base_val, c_model):
            val = base_val or 1000000 
            if c_model == "DISTANCE": return int(val * 1000)
            elif c_model == "TIME": return int(val * 100) # Centiminutes
            elif c_model == "MONEY": return int(val * 100)
            return int(val)
            
        penalty = get_drop_penalty(request.params.penalty_base, cost_model)
        for i in range(len(data['depot_map']), manager.GetNumberOfNodes()):
             if request.params.allow_unserved:
                 routing.AddDisjunction([manager.NodeToIndex(i)], penalty)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        if request.params.time_limit_seconds:
             search_parameters.time_limit.seconds = request.params.time_limit_seconds
        
        if request.params.local_search_metaheuristic == "GUIDED_LOCAL_SEARCH":
             search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH

        solution = routing.SolveWithParameters(search_parameters)
        
        routes = []
        unserved_ids = []
        status_str = "failed"
        
        if solution:
            status_str = "optimized" 
            for i in range(routing.Size()):
                if not routing.IsStart(i) and not routing.IsEnd(i):
                     next_val = solution.Value(routing.NextVar(i))
                     if next_val == i:
                         node_idx = manager.IndexToNode(i)
                         n_data = data['node_map'].get(node_idx)
                         # Debug T4/T5
                         # print(f"DEBUG: Unserved Check Idx {i} Node {node_idx} Data {n_data}")
                         if n_data and n_data.get('type') == 'stop':
                             unserved_ids.append(n_data.get('id', str(node_idx)))

        total_dist = 0.0
        total_time = 0
        
        if solution:
             served_indices = []
             for vehicle_id in range(data['num_vehicles']):
                if solution.Value(routing.NextVar(routing.Start(vehicle_id))) == routing.End(vehicle_id): continue

                v_map = data['vehicle_map'][vehicle_id]
                orig_v = v_map['orig_v']
                (trip_idx, veh_ref) = (v_map['trip_idx'], orig_v)
                final_v_id = f"{orig_v.id}"
                if trip_idx > 0: final_v_id = f"{orig_v.id}#trip{trip_idx+1}"
                
                index = routing.Start(vehicle_id)
                r_start_cmin = solution.Min(time_dimension.CumulVar(index))
                
                steps = []
                route_dist = 0
                route_ton_km = 0.0
                max_mass_kg = 0.0
                sum_mass_kg = 0.0
                step_count_for_avg = 0
                total_demand = 0
                
                route_nodes = []
                chk_index = index
                while not routing.IsEnd(chk_index):
                     n_idx = manager.IndexToNode(chk_index)
                     route_nodes.append(n_idx)
                     chk_index = solution.Value(routing.NextVar(chk_index))
                     
                current_full = {}
                current_empty = {}
                for ct in request.cylinder_types:
                    current_full[ct.id] = 0
                    current_empty[ct.id] = 0
                    
                for n_idx in route_nodes:
                    if n_idx not in data['depot_map'].values():
                        n_data = data['node_map'].get(n_idx)
                        stop_ref = n_data.get('stop_ref')
                        if stop_ref and stop_ref.items:
                            ratio = 1.0
                            if stop_ref.demand_units > 0: ratio = n_data['demand'] / stop_ref.demand_units 
                            for item in stop_ref.items:
                                 qty = int(round(item.deliver_units * ratio))
                                 current_full[item.cylinder_type_id] = current_full.get(item.cylinder_type_id, 0) + qty
                
                cyl_weights = {ct.id: ct for ct in request.cylinder_types}
                co2_factor = 0.1
                if request.params.global_settings:
                    co2_factor = request.params.global_settings.co2_factor_kg_per_ton_km
                
                prev_node_val = None
                prev_departure_val = 0.0 
                index = routing.Start(vehicle_id)
                
                while not routing.IsEnd(index):
                     node_index = manager.IndexToNode(index)
                     time_var = time_dimension.CumulVar(index)
                     service_start_cmin = solution.Min(time_var)
                     
                     # Convert back to minutes for report logic
                     service_start_min = service_start_cmin / 100.0
                     
                     # Robust Wait Calculation (using Manual Logic steps for consistency)
                     speed = float(data['vehicle_speeds'][vehicle_id] or 30.0)
                     arrival_calculated = service_start_min 
                     
                     if prev_node_val is not None:
                         dist_km_segment = data['distance_matrix_km'][prev_node_val][node_index]
                         transit_min = (dist_km_segment / speed) * 60.0
                         arrival_calculated = prev_departure_val + transit_min
                     
                     arrival_time = arrival_calculated
                     arrival = int(round(arrival_time)) 
                     
                     waiting_time = int(max(0, service_start_min - arrival_calculated))
                     
                     service = data['service_times'][node_index]
                     departure = service_start_min + service
                     prev_departure_val = departure 
                     
                     win_start_cmin, win_end_cmin = data['time_windows'][node_index]
                     win_start = win_start_cmin / 100.0
                     win_end = win_end_cmin / 100.0
                     
                     dist_km = 0.0
                     if prev_node_val is not None:
                         dist_km = data['distance_matrix_km'][prev_node_val][node_index]
                         route_dist += dist_km
                         
                     current_mass = veh_ref.tare_weight_kg
                     total_f = 0
                     total_e = 0
                     for c_id, qty in current_full.items():
                         w = cyl_weights.get(c_id)
                         if w: 
                             current_mass += qty * w.full_weight_kg
                             total_f += qty
                     for c_id, qty in current_empty.items():
                         w = cyl_weights.get(c_id)
                         if w: 
                             current_mass += qty * w.empty_weight_kg
                             total_e += qty
                             
                     if current_mass > max_mass_kg: max_mass_kg = current_mass
                     sum_mass_kg += current_mass
                     step_count_for_avg += 1
                     route_ton_km += dist_km * (current_mass / 1000.0)
                     
                     is_depot = (node_index in data['depot_map'].values())
                     late_min = 0
                     if not is_depot and arrival > win_end: late_min = arrival - win_end
                     
                     if not is_depot:
                         node_data = data['node_map'].get(node_index)
                         stop_id_val = node_data['chunk_id'] if node_data else "UNKNOWN"
                         delivered = data['demands'][node_index]
                         
                         steps.append(RouteStep(
                             stop_id=stop_id_val, arrival_time=arrival, departure_time=int(round(departure)), service_time=service,
                             waiting_time=waiting_time, dist_from_prev_km=round(dist_km, 2), delivered_units=delivered,
                             late_minutes=late_min, window_start=int(win_start), window_end=int(win_end),
                             onboard_mass_kg=round(current_mass, 2), full_units_onboard=total_f, empty_units_onboard=total_e
                         ))
                         if stop_id_val == "S2_Wait":
                             print(f"DEBUG: S2_Wait Arr {arrival} Start {service_start_min} Win {win_start} Wait {waiting_time}")
                         total_demand += delivered
                         
                         stop_ref = node_data.get('stop_ref')
                         if stop_ref and stop_ref.items:
                            ratio = 1.0
                            if stop_ref.demand_units > 0: ratio = node_data['demand'] / stop_ref.demand_units
                            for item in stop_ref.items:
                                 del_qty = int(round(item.deliver_units * ratio))
                                 pick_qty = int(round(item.pickup_units * ratio))
                                 current_full[item.cylinder_type_id] = max(0, current_full.get(item.cylinder_type_id, 0) - del_qty)
                                 current_empty[item.cylinder_type_id] = current_empty.get(item.cylinder_type_id, 0) + pick_qty
                     
                     prev_node_val = node_index
                     index = solution.Value(routing.NextVar(index))
                
                end_index = routing.End(vehicle_id)
                dist_to_end = 0.0
                if prev_node_val is not None:
                     end_node = manager.IndexToNode(end_index)
                     dist_to_end = data['distance_matrix_km'][prev_node_val][end_node]
                route_dist += dist_to_end
                
                final_mass = veh_ref.tare_weight_kg
                for c_id, qty in current_full.items():
                     w = cyl_weights.get(c_id)
                     if w: final_mass += qty * w.full_weight_kg
                for c_id, qty in current_empty.items():
                     w = cyl_weights.get(c_id)
                     if w: final_mass += qty * w.empty_weight_kg
                
                route_ton_km += dist_to_end * (final_mass / 1000.0)
                r_end_arrival_cmin = solution.Min(time_dimension.CumulVar(end_index))
                r_co2 = route_ton_km * co2_factor
                
                routes.append(VehicleRoute(
                    vehicle_id=final_v_id, steps=steps, total_dist_km=round(route_dist, 2),
                    total_time_min=round((r_end_arrival_cmin - r_start_cmin) / 100.0), total_demand_units=total_demand,
                    total_ton_km=round(route_ton_km, 3), max_onboard_mass_kg=round(max_mass_kg, 2),
                    avg_onboard_mass_kg=round(sum_mass_kg/max(1, step_count_for_avg), 2), co2_kg=round(r_co2, 3)
                ))
                if c_model == "TIME":
                     # print(f"DEBUG: TIME CUMUL START {r_start_cmin} END {r_end_arrival_cmin} Diff {r_end_arrival_cmin - r_start_cmin}")
                     pass
                total_time += round((r_end_arrival_cmin - r_start_cmin) / 100.0)
                total_dist += route_dist

    except Exception as e:
        traceback.print_exc()
        with open("solver_error.log", "w") as f:
            f.write(traceback.format_exc())
        raise e

    sum_ton_km = sum(r.total_ton_km for r in routes)
    sum_co2 = sum(r.co2_kg for r in routes)

    return OptimizeResponse(
        routes=routes,
        summary=SolutionSummary(
            total_dist_km=round(total_dist, 2), total_time_min=total_time, unserved_stop_ids=unserved_ids,
            status=status_str, total_ton_km=round(sum_ton_km, 3), total_co2_kg=round(sum_co2, 3)
        )
    )
