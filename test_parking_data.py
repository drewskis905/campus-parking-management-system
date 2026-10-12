from datetime import datetime
from pathlib import Path
import sqlite3

from database import database as db


# Only use the separate test database.
TEST_DATABASE = (
    Path(__file__).resolve().parent
    / "database"
    / "parking_test.db"
)

TEST_DAY = "Monday"

# Exact lot name used in your team's database.
LOT_NAME = "Pyramid Parking Structure"

# Each class lasts exactly three hours.
# These building names match your team's buildings.json.
CLASSES = [
    (
        "TEST 101",
        "Engineering/Computer Sciences (ECS)",
        "09:00",
        "12:00"
    ),
    (
        "TEST 102",
        "College of Business (COB)",
        "13:00",
        "16:00"
    )
]

# Students remain parked through both classes and the lunch gap.
PARKING_ARRIVAL = "08:45"
PARKING_DEPARTURE = "16:15"


def check_result(result):
    """Stop if a database insertion fails."""
    if not result["success"]:
        raise RuntimeError(result["message"])


def backup_test_database():
    """Preserve the existing test database before replacing records."""
    if not TEST_DATABASE.is_file():
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    backup_path = TEST_DATABASE.with_name(
        f"parking_test_backup_{timestamp}.db"
    )

    source = sqlite3.connect(str(TEST_DATABASE))
    destination = sqlite3.connect(str(backup_path))

    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    print(f"Previous test database backed up to: {backup_path}")


def main():
    # Redirect your teammate's database functions to the test file.
    db.DATABASE = str(TEST_DATABASE)

    backup_test_database()

    # Create any missing tables.
    # Load lot capacities and building coordinates from JSON.
    db.create_tables()
    db.load_lots()
    db.load_buildings()

    # Verify the reference records exist before clearing test users.
    if db.get_lot(LOT_NAME) is None:
        raise ValueError(f"Lot not found: {LOT_NAME}")

    for class_name, building, start, end in CLASSES:
        if db.get_building(building) is None:
            raise ValueError(f"Building not found: {building}")

    # Remove previous student test records.
    # Keep the lots and buildings tables populated.
    conn = db.get_connection()

    try:
        with conn:
            conn.execute("DELETE FROM parking_plans")
            conn.execute("DELETE FROM schedules")
            conn.execute("DELETE FROM users")
    finally:
        conn.close()

    # range(1, 101) produces numbers 1 through 100.
    for number in range(1, 101):
        # :03d produces 001, 002, ..., 100.
        email = f"pyramid.student{number:03d}@example.test"

        # Create one student account.
        check_result(
            db.add_user(
                f"Student{number:03d}",
                "Test",
                email,
                "FakeTestPassword123!"
            )
        )

        # SQLite generates the ID.
        # Existing ID counters may continue after deleting old users.
        user_id = db.get_user_id(email)

        # Add both classes for this student.
        for class_name, building, start, end in CLASSES:
            check_result(
                db.add_schedule(
                    user_id,
                    class_name,
                    building,
                    TEST_DAY,
                    start,
                    end
                )
            )

        # Add ONE parking plan covering the entire visit.
        check_result(
            db.add_parking_plan(
                user_id,
                LOT_NAME,
                TEST_DAY,
                PARKING_ARRIVAL,
                PARKING_DEPARTURE
            )
        )

    # Read back the counts to confirm what was actually saved.
    conn = db.get_connection()

    try:
        users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        schedules = conn.execute(
            "SELECT COUNT(*) FROM schedules"
        ).fetchone()[0]

        plans = conn.execute(
            "SELECT COUNT(*) FROM parking_plans"
        ).fetchone()[0]
    finally:
        conn.close()

    print(f"\nDatabase: {TEST_DATABASE}")
    print(f"Students: {users}")
    print(f"Classes: {schedules}")
    print(f"Parking plans: {plans}")
    print(f"Day: {TEST_DAY}")
    print(f"Lot: {LOT_NAME}")
    print("Test email: pyramid.student001@example.test")


# Importing this file will not reset the database.
# Seeding happens only when you execute this script directly.
if __name__ == "__main__":
    main()