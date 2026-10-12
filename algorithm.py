from datetime import time, datetime, date
from database.database import get_all
from walk_time import load_lots
from walk_time import score_all_lots
from pathlib import Path
from database import database as db

db.DATABASE = str(
    Path(__file__).resolve().parent / "database" / "parking_test.db"
)

# the records of class schedule of each student stored as a list of dictionaries
schedules = [
    {"student_id": 1, "arrival": time(9, 0), "departure": time(14,0)},   # 9:00am - 2:00pm
    {"student_id": 2, "arrival": time(9, 0), "departure": time(14, 0)},  # 9:00am - 2:00pm
    {"student_id": 3, "arrival": time(9, 0), "departure": time(14, 0)},  # 9:00am - 2:00pm
    {"student_id": 4, "arrival": time(9, 0), "departure": time(14, 0)},  # 9:00am - 2:00pm
    {"student_id": 5, "arrival": time(9, 0), "departure": time(14, 0)},  # 9:00am - 2:00pm
    {"student_id": 6, "arrival": time(9, 0), "departure": time(14, 0)},  # 9:00am - 2:00pm
    {"student_id": 7, "arrival": time(9, 0), "departure": time(14, 0)},  # 9:00am - 2:00pm
    {"student_id": 8, "arrival": time(16, 0), "departure": time(18, 0)}, # 4:00pm - 6:00pm
    {"student_id": 9, "arrival": time(16, 0), "departure": time(18, 0)}, # 4:00pm - 6:00pm
    {"student_id": 10, "arrival": time(16, 0), "departure": time(18, 0)},# 4:00pm - 6:00pm
]

# the records of each parking plan that users planned to do 
parking_plan = [
    {
        "student_id": 1,
        "day": "Monday",
        "lot_id": "G3",
        "arrival": time(9, 0),
        "departure": time(14,0)
    },
    {
        "student_id": 2,
        "day": "Monday",
        "lot_id": "G3",
        "arrival": time(9, 0),
        "departure": time(14,0)
    },
    {
        "student_id": 3,
        "day": "Monday",
        "lot_id": "G3",
        "arrival": time(16, 0),
        "departure": time(18,0)
    },
    {
        "student_id": 4,
        "day": "Monday",
        "lot_id": "G4",
        "arrival": time(16, 0),
        "departure": time(18,0)
    },
    {
        "student_id": 7,
        "day": "Monday",
        "lot_id": "G4",
        "arrival": time(8, 0),
        "departure": time(12, 0)
    },
    {
        "student_id": 8,
        "day": "Monday",
        "lot_id": "G4",
        "arrival": time(9, 30),
        "departure": time(15, 0)
    },
    {
        "student_id": 9,
        "day": "Monday",
        "lot_id": "G4",
        "arrival": time(11, 0),
        "departure": time(14, 0)
    }
]


# These are just mock walk times to test
walk_times = {
    "G3": 5,
    "G4": 8
}

# gives me a list of tuples of (lot name, capaicty), called from database
lots = get_all("lots", "name", "capacity")

def _parse_time(time_str):
    """Converts a stored 'HH:MM' string back into a datetime.time object."""
    return datetime.strptime(time_str, "%H:%M").time()

# gives a score to a parking lot. Each minute is a 1 point. Lowest point means less walk time meaning better score
def calculate_recommendation_score(walk_time, predicted_demand, demand_penalty = 8): # the demand penatly means the "busy-ness" can add up to 8 minutes of walking
    score = walk_time + (predicted_demand * demand_penalty)
    return score

# Responsible for seeing what percentage of students are going to pack that this parking lot/structure
def calculate_lot_demand(plans, lot_id, day, target, lot_capacity):
    assumption_count = 0

    for plan in plans:
        if lot_id == plan["lot_id"] and day == plan["day"]:
            if plan["arrival"] <= target < plan["departure"]:
                assumption_count += 1

    return assumption_count / lot_capacity

def get_all_parking_plans():
    conn = db.get_connection()

    try:
        cursor = conn.execute("""
            SELECT user_id, lot, day, start_time, end_time
            FROM parking_plans
        """)

        return cursor.fetchall()
    finally:
        conn.close()

def calculate_lot_ovelap(lot_id, day, window_start, window_end):
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

    return overlaps

# Responsible for seeing what percentage of students are expected to be parked at this time
def calculate_schedule_demand(schedules, time):
    assumption_count = 0 # counts the number of students planned to park

    for student in schedules: # loops through each student in schedules
        if student["arrival"] <= time < student["departure"]: # checks if the time is between currents students arrival and departure, 
            assumption_count += 1

    return assumption_count / len(schedules)

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
 
        curr_demand = calculate_lot_demand(
            parking_plan, lot_id, day, arrival_time, real_capacity
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
    
        })
 
    scores.sort(key=lambda s: s["score"])
    return scores[:3]  # only the top 3

target_time = time(10, 0)
demand = calculate_schedule_demand(schedules, target_time)
# strftime is function to conver dat and time object into a readable string
# %I — hour using the 12-hour clock
# %M — minutes
# %p — AM or PM
print(f"Estimate {target_time.strftime("%I:%M %p")} to be {classify_demand(demand)}")

lot_demand = calculate_lot_demand(parking_plan, "G3", "Monday", target_time, 5)
print(f"Estimate {target_time.strftime("%I:%M %p")} at lot G3 on a Monday to be {classify_demand(lot_demand)}")

#block of code here is to calculate score for lot G3 and G4
scores = []
for lot_id, walking_minutes in walk_times.items():
    curr_demand = calculate_lot_demand(parking_plan, lot_id, "Monday", target_time, 10)
    curr_score = calculate_recommendation_score(walking_minutes, curr_demand)
    scores.append((lot_id, curr_score))
print(scores)
