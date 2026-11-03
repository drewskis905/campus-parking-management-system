from datetime import datetime, timedelta
from pathlib import Path
from database import database as db


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# __file__ refers to this algorithm.py file.
# .parent gives us the folder containing algorithm.py.
#
# This builds:
# your_project/database/parking_test.db
#
# Changing db.DATABASE tells your teammate's database functions
# to use the TEST database during this Python process.
#
# It does not rename a database or edit database.py.
db.DATABASE = str(
    Path(__file__).resolve().parent
    / "database"
    / "parking.db"
)


def check_database_exists():
    """
    Make sure we are reading an existing test database.

    SQLite normally creates an empty database if the file
    does not exist. This check helps catch an incorrect path.
    """
    if not Path(db.DATABASE).is_file():
        raise FileNotFoundError(
            f"Test database was not found: {db.DATABASE}"
        )


def read_rows(query): # helper function 
    """
    Execute a SELECT query against parking_test.db.

    Returns a list of tuples, with one tuple per database row.
    """
    check_database_exists()

    # david's connection function.
    conn = db.get_connection()

    try:
        cursor = conn.execute(query)
        return cursor.fetchall() # retrieves all remaining reesult rows and returns them as a python list
    finally:
        # Always close the connection, including after an error.
        conn.close()


# ============================================================
# TIME CONVERSION
# ============================================================

def _parse_time(value):
    """
    The database stores times as strings, such as "09:30".

    Our algorithm compares datetime.time objects, so this
    converts "09:30" into the equivalent of time(9, 30).
    """
    return datetime.strptime(value.strip(), "%H:%M").time()


# ============================================================
# READ PARKING PLANS AND CAPACITIES
# ============================================================

def get_all_parking_plans():
    """
    Read ALL students' parking plans from parking_test.db.

    Convert each database tuple into a dictionary so our
    algorithm can use names such as plan["arrival"].
    """
    rows = read_rows("SELECT user_id, lot, day, start_time, end_time FROM parking_plans")

    plans = []

    for user_id, lot, day, start, end in rows:
        plans.append({
            "student_id": user_id,
            "lot_id": lot,
            "day": day,
            "arrival": _parse_time(start),
            "departure": _parse_time(end)
        })

    return plans


def get_all_lot_capacities():
    """
    Read lot names and capacities from the test database.

    Example return value:
    [
        {"lot": "G3", "capacity": 223},
        ...
    ]
    """
    rows = read_rows("SELECT name, capacity FROM lots")

    lots = []
    for name, capacity in rows:
        lots.append({"lot": name, "capacity": capacity})
    
    return lots


def matches_lot_and_day(plan, lot_id, day):
    """
    Check whether a plan belongs to this lot and weekday.

    Stored day values can contain multiple days:
        "Monday/Friday"

    Splitting allows either Monday or Friday to match.

    Returns a Boolean: True or False
        * True - the plan matches both the lot and the requested day
        * False - the lot or day does not match
    """
    plan_days = [
        stored_day.strip()
        for stored_day in plan["day"].split("/")
    ]

    same_lot = plan["lot_id"] == lot_id
    same_day = day.strip() in plan_days

    if same_lot and same_day:
        return True
    else:
        return False
    

# ============================================================
# DEMAND AND SCORING
# ============================================================

def calculate_lot_demand(
    plans, lot_id, day, target, lot_capacity
):
    """
    Count students planning to be in this lot at TARGET time,
    then divide that count by the lot's capacity.

    Arrival is included; departure is excluded.

    Example:
        A plan from 09:00 to 14:00 counts at 09:00.
        It does not count at 14:00.

    This measures stored plans, not actual observed occupancy.

    This function returns a percentage
    """
    if lot_capacity is None or lot_capacity <= 0:
        raise ValueError(
            f"Invalid capacity for {lot_id}: {lot_capacity}"
        )

    # A set stores each student ID only once.
    # This prevents students from having 2 parking plan for that lot and day
    students = set()

    for plan in plans:
        if matches_lot_and_day(plan, lot_id, day):
            if plan["arrival"] <= target < plan["departure"]:
                students.add(plan["student_id"])

    # This fraction can exceed 1 if plans exceed capacity.
    return len(students) / lot_capacity


