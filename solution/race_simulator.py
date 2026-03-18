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

FRESH_TIRE_BONUS = -0.15  # small boost on new tires


# Lap time model
def compute_lap_time(base, tire, tire_age, temp):
    # Base offsets
    offset = TIRE_OFFSET[tire]

    # Piecewise degradation (CRITICAL)
    if tire == "SOFT":
        if tire_age <= 10:
            deg = 0.04 * tire_age
        elif tire_age <= 18:
            deg = 0.04 * 10 + 0.18 * (tire_age - 10)
        else:
            deg = 0.04 * 10 + 0.18 * 8 + 0.4 * (tire_age - 18)

    elif tire == "MEDIUM":
        if tire_age <= 15:
            deg = 0.035 * tire_age
        elif tire_age <= 30:
            deg = 0.035 * 15 + 0.10 * (tire_age - 15)
        else:
            deg = 0.035 * 15 + 0.10 * 15 + 0.25 * (tire_age - 30)

    elif tire == "HARD":
        if tire_age <= 25:
            deg = 0.025 * tire_age
        elif tire_age <= 45:
            deg = 0.025 * 25 + 0.06 * (tire_age - 25)
        else:
            deg = 0.025 * 25 + 0.06 * 20 + 0.15 * (tire_age - 45)

    # Temperature effect
    temp_factor = 1 + 0.008 * (temp - 25)

    lap_time = base + offset + deg * temp_factor

    # Fresh tire boost
    if tire_age == 1:
        lap_time += FRESH_TIRE_BONUS

    return lap_time


def strategy_score(driver, total_laps):
    tire = driver["initial_tire"]
    pits = driver["pit_stops"]

    stints = []
    prev = 0
    current = tire

    for pit in pits:
        stints.append((current, pit["lap"] - prev))
        current = pit["to_tire"]
        prev = pit["lap"]

    stints.append((current, total_laps - prev))

    soft = sum(l for t, l in stints if t == "SOFT")
    medium = sum(l for t, l in stints if t == "MEDIUM")
    hard = sum(l for t, l in stints if t == "HARD")
    stops = len(stints) - 1

    # from the ML model
    score = (
        0.165 * soft
        - 0.043 * medium
        - 0.139 * hard
        - 2.36 * stops
    )

    return score


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
            "initial_tire": strat["starting_tire"], 
            "tire_age": 0,
            "pit_map": {pit["lap"]: pit for pit in strat["pit_stops"]},
            "pit_stops": strat["pit_stops"], 
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

    for d in drivers.values():
        d["score"] = strategy_score(d, total_laps)

    # sort by total time
    sorted_drivers = sorted(
        drivers.items(),
        key=lambda x: x[1]["time"] + 0.1 * x[1]["score"]
    )

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