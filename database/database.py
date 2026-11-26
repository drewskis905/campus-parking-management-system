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

    # Create a table to save each user's parking preferences
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_parking_preferences (
            user_id INTEGER PRIMARY KEY,
            preferred_lot TEXT,
            priority TEXT NOT NULL DEFAULT 'balanced',
            FOREIGN KEY (user_id) REFERENCES users(id)
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
def add_user(first_name, last_name, email, password, *, connection=None):
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
    conn = connection if connection is not None else get_connection()

    try:
        # Hash the password before storing it
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor = conn.execute("""
            INSERT INTO users
            (first_name, last_name, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (first_name, last_name, email, password_hash))

        if connection is None:
            conn.commit()

        return {
            "success": True,
            "user_id": cursor.lastrowid,
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
        if connection is None:
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

# Permanently delete the student's account after verifying their password.
def delete_account(user_id, password):
    conn = get_connection()

    try:
        # Get the student's saved password hash.
        user = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if user is None:
            return {
                "success": False,
                "message": "Account not found."
            }

        # Make sure the student entered their correct password.
        password_hash = user[0]

        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')

        if not bcrypt.checkpw(
            password.encode('utf-8'), password_hash
        ):
            return {
                "success": False,
                "message": "Incorrect password."
            }

        # Remove all information associated with the student's account.
        conn.execute(
            "DELETE FROM schedules WHERE user_id = ?",
            (user_id,)
        )

        conn.execute(
            "DELETE FROM parking_plans WHERE user_id = ?",
            (user_id,)
        )

        conn.execute(
            "DELETE FROM user_parking_preferences WHERE user_id = ?",
            (user_id,)
        )

        # Delete the account after removing its saved information.
        conn.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )

        conn.commit()

        return {
            "success": True,
            "message": "Account deleted successfully."
        }

    except (sqlite3.Error, ValueError):
        # Undo all changes if the account could not be deleted.
        conn.rollback()

        return {
            "success": False,
            "message": "Could not delete account. Please try again."
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


# Check if a new class overlaps with an existing class
def check_schedule_overlap(user_id, day, start_time, end_time, *, connection=None):
    conn = connection if connection is not None else get_connection()

    cursor = conn.execute("""
        SELECT class_name, day, start_time, end_time
        FROM schedules
        WHERE user_id = ?
    """, (user_id,))

    existing_classes = cursor.fetchall()
    if connection is None:
        conn.close()

    # Get the days for the new class
    new_days = set(d.strip() for d in day.split("/"))

    for class_name, existing_day, existing_start, existing_end in existing_classes:

        # Get the days for the existing class
        existing_days = set(d.strip() for d in existing_day.split("/"))

        # Check if they share at least one day
        same_day = bool(new_days & existing_days)

        # Check if their times overlap
        same_time = start_time < existing_end and end_time > existing_start

        if same_day and same_time:
            return class_name

    return None

# Add a class to a user's schedule
def add_schedule(user_id, class_name, building, day, start_time, end_time, *, connection=None):

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

    conn = connection if connection is not None else get_connection()

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
        # Check if the new class overlaps with an existing class
        overlapping_class = check_schedule_overlap(
            user_id,
            day,
            start_time,
            end_time,
            connection=conn,
        )

        if overlapping_class:
            return {
                "success": False,
                "message": f"Could not add schedule: this class overlaps with {overlapping_class}."
            }
        conn.execute("""
            INSERT INTO schedules
            (user_id, class_name, building, day, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, class_name, building, day, start_time, end_time))

        if connection is None:
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
        if connection is None:
            conn.close()


def register_user(first_name, last_name, email, password, schedules):
    """Save an account and all its classes together, or save nothing."""
    conn = None
    try:
        conn = get_connection()
        result = add_user(first_name, last_name, email, password, connection=conn)
        if not result['success']:
            conn.rollback()
            if 'users.email' in result['message']:
                return {'success': False, 'message': 'An account with this email already exists.'}
            return result

        user_id = result['user_id']
        for index, schedule in enumerate(schedules, start=1):
            if conn.execute('SELECT 1 FROM buildings WHERE name = ?',
                            (schedule['building'],)).fetchone() is None:
                conn.rollback()
                return {'success': False, 'message': f'Class {index}: choose a listed building.'}
            result = add_schedule(user_id, **schedule, connection=conn)
            if not result['success']:
                conn.rollback()
                return {'success': False, 'message': f'Class {index}: {result["message"]}'}

        conn.commit()
        return {'success': True, 'user_id': user_id, 'message': 'Account created successfully.'}
    except (sqlite3.Error, ValueError):
        if conn is not None:
            conn.rollback()
        return {'success': False, 'message': 'Could not create your account. Please try again.'}
    finally:
        if conn is not None:
            conn.close()


# Update one class without changing the rest of the student's schedule.
def update_schedule(user_id, schedule_id, class_name, building,
                    day, start_time, end_time):

    # Make sure all the class information was entered.
    if not all([class_name.strip(), building.strip(), day.strip(),
                start_time.strip(), end_time.strip()]):
        return {"success": False, "message": "Please fill in all fields."}

    # Check that the selected days and class times are valid.
    if not validate_class_day(day) or not validate_time(start_time, end_time):
        return {"success": False, "message": "Invalid class days or times."}

    with get_connection() as conn:

        # Make sure this class belongs to the logged-in student.
        existing = conn.execute(
            "SELECT id FROM schedules WHERE id = ? AND user_id = ?",
            (schedule_id, user_id)
        ).fetchone()

        if not existing:
            return {"success": False, "message": "Class not found."}

        # Make sure the building exists in our campus database.
        building_exists = conn.execute(
            "SELECT 1 FROM buildings WHERE name = ?", (building,)
        ).fetchone()

        if not building_exists:
            return {"success": False, "message": "Choose a valid building."}

        # Check other classes, but skip the class we're currently editing.
        other_classes = conn.execute(
            """SELECT class_name, day, start_time, end_time
               FROM schedules
               WHERE user_id = ? AND id != ?""",
            (user_id, schedule_id)
        ).fetchall()

        new_days = set(d.strip() for d in day.split("/"))

        for other_name, other_day, other_start, other_end in other_classes:
            other_days = set(d.strip() for d in other_day.split("/"))

            if new_days & other_days and start_time < other_end and end_time > other_start:
                return {
                    "success": False,
                    "message": f"This class overlaps with {other_name}."
                }

        # Prevent two classes from having the same name.
        duplicate = conn.execute(
            """SELECT 1 FROM schedules
               WHERE user_id = ? AND class_name = ? AND id != ?""",
            (user_id, class_name, schedule_id)
        ).fetchone()

        if duplicate:
            return {"success": False, "message": "This class already exists."}

        # Save the updated class information.
        conn.execute(
            """UPDATE schedules
               SET class_name = ?, building = ?, day = ?,
                   start_time = ?, end_time = ?
               WHERE id = ? AND user_id = ?""",
            (class_name, building, day, start_time, end_time,
             schedule_id, user_id)
        )

    return {"success": True, "message": "Class updated successfully."}


# Delete only the selected class from the student's schedule.
def delete_schedule(user_id, schedule_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM schedules WHERE id = ? AND user_id = ?",
            (schedule_id, user_id)
        )

        if cursor.rowcount == 0:
            return {"success": False, "message": "Class not found."}

    return {"success": True, "message": "Class deleted successfully."}


# Get all classes for a specific user
def get_user_schedule(user_id):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM schedules
        WHERE user_id = ?
        ORDER BY start_time ASC
    """, (user_id,))

    schedule = cursor.fetchall()

    conn.close()

    return schedule

# Get a user's classes for a specific day, sorted by time
def get_user_schedule_by_day(user_id, day):
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM schedules
        WHERE user_id = ?
        AND ('/' || REPLACE(day, ' ', '') || '/') LIKE
            ('%/' || ? || '/%')
        ORDER BY start_time ASC
    """, (user_id, day.strip()))

    schedule = cursor.fetchall()

    conn.close()

    # Check if no classes were found
    if not schedule:
        return f"There are no classes scheduled for {day}."

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

