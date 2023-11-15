import src.constants as c
import numpy as np


def get_actual_availabilities(availabilities, start_time, end_time):
    actual_availabilities = []

    for av in availabilities:
        if av[1] < start_time or av[0] > end_time:
            continue

        if av[0] < start_time:
            av = (start_time, av[1])
        if av[1] > end_time:
            av = (av[0], end_time)

        actual_availabilities.append(av)

    return actual_availabilities


def calculate_possible_visits(availabilities, duration):
    possible_visits = 0

    for av in availabilities:
        time_window = av[1] - av[0]
        possible_visits += (time_window + c.INTRA_MUN_TIME) // (duration + c.INTRA_MUN_TIME)

    return possible_visits


def is_possible_start_time(availabilities, start_time, duration):
    for av in availabilities:
        if av[0] <= start_time and start_time + duration <= av[1]:
            return True

    return False


def sample_extend_time(extend_min, extend_mode, extend_max):
    return int(np.random.triangular(extend_min, extend_mode, extend_max))


def sample_noise_time(noise_time):
    return np.random.randint(-noise_time, noise_time + 1)


def rush_hours_coefficient(time):
    return 0.5 if time in range(60, 180) or time in range(630, 810) else 1


def compute_objective_factor(objective_delta):
    return 1 + (objective_delta / c.OBJ_CONSTANT)


def compute_time_offset_factor(visit):
    return 1 + (np.abs(visit.proposed_start_time - visit.scheduled_start_time) / c.TIME_OFFSET_CONSTANT)


def compute_robustness_factor(op_skill, visit_duration_distr, prev_possible_visits, new_possible_visits, patient_municipality_distr, n_municipalities):
    visit_durations = list(visit_duration_distr.keys())
    skill_coefficients = []
    for skill in [0,1]:
        if op_skill < skill:
            continue
        
        skill_coefficient = 0
        for duration in range(len(visit_durations)):
            duration_coefficient = 0
            for municipality in range(n_municipalities):
                ratio = (c.SMOOTHING_CONSTANT + prev_possible_visits[skill][duration][municipality]) / (c.SMOOTHING_CONSTANT + new_possible_visits[skill][duration][municipality])
                duration_coefficient += ratio * patient_municipality_distr[municipality]
                
            skill_coefficient += duration_coefficient * visit_duration_distr[visit_durations[duration]]

        skill_coefficients.append(skill_coefficient)

    robustness = sum(skill_coefficients) / len(skill_coefficients)

    return robustness


def day_adjustment(day):
    return (5 - day) / 3
    # return day != 4