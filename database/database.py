import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(BASE_DIR, "parking.db")

LOTS_FILE = os.path.join(BASE_DIR, "data", "lots.json")
BUILDINGS_FILE = os.path.join(BASE_DIR, "data", "buildings.json")


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
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS schedules(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            building TEXT NOT NULL,
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
def add_user(name, email):
    conn = get_connection()

    conn.execute("""
        INSERT INTO users (name, email)
        VALUES (?, ?)
    """, (name, email))

    conn.commit()
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

# Add a class to a user's schedule
def add_schedule(user_id, building, day, start_time, end_time):
    conn = get_connection()

    conn.execute("""
        INSERT INTO schedules (user_id, building, day, start_time, end_time)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, building, day, start_time, end_time))

    conn.commit()
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







