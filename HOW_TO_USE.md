# Saral Ravaana: LPG Logistics - User Guide

## Overview
Saral Ravaana is an intelligent routing platform designed for LPG distribution. It optimizes vehicle routes to minimize cost, distance, and CO₂ emissions ("Green VRP").

## Quick Start

### 1. Creating a Route Plan
1. Navigate to **Route Plans** from the header.
2. Click **+ New Plan**.
3. Enter a name (e.g., "Morning Shift - Bangalore South").
4. Select a Depot.
5. Provide the Date.

### 2. Adding Data (Stops & Vehicles)
- **Stops**: Upload a list of customers or add them manually. Each stop needs:
  - Location (Lat/Lng) - Auto-geocoded if address provided (Feature pending).
  - Demand (Items to deliver/pickup).
  - Time Window (Optional).
- **Vehicles**: Assign vehicles to the plan.
  - Set Capacity (Cylinders).
  - Set Shift Timing (Start/End).
  - (Advanced) Enable **Multi-Trip** if vehicles need to reload.

### Route Plans Status
- **Draft**: Initial state. You can edit vehicles and stops.
- **Optimizing**: Solver is running. Please wait (5-10s).
- **Optimized**: Route is ready. Results are frozen.
- **Failed**: Optimization could not satisfy constraints (e.g. impossible time windows).

### Green VRP & CO₂ Analytics
- **Baseline**: We use the **Standard Distance Minimization** as the baseline. 
- **Green Route**: The route optimized for `CO₂` (Ton-KM).
- **Savings**: `(Baseline CO₂ - Green CO₂)` shown as percentage.
- **Emission Factor**: Default 0.1 kg CO₂ per Ton-KM.
- **Metrics**:
    - **Onboard Mass**: Total weight carried over distance.
    - **Ton-KM**: Mass * Distance.
    - **CO₂**: Carbon impact of the route.

### Interpreting Result Analytics
- **Arrival**: Time vehicle arrives at location.
- **Wait**: Time spent waiting for window to open.
- **Departure**: Arrival + Wait + Service.
- **Late Minutes**: Time arrived after window close.
- **Unserved**: Stops dropped due to constraints/penalty.

### Multi-Trip Logic
If enabled, a single vehicle can return to the depot to reload.
- **Trip 1**: Depot -> Customers -> Depot.
- **Trip 2**: Depot (Reload) -> Customers -> Depot.
In the results, these appear as `V1` and `V1#trip2`. Correct interpretation: It's the same physical truck.

### Expectations
| Page | What you expect to see | Action if blank |
| :--- | :--- | :--- |
| **Route Plans** | List of plans created. | Click "+ New Plan" |
| **Plan Details** | Input Steps (Vehicles, Stops) | Add Data manually |
| **Optimization** | Status "Optimizing" then "Optimized" | Refresh if stuck > 1 min |
| **Results** | Map with routes, Metrics on right | Check "Unserved" tab if Map empty |
| **Sustainability** | CO₂ Savings Badge | Run "Green" mode to compare |

## Troubleshooting
- **Unserved Stops?**
  - Check if Demand > Vehicle Capacity.
  - Check Time Windows (is the stop open when the truck arrives?).
  - Check Shift Time (is the driver's day long enough?).
- **Optimization Failed?**
  - Usually means a hard constraint violation (e.g., impossible time windows). Try relaxing constraints.

## Contact & Support
- **Phone**: Click the "Contact" button in the header.
- **WhatsApp**: Direct support available via the header link.
