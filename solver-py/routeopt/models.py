from pydantic import BaseModel, Field
from typing import List, Optional

class Depot(BaseModel):
    id: str
    lat: float
    lng: float
    # Shift times are now primarily per-vehicle or per-depot logic, keeping here for default
    shift_start_min: int = Field(..., description="Minutes from midnight")
    shift_end_min: int

class Capacity(BaseModel):
    units: int

class BreakWindow(BaseModel):
    start_min: int
    end_min: int
    duration_min: int

class Vehicle(BaseModel):
    id: str
    capacity: Capacity
    shift_start_min: int
    shift_end_min: int
    speed_kmph: float = 30.0
    depot_id: Optional[str] = None # Assigned depot
    start_lat: Optional[float] = None # If different from main depot
    start_lng: Optional[float] = None
    end_lat: Optional[float] = None
    end_lng: Optional[float] = None
    breaks: Optional[List[BreakWindow]] = None
    # P1 Physics
    tare_weight_kg: float = 0.0
    max_weight_capacity_kg: float = 0.0
    # Costing
    fixed_cost: float = 0.0

class CylinderType(BaseModel):
    id: str
    full_weight_kg: float
    empty_weight_kg: float

class DemandItem(BaseModel):
    cylinder_type_id: str
    deliver_units: int
    pickup_units: int

class Stop(BaseModel):
    id: str
    lat: float
    lng: float
    demand_units: int 
    service_time_min: int
    time_window_start: Optional[int] = None
    time_window_end: Optional[int] = None
    depot_id: Optional[str] = None # Preferred/Required depot
    priority: int = 1
    # P1 Physics
    items: List[DemandItem] = [] 

class GlobalSettings(BaseModel):
    co2_factor_kg_per_ton_km: float = 0.1
    reload_time_min: int = 30
    enable_multi_trip: bool = False
    max_trips_per_vehicle: int = 2

class SolverParams(BaseModel):
    time_limit_seconds: int = 30
    use_matrix_cache: bool = True
    allow_unserved: bool = True
    penalty_base: int = 100000
    avg_speed_kmph: float = 30.0 # Fallback
    local_search_metaheuristic: Optional[str] = None
    span_cost_coeff: int = 0
    
    # Cost Model Params (P0)
    cost_model: str = "DISTANCE" # DISTANCE, TIME, MONEY
    fuel_cost_per_km: float = 0.0
    driver_cost_per_hour: float = 0.0
    vehicle_fixed_cost: float = 0.0
    
    # P1/P2 Settings (Optional override)
    global_settings: Optional[GlobalSettings] = None

class OptimizeRequest(BaseModel):
    depot: Depot # Main depot (legacy/fallback)
    depots: List[Depot] = [] # All available depots
    vehicles: List[Vehicle]
    stops: List[Stop]
    params: SolverParams = Field(default_factory=SolverParams)
    approach: Optional[str] = "BALANCED"
    # P1 Physics
    cylinder_types: List[CylinderType] = []

class RouteStep(BaseModel):
    stop_id: str
    arrival_time: int
    departure_time: int
    service_time: int
    waiting_time: int
    dist_from_prev_km: float = 0.0
    delivered_units: int = 0
    late_minutes: int = 0
    window_start: int = 0
    window_end: int = 0
    # P1 Physics Outputs
    onboard_mass_kg: float = 0.0
    full_units_onboard: int = 0
    empty_units_onboard: int = 0

class VehicleRoute(BaseModel):
    vehicle_id: str
    steps: List[RouteStep]
    total_dist_km: float
    total_time_min: int
    total_demand_units: int
    # P1 Physics Metrics
    total_ton_km: float = 0.0
    max_onboard_mass_kg: float = 0.0
    avg_onboard_mass_kg: float = 0.0
    co2_kg: float = 0.0 # P2

class SolutionSummary(BaseModel):
    total_dist_km: float
    total_time_min: int
    unserved_stop_ids: List[str]
    status: str
    # P2 Metric
    total_ton_km: float = 0.0
    total_co2_kg: float = 0.0

class OptimizeResponse(BaseModel):
    routes: List[VehicleRoute]
    summary: SolutionSummary
