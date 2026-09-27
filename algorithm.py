from datetime import time

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