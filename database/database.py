import sqlite3
import json
import os
import bcrypt
from datetime import datetime
from enum import Enum

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(BASE_DIR, "parking.db")

LOTS_FILE = os.path.join(BASE_DIR, "data", "lots.json")
BUILDINGS_FILE = os.path.join(BASE_DIR, "data", "buildings.json")

# Days that can be used for a class schedule
class ClassDay(Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"

# Check if the class day is valid
def validate_class_day(day):
    days = day.split("/")

    valid_days = [class_day.value for class_day in ClassDay]

    for class_day in days:
        if class_day.strip() not in valid_days:
            return False

    return True


# Connect to the database
def get_connection():
    return sqlite3.connect(DATABASE)


# Create the database tables
def create_tables():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            capacity INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            lat REAL NOT NULL,
            lng REAL NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS schedules(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            building TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS parking_plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lot TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Load parking lots from lots.json into the database
def load_lots():
    with open(LOTS_FILE, "r") as file:
        lots = json.load(file)

    conn = get_connection()

    for lot in lots:
        conn.execute("""
            INSERT INTO lots (name, lat, lng, capacity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                lat = excluded.lat,
                lng = excluded.lng,
                capacity = excluded.capacity
        """, (
            lot["name"],
            lot["lat"],
            lot["lng"],
            lot["capacity"]
        ))

    conn.commit()
    conn.close()


# Load buildings from buildings.json
def load_buildings():
    with open(BUILDINGS_FILE, "r") as file:
        buildings = json.load(file)

    conn = get_connection()

    for building in buildings:
        conn.execute("""
            INSERT OR IGNORE INTO buildings (name, lat, lng)
            VALUES (?, ?, ?)
        """, (
            building["name"],
            building["lat"],
            building["lng"]
        ))

    conn.commit()
    conn.close()

# Get all parking lots
def get_all_lots():
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM lots
    """)

    lots = cursor.fetchall()
    conn.close()

    return lots


# Get one parking lot by name
def get_lot(name):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM lots
        WHERE name = ?
    """, (name,))

    lot = cursor.fetchone()
    conn.close()

    return lot


# Add a new parking lot
def add_lot(name, lat, lng, capacity=None):
    conn = get_connection()

    conn.execute("""
        INSERT INTO lots (name, lat, lng, capacity)
        VALUES (?, ?, ?, ?)
    """, (name, lat, lng, capacity))

    conn.commit()
    conn.close()


# Update a parking lot's capacity
def update_lot_capacity(name, capacity):
    conn = get_connection()

    conn.execute("""
        UPDATE lots
        SET capacity = ?
        WHERE name = ?
    """, (capacity, name))

    conn.commit()
    conn.close()


# Delete a parking lot
def delete_lot(name):
    conn = get_connection()

    conn.execute("""
        DELETE FROM lots
        WHERE name = ?
    """, (name,))

    conn.commit()
    conn.close()


# Get all buildings
def get_all_buildings():
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM buildings
    """)

    buildings = cursor.fetchall()
    conn.close()

    return buildings

# Get all values from one or more columns in a table
def get_all(table, *columns):
    allowed_columns = {
        "lots": ["id", "name", "lat", "lng", "capacity"],
        "buildings": ["id", "name", "lat", "lng"]
    }

    # Make sure the table exists
    if table not in allowed_columns:
        return None

    # Make sure at least one column was requested
    if not columns:
        return None

    # Make sure every requested column exists
    for column in columns:
        if column not in allowed_columns[table]:
            return None

    conn = get_connection()

    # Put the requested columns together for the SQL query
    selected_columns = ", ".join(columns)

    cursor = conn.execute(
        f"SELECT {selected_columns} FROM {table}"
    )

    rows = cursor.fetchall()

    conn.close()

    # If only one column was requested, return a simple list
    if len(columns) == 1:
        return [row[0] for row in rows]

    # If multiple columns were requested, return the rows
    return rows

# Add a new registered user
def add_user(first_name, last_name, email, password):
    # Check for any empty fields
    empty_fields = []

    if not first_name or not first_name.strip():
        empty_fields.append("first_name")

    if not last_name or not last_name.strip():
        empty_fields.append("last_name")

    if not email or not email.strip():
        empty_fields.append("email")

    if not password or not password.strip():
        empty_fields.append("password")

    # If any fields are empty, don't add the user
    if empty_fields:
        return {
            "success": False,
            "message": f"Could not add user: empty field(s): {', '.join(empty_fields)}."
        }
    conn = get_connection()

    try:
        # Hash the password before storing it
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        conn.execute("""
            INSERT INTO users
            (first_name, last_name, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (first_name, last_name, email, password_hash))

        conn.commit()

        return {
            "success": True,
            "message": "User added successfully."
        }

    except sqlite3.IntegrityError as error:
        return {
            "success": False,
            "message": f"Could not add user: {error}"
        }

    except sqlite3.Error as error:
        return {
            "success": False,
            "message": f"Database error: {error}"
        }

    finally:
        conn.close()

# Check if a user is already registered
def is_registered(email):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM users
        WHERE email = ?
    """, (email,))

    user = cursor.fetchone()

    conn.close()

    return user is not None

# Get a user's ID using their email
def get_user_id(email):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT id FROM users
        WHERE email = ?
    """, (email,))

    user = cursor.fetchone()

    conn.close()

    if user:
        return user[0]

    return None

