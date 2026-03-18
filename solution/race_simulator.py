import sys
import json

# Tuned parameters (based on your analysis)

TIRE_OFFSET = {
    "SOFT": -0.8,
    "MEDIUM": 0.0,
    "HARD": +0.6
}

# (a, b) for degradation = a * (age ^ b)
TIRE_DEG = {
    "SOFT": (0.12, 1.5),
    "MEDIUM": (0.08, 1.3),
    "HARD": (0.05, 1.2)
}

FRESH_TIRE_BONUS = -0.3  # small boost on new tires


# Lap time model
def compute_lap_time(base, tire, tire_age, temp):
    # Base offsets
    offset = TIRE_OFFSET[tire]

    # Piecewise degradation (CRITICAL)
    if tire == "SOFT":
        if tire_age <= 8:
            deg = 0.05 * tire_age
        elif tire_age <= 15:
            deg = 0.05 * 8 + 0.25 * (tire_age - 8)
        else:
            deg = 0.05 * 8 + 0.25 * 7 + 0.6 * (tire_age - 15)

    elif tire == "MEDIUM":
        if tire_age <= 12:
            deg = 0.04 * tire_age
        elif tire_age <= 25:
            deg = 0.04 * 12 + 0.12 * (tire_age - 12)
        else:
            deg = 0.04 * 12 + 0.12 * 13 + 0.3 * (tire_age - 25)

    elif tire == "HARD":
        if tire_age <= 20:
            deg = 0.03 * tire_age
        elif tire_age <= 40:
            deg = 0.03 * 20 + 0.08 * (tire_age - 20)
        else:
            deg = 0.03 * 20 + 0.08 * 20 + 0.2 * (tire_age - 40)

    # Temperature effect
    temp_factor = 1 + 0.015 * (temp - 25)

    lap_time = base + offset + deg * temp_factor

    # Fresh tire boost
    if tire_age == 1:
        lap_time += FRESH_TIRE_BONUS

    return lap_time


# Race simulation
def simulate_race(test_case):
    race_id = test_case["race_id"]
    config = test_case["race_config"]
    strategies = test_case["strategies"]

    total_laps = config["total_laps"]
    base = config["base_lap_time"]
    pit_time = config["pit_lane_time"]
    temp = config["track_temp"]

    # Initialize drivers
    drivers = {}

    for pos, strat in strategies.items():
        drivers[strat["driver_id"]] = {
            "tire": strat["starting_tire"],
            "tire_age": 0,
            "pit_map": {pit["lap"]: pit for pit in strat["pit_stops"]},
            "time": 0
        }

    # Simulate race lap-by-lap
    for lap in range(1, total_laps + 1):
        for d in drivers.values():

            # increase tire age FIRST
            d["tire_age"] += 1

            # compute lap time
            lap_time = compute_lap_time(base, d["tire"], d["tire_age"], temp)
            d["time"] += lap_time

            # check pit AFTER lap
            if lap in d["pit_map"]:
                pit = d["pit_map"][lap]
                d["time"] += pit_time
                d["tire"] = pit["to_tire"]
                d["tire_age"] = 0 # reset age on new tires

    # sort by total time
    sorted_drivers = sorted(drivers.items(), key=lambda x: x[1]["time"])

    finishing_order = [driver_id for driver_id, _ in sorted_drivers]

    return {
        "race_id": race_id,
        "finishing_positions": finishing_order
    }


# Entry point
if __name__ == "__main__":
    test_case = json.load(sys.stdin)
    result = simulate_race(test_case)
    print(json.dumps(result))