"""Create one parking plan per user per scheduled day.

Run after seed_database.py, with ORS_API_KEY set:
    python database/seed_parking_plan.py

Plans cover the first class's start through the last class's end.
Existing user/day plans are skipped, so an interrupted run can be resumed.
"""

import random
import sys
from datetime import datetime
from pathlib import Path

# Support direct execution and python -m database.seed_parking_plan.
# Replace the script directory so database.py does not shadow the package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ is None or __package__ == "":
    sys.path[0] = str(PROJECT_ROOT)

from database import database as db
from algorithm_version2 import check_database_exists, get_lot_recommendations


def seed_parking_plan():
    check_database_exists()

    conn = db.get_connection()
    try:
        users = conn.execute("SELECT id FROM users ORDER BY id").fetchall()
    finally:
        conn.close()

    plans_created = 0
    plans_skipped = 0
    days_without_routes = 0

    print(f"Creating parking plans for {len(users)} users...")

    for (user_id,) in users:
        # A stored plan can cover multiple days, such as Monday/Wednesday.
        existing_days = set()
        for plan in db.get_user_parking_plans(user_id):
            existing_days.update(day.strip() for day in plan[3].split("/"))

        for class_day in db.ClassDay:
            day = class_day.value
            classes = db.get_user_schedule_by_day(user_id, day)

            # The database helper returns a message string for an empty day.
            if isinstance(classes, str) or not classes:
                continue

            if day in existing_days:
                plans_skipped += 1
                continue

            # Rows: id, user_id, class_name, building, day, start, end.
            first_class = min(classes, key=lambda row: datetime.strptime(row[5], "%H:%M"))
            last_class = max(classes, key=lambda row: datetime.strptime(row[6], "%H:%M"))
            start_time = first_class[5]
            end_time = last_class[6]

            # Recalculate demand each time, including plans just inserted.
            recommendations = get_lot_recommendations(
                first_class_name=first_class[3],
                last_class_name=last_class[3],
                day=day,
                arrival_time=datetime.strptime(start_time, "%H:%M").time(),
                departure_time=datetime.strptime(end_time, "%H:%M").time(),
                exclude_student_id=user_id,
            )

            if recommendations is None:
                raise RuntimeError(
                    f"Could not get routes for user {user_id} on {day}. "
                    "Check the routing error and ORS_API_KEY, then rerun. "
                    f"{plans_created} new plans were saved before stopping."
                )

            if not recommendations:
                days_without_routes += 1
                print(f"No reachable lots for user {user_id} on {day}; skipping.")
                continue

            # Each returned option has an equal chance of being selected.
            selected_lot = random.choice(recommendations)["lot"]
            result = db.add_parking_plan(
                user_id, selected_lot, day, start_time, end_time
            )

            if not result["success"]:
                raise RuntimeError(
                    f"User {user_id}, {day}: {result['message']}"
                )

            plans_created += 1
            print(f"User {user_id}: {day} | {selected_lot} | {start_time}-{end_time}")

    print(f"New parking plans created: {plans_created}")
    print(f"Existing user/day plans skipped: {plans_skipped}")
    print(f"Days without reachable lots: {days_without_routes}")
    return plans_created


if __name__ == "__main__":
    seed_parking_plan()
