
import json
import os
from pathlib import Path

import requests


# Get our API key from the environment variables.
API_KEY = os.environ.get("ORS_API_KEY", "")

# This API gives us the actual walking path between two locations.
ORS_DIRECTIONS_URL = (
    "https://api.heigit.org/openrouteservice/v2/"
    "directions/foot-walking/geojson"
)

# Save walking routes separately so we do not affect the walking-time cache.
DATA_DIR = Path(__file__).resolve().parent.parent / "database" / "data"
ROUTES_FILE = DATA_DIR / "walking_routes.json"


def load_route_cache():
    # Load routes we have already requested so we can reuse them.
    if not ROUTES_FILE.exists():
        return {}

    with open(ROUTES_FILE, "r") as file:
        return json.load(file)


def save_route_cache(cache):
    # Save new routes so we do not have to request them again.
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROUTES_FILE, "w") as file:
        json.dump(cache, file, indent=2)


def get_walking_route(lot_name, building_name, lot_coords, building_coords):
    # Use both locations and their coordinates to identify the exact route.
    # This also prevents us from reusing an old route if coordinates change.
    cache_key = json.dumps([
        lot_name,
        building_name,
        list(lot_coords),
        list(building_coords),
    ])

    cache = load_route_cache()

    # Return the saved route if we have already requested it.
    if cache_key in cache:
        print("[walking_route] Using cached route")
        return cache[cache_key]

    if not API_KEY:
        print("[walking_route] ORS_API_KEY is missing")
        return None

    # OpenRouteService expects longitude first, then latitude.
    lot_lat, lot_lng = lot_coords
    building_lat, building_lng = building_coords

    body = {
        "coordinates": [
            [lot_lng, lot_lat],
            [building_lng, building_lat],
        ]
    }

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json",
    }

    # Request the walking path only when it is not already cached.
    try:
        response = requests.post(
            ORS_DIRECTIONS_URL,
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        feature = data["features"][0]
        summary = feature["properties"]["summary"]

        route = {
            "coordinates": feature["geometry"]["coordinates"],
            "distance_meters": summary["distance"],
            "duration_minutes": summary["duration"] / 60,
        }

    except (requests.RequestException, KeyError, IndexError, ValueError) as error:
        print(f"[walking_route] Could not get walking route: {error}")
        return None

    # Save the new route for future students who choose the same locations.
    cache[cache_key] = route
    save_route_cache(cache)

    print("[walking_route] New route saved to cache")
    return route


if __name__ == "__main__":
    from walk_time import load_lots, load_buildings

    # Load the parking lots and buildings from our project files.
    lots = load_lots()
    buildings = load_buildings()

    # Use the first parking lot and building to test the Directions API.
    lot = lots[0]
    building = buildings[0]

    # Get the actual walking route between these two locations.
    route = get_walking_route(
        lot["name"],
        building["name"],
        (lot["lat"], lot["lng"]),
        (building["lat"], building["lng"]),
    )

    # Display the walking distance and time if the request worked.
    if route is not None:
        print("Parking lot:", lot["name"])
        print("Building:", building["name"])
        print("Walking distance:", round(route["distance_meters"]), "meters")
        print("Walking time:", round(route["duration_minutes"], 1), "minutes")
        print("Route points:", len(route["coordinates"]))
    else:
        print("Could not get the walking route.")