def calculate_recommendation_score(walking_minutes, predicted_demand, demand_penalty=8):
    """
    Lower scores are better.

    walking_minutes is the total walking time returned by
    walk_time.py: to the first class + back from the last class.

    The demand penalty adds 8 points when demand equals 1.
    """
    return walking_minutes + predicted_demand * demand_penalty


def calculate_lot_overlap(
    plans, lot_id, day, window_start, window_end
):
    """
    Return the portion of each matching parking plan that
    overlaps the requested visit.

    These intervals provide extra detail. Their count is NOT
    the number of students simultaneously parked throughout
    the entire visit.

    Demand for ranking is calculated separately at arrival.
    """
    overlaps = []

    for plan in plans:
        if not matches_lot_and_day(plan, lot_id, day):
            continue

        # Support checking a single instant.
        if window_start == window_end:
            if plan["arrival"] <= window_start < plan["departure"]:
                overlaps.append((window_start, window_end))

        # Otherwise, check whether two time intervals overlap.
        elif (
            plan["arrival"] < window_end
            and plan["departure"] > window_start
        ):
            overlaps.append((
                max(plan["arrival"], window_start),
                min(plan["departure"], window_end)
            ))

    return overlaps


# ============================================================
# RANK PARKING LOTS USING THE REAL ROUTING API
# ============================================================

def get_lot_recommendations(first_class_name, last_class_name, day, arrival_time, departure_time, exclude_student_id=None):
    """
    Return up to three lots, ordered from lowest to highest score.

    Sources:
    - Parking plans: parking_test.db
    - Capacities: parking_test.db
    - Coordinates: walk_time.py's existing JSON loaders
    - Walking durations: OpenRouteService API

    Returns None if score_all_lots() reports failure.
    """
    if departure_time < arrival_time:
        raise ValueError(
            "Departure must not be earlier than arrival."
        )

    # Read current parking plans from SQLite.
    plans = get_all_parking_plans()

    # Remove the logged-in student's own plans.
    # We want demand caused by OTHER students.
    if exclude_student_id is not None:
        plans = [
            plan for plan in plans
            if plan["student_id"] != exclude_student_id
        ]

    # Convert capacity records into a lookup dictionary.
    # Example: capacities["G3"] gives G3's capacity.
    capacities = {
        lot["lot"]: lot["capacity"]
        for lot in get_all_lot_capacities()
    }

    # Import the existing routing function.
    # Importing does not run walk_time.py's guarded demo.
    from walk_time import score_all_lots

    # This actually calls the routing API.
    #
    # Each returned item has:
    # "lot", "walk_to", "walk_from", and "total".
    walk_results = score_all_lots(first_class_name, last_class_name)

    if walk_results is None:
        return None

    scores = []

    for result in walk_results:
        lot_id = result["lot"]

        # Do not silently substitute a fake capacity.
        if lot_id not in capacities:
            raise ValueError(
                f"Lot {lot_id} is missing from parking_test.db"
            )

        capacity = capacities[lot_id]

        # Estimate demand at this student's planned arrival.
        demand = calculate_lot_demand(plans, lot_id, day, arrival_time, capacity)

        score = calculate_recommendation_score(result["total"], demand)

        # Recover the integer number of other planned cars.
        planned_occupied = round(demand * capacity)

        scores.append({
            "lot": lot_id,
            "score": score,
            "walk_to": result["walk_to"],
            "walk_from": result["walk_from"],
            "capacity": capacity,
            "planned_occupied": planned_occupied,

            # These two values are based on plans only.
            "remaining_spots": max(0, capacity - planned_occupied),
            "percent_full": round(demand * 100, 1)
        })

    # Sort by score: smallest first.
    scores.sort(key=lambda result: result["score"])

    # Return the best three, or fewer if fewer routes exist.
    return scores[:3]


# ============================================================
# LOOK UP ONE STUDENT'S SCHEDULE
# ============================================================

