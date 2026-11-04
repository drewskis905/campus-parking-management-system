"""
Handles all walk-time calculation for the CSULB parking app.
Uses OpenRouteService (via the HeiGIT API)

Usage:
    from Walk_time import score_all_lots
"""

import json
import os
import time
import requests
from pathlib import Path

# OpenRouteService (ORS) API key, read from the ORS_API_KEY environment variable.
API_KEY = os.environ.get("ORS_API_KEY", "")
ORS_MATRIX_URL = "https://api.heigit.org/openrouteservice/v2/matrix/foot-walking"

DATA_DIR = Path(__file__).resolve().parent.parent / "database" / "data"
LOTS_FILE = str(DATA_DIR / "lots.json")
BUILDINGS_FILE = str(DATA_DIR / "buildings.json")

# Walk times between lots and buildings never change, so each building is fetched
# from ORS once and saved here. The Matrix API allows 40 requests/min, 500/day.
WALK_TIMES_FILE = str(DATA_DIR / "walk_times.json")
SECONDS_BETWEEN_REQUESTS = 1.6  # keeps us under 40 requests per minute


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

    # Retry dropped connections and rate limits (429) a few times before giving up.
    response = None
    for attempt in range(5):
        try:
            response = requests.post(ORS_MATRIX_URL, json=body, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"[walk_time] Connection error (attempt {attempt + 1}/5): {e}")
            time.sleep(2 ** attempt)
            continue
        if response.status_code == 429:
            print(f"[walk_time] Rate limited (attempt {attempt + 1}/5), waiting...")
            time.sleep(2 ** attempt * 5)
            continue
        break

    if response is None:
        print("[walk_time] API error: could not connect after 5 attempts")
        return None

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
# WALK TIME CACHE
# ---------------------------------------------------------------------

def load_walk_time_cache(path=WALK_TIMES_FILE):
    """
    Loads saved walk times, shaped like:
        {"Building Name": {"to": {"G1": 6.3, ...}, "from": {"G1": 5.1, ...}}}
    "to" is lot -> building, "from" is building -> lot. None means no route.
    """
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_walk_time_cache(cache, path=WALK_TIMES_FILE):
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


_last_request_time = 0.0


def get_building_walk_times(building, lots, cache):
    """
    Returns {"to": {...}, "from": {...}} walk times for one building.
    Uses the cache when every lot is present; otherwise makes 2 ORS calls
    (throttled) and saves the result. Returns None if the API call fails.
    """
    global _last_request_time

    entry = cache.get(building["name"])
    lot_names = [lot["name"] for lot in lots]
    if entry and all(name in entry["to"] and name in entry["from"] for name in lot_names):
        return entry

    lot_coords = [(lot["lat"], lot["lng"]) for lot in lots]
    building_coords = [(building["lat"], building["lng"])]

    # Space out requests so we stay under the per-minute limit.
    wait = SECONDS_BETWEEN_REQUESTS - (time.time() - _last_request_time)
    if wait > 0:
        time.sleep(wait)
    # One matrix call: every lot -> building
    to_building = get_walk_time_matrix(lot_coords, building_coords)
    _last_request_time = time.time()
    if to_building is None:
        return None

    time.sleep(SECONDS_BETWEEN_REQUESTS)
    # One matrix call: building -> every lot
    from_building = get_walk_time_matrix(building_coords, lot_coords)
    _last_request_time = time.time()
    if from_building is None:
        return None

    entry = {
        "to": {name: to_building[i][0] for i, name in enumerate(lot_names)},
        "from": {name: from_building[0][i] for i, name in enumerate(lot_names)},
    }
    cache[building["name"]] = entry
    save_walk_time_cache(cache)
    return entry


def build_walk_time_cache():
    """
    Fetches walk times for every uncached building in just 2 ORS calls:
    all lots -> all buildings, then all buildings -> all lots.
    """
    lots = load_lots()
    buildings = load_buildings()
    cache = load_walk_time_cache()

    missing = [b for b in buildings if b["name"] not in cache]
    if not missing:
        print(f"All {len(buildings)} buildings already cached.")
        return True
    print(f"Fetching walk times for {len(missing)} buildings (2 API calls)...")

    lot_names = [lot["name"] for lot in lots]
    lot_coords = [(lot["lat"], lot["lng"]) for lot in lots]
    building_coords = [(b["lat"], b["lng"]) for b in missing]

    # One matrix call: every lot -> every building
    to_buildings = get_walk_time_matrix(lot_coords, building_coords)
    if to_buildings is None:
        return False

    time.sleep(SECONDS_BETWEEN_REQUESTS)
    # One matrix call: every building -> every lot
    from_buildings = get_walk_time_matrix(building_coords, lot_coords)
    if from_buildings is None:
        return False

    for j, building in enumerate(missing):
        cache[building["name"]] = {
            "to": {name: to_buildings[i][j] for i, name in enumerate(lot_names)},
            "from": {name: from_buildings[j][i] for i, name in enumerate(lot_names)},
        }
    save_walk_time_cache(cache)
    print(f"Done. Walk times for {len(cache)} buildings saved to {WALK_TIMES_FILE}")
    return True


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

    # Walk times come from the cache; ORS is only called for uncached buildings.
    cache = load_walk_time_cache()

    first_times = get_building_walk_times(first_class, lots, cache)
    if first_times is None:
        return None

    last_times = get_building_walk_times(last_class, lots, cache)
    if last_times is None:
        return None

    results = []
    for lot in lots:
        walk_to = first_times["to"][lot["name"]]
        walk_from = last_times["from"][lot["name"]]

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
    import sys
    if "--build-cache" in sys.argv:
        sys.exit(0 if build_walk_time_cache() else 1)

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
