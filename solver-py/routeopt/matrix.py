import math
from typing import List, Tuple
from .models import Stop, Depot # Should match your models

# Haversine implementation for MVP v1
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  # Earth radius in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d

def compute_time_matrix(locations: List[Tuple[float, float]], speed_kmh: float = 30.0) -> List[List[int]]:
    """
    Returns time matrix in minutes.
    locations[0] should be depot if implied, but here we pass all points.
    """
    size = len(locations)
    matrix = [[0] * size for _ in range(size)]
    
    for i in range(size):
        for j in range(size):
            if i == j:
                matrix[i][j] = 0
            else:
                dist = haversine_distance(locations[i][0], locations[i][1], 
                                          locations[j][0], locations[j][1])
                # Time = (dist / speed) * 60
                time_min = int(round((dist / speed_kmh) * 60))
                matrix[i][j] = time_min
    return matrix

def compute_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
    """
    Returns distance matrix in kilometers.
    """
    size = len(locations)
    matrix = [[0.0] * size for _ in range(size)]
    
    for i in range(size):
        for j in range(size):
            if i == j:
                matrix[i][j] = 0.0
            else:
                dist = haversine_distance(locations[i][0], locations[i][1], 
                                          locations[j][0], locations[j][1])
                matrix[i][j] = dist
    return matrix