def verify_password(email, password):
    conn = get_connection()

    try:
        # Get the stored password hash for this email
        cursor = conn.execute("""
            SELECT password_hash FROM users
            WHERE email = ?
        """, (email,))

        user = cursor.fetchone()

        # No account was found with this email
        if user is None:
            return {
                "success": False,
                "message": "Invalid email or password."
            }

        stored_hash = user[0]

        # Check the entered password against the stored hash
        if bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8")
        ):
            return {
                "success": True,
                "message": "Password is correct."
            }

        return {
            "success": False,
            "message": "Invalid email or password."
        }

    except sqlite3.Error as error:
        return {
            "success": False,
            "message": f"Database error: {error}"
        }

    finally:
        conn.close()

# Delete a registered user
def delete_user(email):
    conn = get_connection()

    conn.execute("""
        DELETE FROM users
        WHERE email = ?
    """, (email,))

    conn.commit()
    conn.close()

# Delete all schedules for a specific user
def delete_user_schedule(user_id):
    conn = get_connection()

    conn.execute("""
        DELETE FROM schedules
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

# Check that the start and end times are valid
def validate_time(start_time, end_time):
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")

        # Make sure the end time is after the start time
        if start >= end:
            return False

        # Earliest allowed time is 7:00 AM
        earliest_time = datetime.strptime("07:00", "%H:%M")

        # Latest allowed time is 9:00 PM
        latest_time = datetime.strptime("23:00", "%H:%M")

        # Make sure the times are within the allowed range
        if start < earliest_time or end > latest_time:
            return False

        return True

    except ValueError:
        return False

# Convert stored time to AM/PM for displaying
def format_time(time_string):
    time = datetime.strptime(time_string, "%H:%M")
    return time.strftime("%I:%M %p").lstrip("0")

# Add a class to a user's schedule
def add_schedule(user_id, class_name, building, day, start_time, end_time):

    # Check for any empty fields
    empty_fields = []

    if user_id is None:
        empty_fields.append("user_id")

    if not class_name or not class_name.strip():
        empty_fields.append("class_name")

    if not building or not building.strip():
        empty_fields.append("building")

    if not day or not day.strip():
        empty_fields.append("day")

    if not start_time or not start_time.strip():
        empty_fields.append("start_time")

    if not end_time or not end_time.strip():
        empty_fields.append("end_time")

    # If any fields are empty, don't add the schedule
    if empty_fields:
        return {
            "success": False,
            "message": f"Could not add schedule: empty field(s): {', '.join(empty_fields)}."
        }

    # Make sure the class day is valid
    if not validate_class_day(day):
        return {
            "success": False,
            "message": "Could not add schedule: invalid class day."
        }

    # Check the times before adding the schedule
    if not validate_time(start_time, end_time):
        return {
            "success": False,
            "message": "Could not add schedule: invalid start or end time."
        }

    conn = get_connection()

    try:
        # Check if this class is already in the user's schedule
        cursor = conn.execute("""
            SELECT id FROM schedules
            WHERE user_id = ?
            AND class_name = ?
        """, (user_id, class_name))

        existing_schedule = cursor.fetchone()

        if existing_schedule:
            return {
                "success": False,
                "message": "Could not add schedule: this class is already in the user's schedule."
            }
        conn.execute("""
            INSERT INTO schedules
            (user_id, class_name, building, day, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, class_name, building, day, start_time, end_time))

        conn.commit()

        return {
            "success": True,
            "message": "Schedule added successfully."
        }

    except sqlite3.Error as error:
        return {
            "success": False,
            "message": f"Could not add schedule: {error}"
        }

    finally:
        conn.close()

