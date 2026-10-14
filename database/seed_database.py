import random
import json
import os
from database import *

# Number of fake students to generate
NUM_STUDENTS = 1000

# Password used for all test accounts
TEST_PASSWORD = "ParkingTest123!"

# Find the buildings JSON file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILDINGS_FILE = os.path.join(BASE_DIR, "data", "buildings.json")

# Load the buildings
with open(BUILDINGS_FILE, "r") as file:
    buildings_data = json.load(file)

building_names = [building["name"] for building in buildings_data]

# Buildings where students can have classes
classroom_buildings = [
    "Engineering/Computer Sciences (ECS)",
    "Engineering 2",
    "Engineering 3",
    "Engineering 4 (EN4)",
    "Vivian Engineering Center (VEC)",
    "Hall of Science (HSCI)",
    "Molecular & Life Sciences Center (MLSC)",
    "Liberal Arts 1 (LA1)",
    "Liberal Arts 2 (LA2)",
    "Liberal Arts 3 (LA3)",
    "Liberal Arts 4 (LA4)",
    "Liberal Arts 5 (LA5)",
    "College of Business (COB)",
    "Psychology (PSY)",
    "Kinesiology (KIN)",
    "Fine Arts 1 (FA1)",
    "Fine Arts 2 (FA2)",
    "Language Arts Building (LAB)",
    "Health & Human Services 1 Classrooms (HHS1)"
]

# Only use buildings that actually exist in the JSON file
classroom_buildings = [
    building for building in classroom_buildings
    if building in building_names
]

# Example classes for the fake schedules
class_names = [
    "CECS 100", "CECS 105", "CECS 174", "CECS 225",
    "CECS 228", "CECS 229", "CECS 262", "CECS 274",
    "CECS 277", "CECS 282", "CECS 323", "CECS 326",
    "CECS 327", "CECS 328", "CECS 329", "CECS 342",
    "CECS 343", "CECS 346", "CECS 378", "CECS 381",
    "CECS 424", "CECS 428", "CECS 443", "CECS 448",
    "CECS 451", "CECS 453", "CECS 456", "CECS 478",

    "MATH 111", "MATH 112", "MATH 113", "MATH 122",
    "MATH 123", "MATH 224", "MATH 247", "MATH 310",
    "MATH 323", "MATH 341", "MATH 370",

    "PHYS 100", "PHYS 151", "PHYS 152", "PHYS 254",
    "PHYS 255", "PHYS 310",

    "BIOL 100", "BIOL 200", "BIOL 201", "BIOL 205",
    "BIOL 207", "BIOL 260", "BIOL 340",

    "CHEM 100", "CHEM 111A", "CHEM 111B",
    "CHEM 220A", "CHEM 220B", "CHEM 320",

    "ACCT 201", "ACCT 202", "FIN 300",
    "MGMT 300", "MKTG 300", "IS 300",

    "PSY 100", "PSY 220", "PSY 241",
    "PSY 301", "PSY 310", "PSY 370",

    "ENGL 100", "ENGL 180", "ENGL 250",
    "ENGL 300", "ENGL 317",

    "COMM 110", "COMM 130", "COMM 200",
    "COMM 300", "COMM 335",

    "HIST 101", "HIST 102", "HIST 172",
    "HIST 173", "HIST 300",

    "POSC 100", "POSC 199", "POSC 300",
    "POSC 320",

    "ART 110", "ART 130", "ART 181",
    "ART 223", "ART 300",

    "MAE 101", "MAE 205", "MAE 272",
    "MAE 300", "MAE 371",

    "KIN 100", "KIN 201", "KIN 301",
    "HSC 150", "HSC 210",

    "SOC 100", "SOC 142", "SOC 270",
    "SOC 335"
]

# Possible days for classes
class_days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Monday/Wednesday",
    "Tuesday/Thursday",
    "Monday/Wednesday/Friday",
    "Wednesday/Friday"
]


def seed_database():

    users_created = 0
    schedules_created = 0

    print("Starting database seed...\n")

    # Make sure we have buildings to assign classes to
    if not classroom_buildings:
        print("Error: No classroom buildings were found.")
        return

    for i in range(1, NUM_STUDENTS + 1):

        # Each student gets their own random seed.
        # This keeps their generated schedule the same every time.
        random.seed(42 + i)

        first_name = "Test"
        last_name = f"Student{i}"
        email = f"student{i:04d}@test.com"

        # Check if this student already exists
        user_id = get_user_id(email)

        if user_id is not None:
            print(f"{email} already exists.")

        else:
            # Create the student account
            result = add_user(
                first_name,
                last_name,
                email,
                TEST_PASSWORD
            )

            if not result["success"]:
                print(
                    f"Could not create {email}: "
                    f"{result['message']}"
                )
                continue

            users_created += 1

            # Get the new student's ID
            user_id = get_user_id(email)

            if user_id is None:
                print(f"Could not find ID for {email}")
                continue

            print(f"Created: {email}")

        # Check if the student already has classes
        existing_schedule = get_user_schedule(user_id)

        if existing_schedule:
            print("  Schedule already exists. Skipping.")
            continue

        # Give each student between 1 and 6 classes
        number_of_classes = random.randint(1, 6)

        # Choose different classes for this student
        selected_classes = random.sample(
            class_names,
            number_of_classes
        )

        print(f"  Generating {number_of_classes} classes...")

        for class_name in selected_classes:

            # Try different times if a class overlaps
            for attempt in range(100):

                day = random.choice(class_days)

                building = random.choice(classroom_buildings)

                # Generate a class between 7 AM and 11 PM
                start_hour = random.randint(7, 22)
                end_hour = start_hour + 1

                start_time = f"{start_hour:02d}:00"
                end_time = f"{end_hour:02d}:00"

                # Add the class using our existing validation
                result = add_schedule(
                    user_id,
                    class_name,
                    building,
                    day,
                    start_time,
                    end_time
                )

                if result["success"]:

                    schedules_created += 1

                    print(
                        f"  Added: {class_name} | "
                        f"{day} | "
                        f"{start_time}-{end_time} | "
                        f"{building}"
                    )

                    break

            else:
                print(f"  Could not schedule: {class_name}")

        print()

    print("--------------------------------")
    print("Database seeding finished!")
    print("New users created:", users_created)
    print("New schedules created:", schedules_created)
    print("--------------------------------")


if __name__ == "__main__":
    seed_database()
