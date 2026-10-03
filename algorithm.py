from datetime import time, datetime, date
from walk_time import score_all_lots
# from database.database import get_all_parking_plans, get_lot

from fake_database import get_all_parking_plans, get_lot

def _parse_time(time_str):
    """Converts a stored 'HH:MM' string back into a datetime.time object."""
    return datetime.strptime(time_str, "%H:%M").time()


# gives a score to a parking lot. Each minute is a 1 point. Lowest point means
# less walk time meaning better score
def calculate_recommendation_score(walk_time, predicted_demand, demand_penalty=8):
    # the demand penalty means the "busy-ness" can add up to 8 minutes of walking
    score = walk_time + (predicted_demand * demand_penalty)
    return score


def calculate_lot_demand(lot_id, day, window_start, window_end, lot_capacity):
    """
    Estimates how busy a lot will be during the given window.

    - For "will I find a spot at arrival": pass window_start == window_end.
    - For "how busy across my whole visit": pass real arrival and departure.

    Returns (demand, overlaps) - demand is a 0-1 fraction of capacity,
    overlaps is a list of (overlap_start, overlap_end) for each student
    whose stored plan overlaps this window.
    """
    assumption_count = 0
    overlaps = []
    rows = get_all_parking_plans()  # (user_id, lot_id, day, arrival_time, departure_time)

    for row in rows:
        _, row_lot_id, row_day, row_arrival_str, row_departure_str = row
        if row_lot_id == lot_id and row_day == day:
            row_arrival = _parse_time(row_arrival_str)
            row_departure = _parse_time(row_departure_str)

            if row_arrival < window_end and row_departure > window_start:
                assumption_count += 1

                overlap_start = max(row_arrival, window_start)
                overlap_end = min(row_departure, window_end)
                overlaps.append((overlap_start, overlap_end))

    demand = assumption_count / lot_capacity
    return demand, overlaps


def classify_demand(demand):
    if demand >= 0 and demand <= 0.33:
        return "Low"
    elif demand > 0.33 and demand <= 0.66:
        return "Moderate"
    else:
        return "High"

def summarize_overlaps(overlaps):
    #needed cleaner print
    if not overlaps:
        return "Likely empty during your visit"
 
    if len(overlaps) == 1:
        start, end = overlaps[0]
        return f"Busy {start.strftime('%I:%M %p')}-{end.strftime('%I:%M %p')} (1 other student)"
 
    return f"Busy at times during your visit ({len(overlaps)} other students)"

def get_all_lot_capacities():
    """
    Returns every lot's name and capacity, with no walk-time or demand
    calculation involved - just a plain list, for a "browse all lots"
    view rather than a personalized recommendation.
 
    Returns a list of dicts: [{"lot": "G3", "capacity": 223}, ...]
    """
    lots = load_lots()  # from walk_time.py - reads lots.json directly
    return [{"lot": lot["name"], "capacity": lot["capacity"]} for lot in lots]




def get_lot_recommendations(first_class_name, last_class_name, day, arrival_time, departure_time):
    """
    Given a student's first/last class building names and their real
    arrival/departure times, returns the TOP 3 lots (best first), each
    with its score, walk times, capacity, percent full, and overlap detail.
    """
    results = score_all_lots(first_class_name, last_class_name)
    if results is None:
        return None
 
    scores = []
    for r in results:
        lot_id = r["lot"]
        walking_minutes = r["total"]
 
        lot_info = get_lot(lot_id)  # (id, name, lat, lng, capacity)
        real_capacity = lot_info[4] if lot_info else 10
 
        curr_demand, overlaps = calculate_lot_demand(
            lot_id, day, arrival_time, departure_time, real_capacity
        )
        curr_score = calculate_recommendation_score(walking_minutes, curr_demand)
 
        percent_full = round(curr_demand * 100, 1)
        estimated_occupied = round(curr_demand * real_capacity)
        remaining_spots = real_capacity - estimated_occupied

        scores.append({
            "lot": lot_id,
            "score": curr_score,
            "walk_to": r["walk_to"],
            "walk_from": r["walk_from"],
            "remaining_spots": remaining_spots,
            "percent_full": percent_full,
            "overlaps": overlaps,
            "summary": summarize_overlaps(overlaps)
        })
 
    scores.sort(key=lambda s: s["score"])
    return scores[:3]  # only the top 3




#  MANUAL TEST (only runs if you execute this file directly)


if __name__ == "__main__":
    test_scores = get_lot_recommendations(
        "Fine Arts 3 (FA3)", "College of Liberal Arts (CLA)",
        day="Monday",
        arrival_time=time(8, 0),
        departure_time=time(14, 0)
    )
 
    if test_scores is None:
        print("Something went wrong - check the error message above.")
    else:
        print("Top 3 recommended lots:\n")
        for s in test_scores:
                        print(f"{s['lot']}: score={s['score']:.1f}, "
                  f"walk to class={s['walk_to']:.1f} min, "
                  f"walk back={s['walk_from']:.1f} min, "
                  f"{s['remaining_spots']} spots available, "
                  f"{s['percent_full']}% full - {s['summary']}")