# Get all classes for a specific user
def get_user_schedule(user_id):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM schedules
        WHERE user_id = ?
    """, (user_id,))

    schedule = cursor.fetchall()

    conn.close()

    return schedule

# Get one building by name
def get_building(name):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM buildings
        WHERE name = ?
    """, (name,))

    building = cursor.fetchone()
    conn.close()

    return building


# Add a new building
def add_building(name, lat, lng):
    conn = get_connection()

    conn.execute("""
        INSERT INTO buildings (name, lat, lng)
        VALUES (?, ?, ?)
    """, (name, lat, lng))

    conn.commit()
    conn.close()


# Update a building's coordinates
def update_building(name, lat, lng):
    conn = get_connection()

    conn.execute("""
        UPDATE buildings
        SET lat = ?, lng = ?
        WHERE name = ?
    """, (lat, lng, name))

    conn.commit()
    conn.close()


# Delete a building
def delete_building(name):
    conn = get_connection()

    conn.execute("""
        DELETE FROM buildings
        WHERE name = ?
    """, (name,))

    conn.commit()
    conn.close()


# Add a parking plan for a user
def add_parking_plan(user_id, lot, day, start_time, end_time):
    # Check for any empty fields
    empty_fields = []

    if user_id is None:
        empty_fields.append("user_id")

    if not lot or not lot.strip():
        empty_fields.append("lot")

    if not day or not day.strip():
        empty_fields.append("day")

    if not start_time or not start_time.strip():
        empty_fields.append("start_time")

    if not end_time or not end_time.strip():
        empty_fields.append("end_time")

    # If any fields are empty, don't add the parking plan
    if empty_fields:
        return {
            "success": False,
            "message": f"Could not add parking plan: empty field(s): {', '.join(empty_fields)}."
        }
    # Make sure the parking plan day is valid
    if not validate_class_day(day):
        return {
            "success": False,
            "message": "Could not add parking plan: invalid day."
        }

    # Check the times before adding the parking plan
    if not validate_time(start_time, end_time):
        return {
            "success": False,
            "message": "Could not add parking plan: invalid start or end time."
        }

    conn = get_connection()

    try:
        conn.execute("""
            INSERT INTO parking_plans
            (user_id, lot, day, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, lot, day, start_time, end_time))

        conn.commit()

        return {
            "success": True,
            "message": "Parking plan added successfully."
        }

    except sqlite3.Error as error:
        return {
            "success": False,
            "message": f"Could not add parking plan: {error}"
        }

    finally:
        conn.close()

# Get all parking plans for a specific user
def get_user_parking_plans(user_id):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM parking_plans
        WHERE user_id = ?
    """, (user_id,))

    plans = cursor.fetchall()

    conn.close()

    return plans

# Delete one specific parking plan
def delete_parking_plan(plan_id):
    conn = get_connection()

    conn.execute("""
        DELETE FROM parking_plans
        WHERE id = ?
    """, (plan_id,))

    conn.commit()
    conn.close()

# Update a specific parking plan
def update_parking_plan(plan_id, lot, day, start_time, end_time):
    # Make sure the parking plan day is valid
    if not validate_class_day(day):
        return {
            "success": False,
            "message": "Could not update parking plan: invalid day."
        }

    # Check the times before updating the parking plan
    if not validate_time(start_time, end_time):
        return {
            "success": False,
            "message": "Could not update parking plan: invalid start or end time."
        }

    conn = get_connection()

    try:
        conn.execute("""
            UPDATE parking_plans
            SET lot = ?, day = ?, start_time = ?, end_time = ?
            WHERE id = ?
        """, (lot, day, start_time, end_time, plan_id))

        conn.commit()

        return {
            "success": True,
            "message": "Parking plan updated successfully."
        }

    except sqlite3.Error as error:
        return {
            "success": False,
            "message": f"Could not update parking plan: {error}"
        }

    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()

    load_lots()
    load_buildings()

    print("Database setup complete!")

    print("\nParking lots:")
    for lot in get_all_lots():
        print(lot)

    print("\nBuildings:")
    for building in get_all_buildings():
        print(building)







