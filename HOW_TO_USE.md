# Saral Ravaana: LPG Logistics - User Guide

## Overview
Saral Ravaana is an intelligent routing platform designed for LPG distribution. It optimizes vehicle routes to minimize cost, distance, and CO₂ emissions ("Green VRP").

## Quick Start

### 1. Managing Global Fleet
1. Navigate to **Fleet** from the header.
2. Click **+ Add New Vehicle**.
3. Define the vehicle profile (Capacity, Speed, Driver Contact).
4. Use these vehicles across multiple Route Plans without re-entering data.
   - **Soft Delete**: Deleting a vehicle archives it (sets `isActive=false`) so historical plans remain intact.

### 2. Creating a Route Plan
1. Navigate to **Route Plans**.
2. Click **+ New Plan**.
3. Select a **Depot** and **Date**.
4. **Import Vehicles**: Click "Import from Fleet" to pull in your active trucks.
5. **Add Stops**: Upload stops or add manually.
   - **Customers**: New stops are automatically added to the Global Customer Database.

### 3. Optimization
1. Once data is ready, click **Optimize Route**.
2. **Select Mode**:
   - **Fast**: Quickest result (Savings algorithm).
   - **Balanced**: Best trade-off (Metaheuristic).
   - **Precise**: Deep search (Guided Local Search).
3. Wait for the status to change from **Optimizing** to **Optimized**.

### 4. Viewing Results & Export
1. Click **Results**.
2. **Map**: View color-coded routes. Toggle "Maximize" (⤡) for full screen.
3. **Metrics**: Review Total Distance, Time, and CO₂.
4. **Export**: Click **📊 Download Excel** to get a multi-sheet report (Summary, Customers, Fleet) for dispatch.

---

## Features

### 📍 Customers Module
- **Directory**: View all unique customers served.
- **Copy Coordinates**: One-click copy for Google Maps usage.
- **Location Sync**: Customer data is de-duplicated based on Name + Coordinates.

### 🚛 Global Fleet
- **Centralized Database**: Manage your assets in one place.
- **Import Logic**: Only "Active" vehicles are shown during plan creation.

### 📦 Bulk Actions
- **Delete**: Select multiple plans on the dashboard to delete in bulk.
- **Compare**: Select > 1 plan to view side-by-side KPI comparison (Distance, Cost, Unserved, CO₂).

---

## Technical Details

### Green VRP & CO₂ Analytics
- **Baseline**: Standard Distance Minimization.
- **Green Route**: Optimized for `CO₂` (Ton-KM).
- **Savings**: `(Baseline - Green)` %.
- **Emission Factor**: Default 0.1 kg CO₂ per Ton-KM.

### Multi-Trip Logic
If enabled, a single vehicle can return to the depot to reload.
- **Trip 1**: Depot -> Customers -> Depot.
- **Trip 2**: Depot (Reload) -> Customers -> Depot.
Results show `V1` and `V1#trip2`.

### Troubleshooting
- **Unserved Stops?**
  - Check Demand > Vehicle Capacity.
  - Check Time Windows (is the stop open when the truck arrives?).
  - Check Shift Time (is the driver's day long enough?).
- **Optimization Failed?**
  - Usually means a hard constraint violation (e.g., impossible time windows).
  - Try relaxing constraints or adding more vehicles.

---

## Smoke Test Procedure
To verify system health, run the following command in the terminal:
```bash
python tests/verify_all.py
```
**Expected Output:**
- `verify_p0`: PASS
- `verify_p1_p2`: PASS
- `verify_p3`: PASS
- `certify_phase0`: PASS

**UI Manual Check:**
1. Create Plan -> Add 1 Vehicle, 2 Stops.
2. Optimize (Balanced).
3. Verify Map renders routes.
4. Verify "Download Excel" produces a file.