def recommend_for_student(user_id, day=None):
    """
    Retrieve this student's schedule and use it to request
    parking recommendations.

    If day is omitted, use today's weekday.

    Testing assumptions:
    - Use the first and last classes of the selected day.
    - Arrive 15 minutes before the first class.
    - Use the last class's end as the departure estimate.
    """
    check_database_exists()

    # Uses this computer's local timezone.
    # A deployed server should use America/Los_Angeles.
    now = datetime.now()

    if day is None:
        # Explicit English names match the database's day values.
        weekdays = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]
        day = weekdays[now.weekday()]

    # Calls your teammate's function.
    # Because db.DATABASE was changed above, this reads
    # schedules from parking_test.db.
    classes = db.get_user_schedule_by_day(user_id, day)

    # The current database function returns a message string
    # when there are no classes. Also handle an empty list.
    if isinstance(classes, str) or not classes:
        print(
            f"No classes found for student {user_id} on {day}."
        )
        return []

    # A schedule row contains:
    # index 0: schedule ID
    # index 1: user ID
    # index 2: class name
    # index 3: building name
    # index 4: day(s)
    # index 5: start time string
    # index 6: end time string

    # Find the earliest starting class.
    first_class = [0]

    # Find the latest ending class.
    last_class = [-1]

    first_building = classes[0][3]
    last_building = classes[-1][3]

    first_start = _parse_time(classes[0][5])
    last_end = _parse_time(classes[-1][6])

    # Convert to datetime so we can subtract 15 minutes.
    first_class_datetime = datetime.combine(
        now.date(),
        first_start
    )

    arrival_time = (
        first_class_datetime - timedelta(minutes=15)
    ).time()

    departure_time = last_end

    print(f"\nStudent ID: {user_id}")
    print(f"Selected day: {day}")
    print(
        f"First class: {classes[0][2]} "
        f"at {first_building}"
    )
    print(
        f"Last class: {classes[-1][2]} "
        f"at {last_building}"
    )
    print(
        "Estimated parking arrival: "
        f"{arrival_time.strftime('%I:%M %p')}"
    )

    return get_lot_recommendations(
        first_class_name=first_building,
        last_class_name=last_building,
        day=day,
        arrival_time=arrival_time,
        departure_time=departure_time,
        exclude_student_id=user_id
    )


# ============================================================
# LOCAL TEST: SIMULATE ONE LOGGED-IN STUDENT
# ============================================================

if __name__ == "__main__":
    check_database_exists()
    print(f"Using database: {db.DATABASE}")

    # This email belongs to a Friday student from the generated
    # batch. Change it to another email in your users table.
    email = "student0005@test.com"

    # Retrieve the actual database ID, rather than guessing it.
    user_id = db.get_user_id(email)

    if user_id is None:
        print(f"No student found with email: {email}")

    else:
        # Uses today's weekday and the REAL routing API.
        recommendations = recommend_for_student(user_id, "Monday/Wednesday/Friday")

        # To test Friday regardless of today's date, replace
        # the line above with:
        #
        # recommendations = recommend_for_student(
        #     user_id, day="Friday"
        # )

        if recommendations is None:
            print(
                "Could not calculate walking routes. "
                "Check the error printed by walk_time.py."
            )

        elif recommendations:
            print("\nTop parking recommendations:")

            for rank, result in enumerate(
                recommendations, start=1
            ):
                print(
                    f"\n{rank}. {result['lot']}\n"
                    f"   Score: {result['score']:.2f}\n"
                    f"   Walk to first class: "
                    f"{result['walk_to']:.1f} minutes\n"
                    f"   Walk back from last class: "
                    f"{result['walk_from']:.1f} minutes\n"
                    f"   Capacity: {result['capacity']}\n"
                    f"   Other planned cars at arrival: "
                    f"{result['planned_occupied']}\n"
                    f"   Percent Full at arrival: "
                    f"{result['percent_full']:.1f}%\n"
                    f"   Remaining spots at arrival: "
                    f"{result['remaining_spots']}"
                )