"""
fake_database.py

A temporary stand-in for database.py, so you can test algorithm.py
end-to-end WITHOUT needing the real parking_plans table to exist yet.

Returns data in the exact same shape the real database.py functions
would - once David's real version is ready, just change the import
in algorithm.py back to:
    from database.database import get_all_parking_plans, get_lot
"""

from datetime import time

# Pretend this is what's actually stored in the parking_plans table -
# same shape as the real get_all_parking_plans() would return:
# (user_id, lot_id, day, arrival_time, departure_time)  -- times as "HH:MM" strings
_FAKE_PARKING_PLANS = [
    (1, "G3", "Monday", "09:00", "14:00"),
    (2, "G3", "Monday", "09:00", "14:00"),
    (3, "G3", "Monday", "16:00", "18:00"),
    (4, "G4", "Monday", "16:00", "18:00"),
    (7, "G4", "Monday", "08:00", "12:00"),
    (8, "G4", "Monday", "09:30", "15:00"),
    (9, "G4", "Monday", "11:00", "14:00"),
]

# Pretend this is what's in the lots table - same shape as the real
# get_lot() would return: (id, name, lat, lng, capacity)
_FAKE_LOTS = {
    "G3": (3, "G3", 33.782955, -118.117363, 223),
    "G4": (4, "G4", 33.784679, -118.118614, 213),
}


def get_all_parking_plans():
    """Fake version - returns hardcoded test data instead of querying a real database."""
    return _FAKE_PARKING_PLANS


def get_lot(lot_id):
    """Fake version - returns hardcoded test data instead of querying a real database."""
    return _FAKE_LOTS.get(lot_id)  # returns None if lot_id isn't in the fake data