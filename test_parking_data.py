from pathlib import Path
from datetime import time
from database import database as db

# redirects davids function to a separate database called parking_test.db containing only test data called parking_test.db 
db.DATABASE = str(Path(__file__).resolve().parent / "database" / "parking_test.db")

# create the tables and populate the lot/building reference data
db.create_tables()
db.load_lots()
db.load_buildings()

def check_result(result):
    if not result["success"]:
        raise RuntimeError(result["message"])


# Choose an existing building from the database.
building = db.get_all("buildings", "name")[0]

# first name, email, class start, class end, parking arrival, departure
fake_students = [
    ("Alex", "alex@example.test", "09:00", "10:15", "08:45", "14:00"),
    ("Sam", "sam@example.test", "09:00", "10:15", "08:45", "14:00"),
    ("Jamie", "jamie@example.test", "16:00", "17:15", "15:45", "18:00"),
]

student_ids = []

for first_name, email, class_start, class_end, arrival, departure in fake_students:
    user_id = db.get_user_id(email)

    # Avoid creating the same student again when rerunning.
    if user_id is None:
        result = db.add_user(
            first_name,
            "Test",
            email,
            "FakeTestPassword123!"
        )
        check_result(result)

        user_id = db.get_user_id(email)

    student_ids.append(user_id)

    # Add one mock class if it is not already stored.
    existing_classes = db.get_user_schedule(user_id)

    if not any(row[2] == "TEST 101" for row in existing_classes):
        result = db.add_schedule(
            user_id,
            "TEST 101",
            building,
            "Monday",
            class_start,
            class_end
        )
        check_result(result)

    # Add the parking plan only if this exact plan is not stored.
    existing_plans = db.get_user_parking_plans(user_id)
    expected_plan = ("G3", "Monday", arrival, departure)

    if not any(row[2:] == expected_plan for row in existing_plans):
        result = db.add_parking_plan(
            user_id,
            "G3",
            "Monday",
            arrival,
            departure
        )
        check_result(result)

print("Fake students, schedules, and parking plans are ready.")