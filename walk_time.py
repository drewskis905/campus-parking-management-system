"""
Handles all walk-time calculation for the CSULB parking app.
Uses OpenRouteService (via the HeiGIT API)

Usage:
    from Walk_time import score_all_lots
"""

import json
import os
import requests


# My API key for OpenRouteService (ORS) - you should replace this with your own key.
API_KEY =  os.getenv("ORS_API_KEY") # <-- put your real OpenRouteService key here
ORS_MATRIX_URL = "https://api.heigit.org/openrouteservice/v2/matrix/foot-walking"

LOTS_FILE = "lots.json" # our lots file
BUILDINGS_FILE = "buildings.json" # our buildings file



def load_lots(path=LOTS_FILE):
    #Loads the list of parking lots from lots.json.
    with open(path, "r") as f:
        return json.load(f)


def load_buildings(path=BUILDINGS_FILE):
    #Loads the list of campus buildings from buildings.json.
    with open(path, "r") as f:
        return json.load(f)


def find_building(name, buildings):
    """
    Looks up a building by exact name match.
    Returns the building dict, or None if not found.
    """
    for b in buildings:
        if b["name"] == name:
            return b
    return None


def find_lot(name, lots):
    """
    Looks up a lot by exact name match.
    this might be a problem later if we do not have the exact name for the lot.
    """
    for l in lots:
        if l["name"] == name:
            return l
    return None



# WALK TIME CALCULATION (OpenRouteService Matrix API)


def get_walk_time_matrix(origins, destinations):
    """
    Calls the ORS Matrix API to get walk times (in minutes) between
    every origin and every destination, in a single request.

    origins / destinations: lists of (lat, lng) tuples.

    Returns a 2D list: durations[i][j] = minutes from origins[i] to destinations[j].
    Returns None if the API call fails.
    """
    headers = { #API is expecting an Authorization header with the API key and JSON content type
        "Authorization": API_KEY,
        "Content-Type": "application/json" #content type we are feeding it
    }

    all_coords = origins + destinations #groups all 17 parking lots, + the building
    #origins = [(lat1, lng1), (lat2, lng2), ...]  # list of origin coordinates
    #destinations = [(latx, lngx)]  # list of destination coordinates
    coords_lnglat = [[lng, lat] for lat, lng in all_coords]  # ORS wants [lng, lat]
    #so its [lng, lat] for every coordinate (list of tuples) the loop is going through each tuple and flips them because for some reason the api wants long first
    body = {
        "locations": coords_lnglat,
        "sources": list(range(len(origins))),
        "destinations": list(range(len(origins), len(origins) + len(destinations))),
        "metrics": ["duration"]
    }

    response = requests.post(ORS_MATRIX_URL, json=body, headers=headers)

    if response.status_code != 200:
        print(f"[walk_time] API error: {response.status_code} - {response.text}")
        return None

    data = response.json()
    durations_seconds = data["durations"]
    durations_minutes = [
        [d / 60 if d is not None else None for d in row]
        for row in durations_seconds
    ]
    return durations_minutes


# ---------------------------------------------------------------------
# MAIN SCORING FUNCTION
# ---------------------------------------------------------------------

def score_all_lots(first_class_name, last_class_name):
    """
    Given the name of a student's first-class building and last-class
    building, scores every parking lot by total walk time and returns
    a ranked list (best/shortest total walk first).

    Returns a list of dicts:
        [{"lot": "G2", "walk_to": 6.3, "walk_from": 5.1, "total": 11.4}, ...]

    Returns None if either building name isn't found, or if the API call fails.
    """
    lots = load_lots()
    buildings = load_buildings()

    first_class = find_building(first_class_name, buildings)
    last_class = find_building(last_class_name, buildings)

    if first_class is None:
        print(f"[walk_time] Building not found: '{first_class_name}'")
        return None
    if last_class is None:
        print(f"[walk_time] Building not found: '{last_class_name}'")
        return None

    lot_coords = [(lot["lat"], lot["lng"]) for lot in lots]

    # One matrix call: every lot -> first class building
    to_first_class = get_walk_time_matrix(
        lot_coords, [(first_class["lat"], first_class["lng"])]
    )
    if to_first_class is None:
        return None

    # One matrix call: last class building -> every lot
    from_last_class = get_walk_time_matrix(
        [(last_class["lat"], last_class["lng"])], lot_coords
    )
    if from_last_class is None:
        return None

    results = []
    for i, lot in enumerate(lots):
        walk_to = to_first_class[i][0]
        walk_from = from_last_class[0][i]

        if walk_to is None or walk_from is None:
            # ORS couldn't find a route for this lot - skip it rather than crash
            continue

        total = walk_to + walk_from
        results.append({
            "lot": lot["name"],
            "walk_to": walk_to,
            "walk_from": walk_from,
            "total": total
        })

    results.sort(key=lambda r: r["total"])
    return results


# Quick test but this will only work with this hard coded for now

if __name__ == "__main__":
    results = score_all_lots("Fine Arts 3 (FA3)", "College of Liberal Arts (CLA)")

    if results is None:
        print("Something went wrong - check the error message above.")
    else:
        print("All lots, ranked by total walk time:\n")
        for r in results:
            print(f"{r['lot']}: to class = {r['walk_to']:.1f} min, "
                  f"from class = {r['walk_from']:.1f} min, "
                  f"total = {r['total']:.1f} min")

        print("\nTop 3:")
        for r in results[:3]:
            print(f"{r['lot']}: {r['total']:.1f} min total")
