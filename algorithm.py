from datetime import time

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

demand = calculate_schedule_demand(schedules, time(10, 0))
print(f"Estimate to be {classify_demand(demand)}")