# Save or update the student's selected parking preference.
def save_parking_preference(user_id, priority, preferred_lot=None):
    # Make sure the selected preference is valid.
    if priority not in ('availability', 'distance', 'preferred_lot'):
        return {
            "success": False,
            "message": "Invalid parking preference."
        }

    # Only save a parking lot when the student chooses that option.
    if priority == 'preferred_lot':
        if not preferred_lot:
            return {
                "success": False,
                "message": "Please select a parking lot."
            }
    else:
        preferred_lot = None

    conn = get_connection()

    try:
        # Update the existing preference if the student already has one.
        conn.execute("""
            INSERT INTO user_parking_preferences
                (user_id, preferred_lot, priority)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                preferred_lot = excluded.preferred_lot,
                priority = excluded.priority
        """, (user_id, preferred_lot, priority))

        conn.commit()

        return {
            "success": True,
            "message": "Parking preference saved successfully."
        }

    finally:
        conn.close()

# Get the user's saved parking preference
def get_user_parking_prefer(user_id):
    conn = get_connection()

    try:
        # Find the parking priority saved by this user
        cursor = conn.execute("""
            SELECT priority
            FROM user_parking_preferences
            WHERE user_id = ?
        """, (user_id,))

        preference = cursor.fetchone()

        # Use balanced if the user has not saved a preference
        if preference is None:
            return "balanced"

        return preference[0]

    finally:
        conn.close()


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



# Save a student's parking plan for a specific day.
# If they already have a plan for that day, replace it instead of adding another one.
def save_parking_plan(user_id, lot, day, start_time, end_time):

    # Check the information before saving anything to the database.
    if user_id is None or not all([lot, day, start_time, end_time]):
        return {"success": False, "message": "Missing parking plan information."}

    if not validate_class_day(day) or "/" in day:
        return {"success": False, "message": "Choose one valid day."}

    if not validate_time(start_time, end_time):
        return {"success": False, "message": "Invalid parking plan times."}

    try:
        with get_connection() as conn:

            # Check whether this student already has a parking plan for this day.
            existing_plan = conn.execute(
                """SELECT id FROM parking_plans
                   WHERE user_id = ? AND day = ?""",
                (user_id, day)
            ).fetchone()

            if existing_plan:

                # Update the existing plan so we don't count the same student twice.
                conn.execute(
                    """UPDATE parking_plans
                       SET lot = ?, start_time = ?, end_time = ?
                       WHERE user_id = ? AND day = ?""",
                    (lot, start_time, end_time, user_id, day)
                )
                message = "Parking plan updated successfully."

            else:

                # Create a new plan if this student hasn't chosen a lot for this day.
                conn.execute(
                    """INSERT INTO parking_plans
                       (user_id, lot, day, start_time, end_time)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, lot, day, start_time, end_time)
                )
                message = "Parking plan saved successfully."

        return {"success": True, "message": message}

    except sqlite3.Error as error:
        return {"success": False, "message": f"Could not save parking plan: {error}"}


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





