import src.constants as c
import src.utilities as u
import src.stats as s
import src.manipulation as m
import src.processing as p

import os
import numpy as np
import csv
import random
import math


# --------------- HYPERPARAMETERS --------------- #

def generate_hyperparams(
    Cw=c.DEF_C_WAGE,
    Cm=c.DEF_C_MOVEMENT,
    Co=c.DEF_C_OVERSKILL,
    Cx=c.DEF_C_EXECUTION,
    bigM=c.DEF_BIG_M,
    sigma0=c.DEF_SIGMA0,
    sigma1=c.DEF_SIGMA1,
    omega=c.DEF_OMEGA,
    n_days=c.DEF_NUM_DAYS,
    n_municipalities=c.DEF_NUM_MUNICIPALITIES,
    verbose=False
):
    if verbose:
        print("Generating hyperparameters")

    hp_data = {}
    
    # create array with all hyperparameters
    hp_values = [Cw, Cm, Co, Cx, bigM, sigma0, sigma1, omega, n_days, n_municipalities]

    # create dictionary with hyperparameters names as keys and values as values
    for i, hp in enumerate(c.HYPERPARAMS):
        hp_data[hp] = hp_values[i]

    u.save_JSON(hp_data, c.HYPERPARAMS_JSON)

    if verbose:
        print("Generated hyperparameters")

# --------------- END HYPERPARAMETERS --------------- #


# --------------- MUNICIPALITIES --------------- #

def generate_random_municipalities(
    n_municipalities=c.DEF_NUM_MUNICIPALITIES,
    min_time_dist=c.DEF_MIN_DIST,
    max_time_dist=c.DEF_MAX_DIST
):
    municipalities = [(0, 0)]

    for _ in range(n_municipalities - 1):
        while True:
            # generate a random angle in radians
            angle = random.uniform(0, 2 * math.pi)
            # generate a random distance within the specified range
            distance = random.uniform(min_time_dist, max_time_dist)
            
            # randomly select a previous point index (excluding the last point)
            prev_point_index = random.randint(0, len(municipalities) - 1)
            prev_x, prev_y = municipalities[prev_point_index]
            
            # calculate the new point's coordinates
            new_x = prev_x + distance * math.cos(angle)
            new_y = prev_y + distance * math.sin(angle)

            # round to integers new_x and new_y
            new_x = int(new_x)
            new_y = int(new_y)
            
            # check the distance to the closest existing point
            closest_dist = min(math.sqrt((x - new_x)**2 + (y - new_y)**2) for x, y in municipalities)
            
            # if the new point meets the distance criteria, add it and break the loop
            if closest_dist >= min_time_dist:
                municipalities.append((new_x, new_y))
                break
    
    return municipalities


def generate_municipalities(
    n_municipalities=c.DEF_NUM_MUNICIPALITIES,
    min_time_dist=c.DEF_MIN_DIST,
    max_time_dist=c.DEF_MAX_DIST,
    municipalities=None,
    verbose=False
):
    if verbose:
        print(f"Generating {n_municipalities} municipalities")
    
    if municipalities is None:
        # generate one municipality at a time such that each time the closest one 
        # is at least min_time_dist away and at most max_time_dist away
        municipalities = generate_random_municipalities(n_municipalities, min_time_dist, max_time_dist)

    # extract lats and lons from municipalities
    lats = [municipality[0] for municipality in municipalities]
    lons = [municipality[1] for municipality in municipalities]

    municipality_data = {}
    municipality_data[c.MUN_LATITUDE] = lats
    municipality_data[c.MUN_LONGITUDE] = lons

    u.save_JSON(municipality_data, c.MUNICIPALITY_JSON)

    if verbose:
        print(f"Generated {n_municipalities} municipalities")

    u.generate_commuting_matrix()

    if verbose:
        print("Generated commuting matrix")
    
    return True

# --------------- END MUNICIPALITIES --------------- #


# --------------- PATIENTS --------------- #

def generate_uniform_municipalities(n_people, municipality_prob_distr):
    municipalities = []
    
    # multiply each probability by the number of people
    mun_people = [p * n_people for p in municipality_prob_distr]

    # floor each probability
    mun_people = [math.floor(p) for p in mun_people]

    # if the sum of the probabilities is less than n_people, add 1 to the largest number
    if sum(mun_people) < n_people:
        mun_people[mun_people.index(max(mun_people))] += n_people - sum(mun_people)

    # for each municipality, append the number of people specified by mun_people
    for i, p in enumerate(mun_people):
        municipalities.extend([i] * p)
    
    # shuffle the list
    random.shuffle(municipalities)

    return municipalities


def mun_prob_distr_from_comm_matrix():
    _, averages = s.municipality_time_from_others()
    averages = [1 / a for a in averages]
    mun_prob_distr = [a / sum(averages) for a in averages]
    return mun_prob_distr


def generate_patients(
    n_patients,
    uniform=True,
    municipality_prob_distr=None,
    municipalities=None,
    verbose=False
):
    if verbose:
        print(f"Generating {n_patients} patients")

    patient_data = {}
    patient_data[c.N_PATIENTS] = n_patients

    n_municipalities = m.get_num_municipalities()

    if municipalities is None:
        if municipality_prob_distr is None:
            municipality_prob_distr = [1 / n_municipalities] * n_municipalities
        elif municipality_prob_distr is True:
            municipality_prob_distr = mun_prob_distr_from_comm_matrix()
        if uniform:
            municipalities = generate_uniform_municipalities(n_patients, municipality_prob_distr)
        else:
            # generate municipality for each patient
            municipalities = np.random.choice(np.arange(n_municipalities), n_patients, p=municipality_prob_distr).tolist()

        # add 1 to each municipality index to match the ones in the commuting matrix
        municipalities = [municipality + 1 for municipality in municipalities]

    patient_data[c.PAT_MUNICIPALITY] = municipalities

    u.save_JSON(patient_data, c.PATIENT_JSON)

    if verbose:
        print(f"Generated {n_patients} patients")

# --------------- END PATIENTS --------------- #


# --------------- OPERATORS --------------- #

def generate_uniform_skills(n_operators, skill_prob_distr):
    # assume that there are only 2 levels of skill
    high_level = 1 / skill_prob_distr[1]

    skills = []
    for op in range(n_operators):
        # append ratio 0, then 1 and repeat
        skills.append(int(op % high_level == 0))

    # shuffle the list
    random.shuffle(skills)

    return skills


def generate_uniform_times(n_operators, min_base_time, max_base_time, skills):
    # divide both times by DEF_BASE_TIME_UNIT to get the number of time units
    min_base_hours = min_base_time // c.DEF_BASE_TIME_UNIT
    max_base_hours = max_base_time // c.DEF_BASE_TIME_UNIT
    time_units = max_base_hours - min_base_hours

    times = []
    for op in range(n_operators):
        time = min_base_hours + op * time_units // (n_operators-1)
        time = time * c.DEF_BASE_TIME_UNIT
        times.append(time)

    # retrieve indexes of 1s in skills
    high_level_indexes = [i for i, x in enumerate(skills) if x == 1]

    # remove from the times list the largest len(high_level_indexes) elements and create a new list with them
    high_level_times = []
    for _ in range(len(high_level_indexes)):
        high_level_times.append(times.pop())

    # shuffle both lists
    random.shuffle(times)
    random.shuffle(high_level_times)

    # merge the two lists by inserting the high level times in the positions specified by high_level_indexes
    for i, time in zip(high_level_indexes, high_level_times):
        times.insert(i, time)

    return times


def generate_random_times(n_operators, min_base_time, max_base_time):
    # divide both times by DEF_BASE_TIME_UNIT to get the number of time units
    min_base_hours = min_base_time // c.DEF_BASE_TIME_UNIT
    max_base_hours = max_base_time // c.DEF_BASE_TIME_UNIT
    time_units = max_base_hours - min_base_hours

    # generate a list of n_operators random numbers between 0 and time_units
    times = np.random.randint(time_units, size=n_operators)
    times = (times + min_base_hours) * c.DEF_BASE_TIME_UNIT

    return times    


def generate_uniform_availabilities(n_operators, n_days, av_perc, skills):
    # generate a n_days x n_operators matrix of ones
    availabilities = np.ones((n_days, n_operators))

    unavailable_per_day = int((1 - av_perc) * n_operators)

    # for each row, set unavailable_per_day random element to 0
    for row in availabilities:
        indices = random.sample(range(n_operators), unavailable_per_day)
        for index in indices:
            row[index] = 0

    availabilities = availabilities.T.tolist()

    for i in range(len(availabilities)):
        if skills[i]:
            # convert each 0 to 1 in availabilities[i]
            availabilities[i] = [1 if x == 0 else x for x in availabilities[i]]

    return availabilities


def generate_uniform_perturbations(n_operators, n_days, time_pert, time_pert_distr):
    # generate a n_days x n_operators matrix of zeros
    perturbations = np.zeros((n_days, n_operators))

    time_pert_numbers = [0] * len(time_pert_distr)

    time_pert_numbers[1:] = [int(t * n_operators) for t in time_pert_distr[1:]]
    time_pert_numbers[0] = n_operators - sum(time_pert_numbers[1:])

    # for each row, set time_pert_numbers[i] random element to time_pert[i]
    for i, row in enumerate(perturbations):
        index = 0
        for j in range(len(time_pert_numbers)):
            row[index:index+time_pert_numbers[j]] = time_pert * j
            index += time_pert_numbers[j]

        # shuffle row
        np.random.shuffle(row)

    perturbations = perturbations.T

    return perturbations


def generate_operators(
    n_operators,
    # municipalities
    uniform_mun=True,
    municipality_prob_distr=None,
    municipalities=None,
    # skills
    uniform_skill=True,
    skill_prob_distr=c.DEF_SKILL_DISTR,
    skills=None,
    # time
    uniform_time=True,
    min_base_time=c.DEF_MIN_BASE_TIME,
    max_base_time=c.DEF_MAX_BASE_TIME,
    times=None,
    # max time
    max_time=c.DEF_MAX_TIME,
    # availability
    uniform_av=True,
    av_perc=c.DEF_AV_PERC,
    availabilities=None,
    # start time and end time
    uniform_st=True,
    uniform_et=True,
    time_pert=c.DEF_TIME_PERT,
    start_time_pert_distr=c.DEF_START_TIME_PERT_DISTR,
    end_time_pert_distr=c.DEF_END_TIME_PERT_DISTR,
    start_times=None,
    end_times=None,
    verbose=False
):
    if verbose:
        print(f"Generating {n_operators} operators")

    n_days = m.get_num_days()
    n_municipalities = m.get_num_municipalities()

    # municipalities
    if municipalities is None:
        if municipality_prob_distr is None:
            municipality_prob_distr = [1 / n_municipalities] * n_municipalities
        elif municipality_prob_distr is True:
            municipality_prob_distr = mun_prob_distr_from_comm_matrix()

        if uniform_mun:
            municipalities = generate_uniform_municipalities(n_operators, municipality_prob_distr)
        else:
            # generate municipality for each operator
            municipalities = np.random.choice(np.arange(n_municipalities), n_operators, p=municipality_prob_distr).tolist()

        municipalities = [municipality + 1 for municipality in municipalities]

    # skills
    if skills is None:
        if uniform_skill:
            skills = generate_uniform_skills(n_operators, skill_prob_distr)
        else:
            # skill: either 0 or 1 with probability skill_distr
            skills = np.random.choice(np.arange(len(skill_prob_distr)), n_operators, p=skill_prob_distr).tolist()
            
    # times
    if times is None:
        if uniform_time:
            times = generate_uniform_times(n_operators, min_base_time, max_base_time, skills)
        else:
            times = generate_random_times(n_operators, min_base_time, max_base_time)


    # max_times
    max_times = [max_time] * n_operators

    # availabilities
    if availabilities is None:
        if uniform_av:
            availabilities = generate_uniform_availabilities(n_operators, n_days, av_perc, skills)
        else:
            # availability: 1 with probability av_perc
            availabilities = np.random.choice([0, 1], (n_operators, n_days), p=[1 - av_perc, av_perc])

        # convert to int each element
        availabilities = [[int(av) for av in row] for row in availabilities]
    
    # start_times
    if start_times is None:
        start_times = [[c.DEF_OP_START_TIME] * n_days] * n_operators
        if uniform_st:
            start_time_pert = generate_uniform_perturbations(n_operators, n_days, time_pert, start_time_pert_distr)
            start_times = np.add(start_times, start_time_pert).tolist()
        else:
            # random sample from start_time_pert_distr
            start_time_pert = np.random.choice(np.arange(len(start_time_pert_distr)), n_operators, p=start_time_pert_distr).tolist()
            start_times = np.add(start_times, start_time_pert).tolist()

        # convert to int
        start_times = [[int(st) for st in row] for row in start_times]
    
    # end_times
    if end_times is None:
        end_times = [[c.DEF_OP_END_TIME] * n_days] * n_operators
        if uniform_et:
            end_time_pert = generate_uniform_perturbations(n_operators, n_days, time_pert, end_time_pert_distr)
            end_times = np.subtract(end_times, end_time_pert).tolist()
        else:
            # random sample from end_time_pert_distr
            end_time_pert = np.random.choice(np.arange(len(end_time_pert_distr)), n_operators, p=end_time_pert_distr).tolist()
            end_times = np.subtract(end_times, end_time_pert).tolist()

        # convert to int
        end_times = [[int(et) for et in row] for row in end_times]
    
    operator_values = (municipalities, skills, times, max_times, availabilities, start_times, end_times)

    operator_data = {}

    operator_data[c.N_OPERATORS] = n_operators

    for i, op_data in enumerate(c.ALL_OP_PARAMS):
        operator_data[op_data] = operator_values[i]

    u.save_JSON(operator_data, c.OPERATOR_JSON)

    if verbose:
        print(f"Generated {n_operators} operators")

# --------------- END OPERATORS --------------- #

# --------------- VISITS --------------- #

def generate_uniform_care_plan_hours(n_patients, care_plan_hours_distr):
    care_plan_hours_numbers = [int(cphd * n_patients) for cphd in care_plan_hours_distr]

    if sum(care_plan_hours_numbers) < n_patients:
        care_plan_hours_numbers[0] += n_patients - sum(care_plan_hours_numbers)

    care_plan_hours = []

    for i, cphn in enumerate(care_plan_hours_numbers):
        care_plan_hours.extend([i + 1] * cphn)

    random.shuffle(care_plan_hours)

    return care_plan_hours


def generate_care_plan_info(care_plan_hours, n_days, verbose=False):
    care_plan_visit_durations = []
    care_plan_days = []
    care_plan_times = []

    time_units = u.get_time_units()
    visit_matrix = np.zeros((n_days, time_units))

    for cph in care_plan_hours:
        if cph == 1:
            visit_durations = [60]
        elif cph == 2:
            visit_durations = [60, 60]
        elif cph == 3:
            # randomize between 3 visits of 60 minutes or 2 of 90
            if np.random.choice([0, 1]):
                visit_durations = [60, 60, 60]
            else:
                visit_durations = [90, 90]
        elif cph == 4:
            choice = np.random.choice([0, 1, 2])
            if choice == 0:
                visit_durations = [60, 60, 60, 60]
            elif choice == 1:
                visit_durations = [90, 90, 60]
            else:
                visit_durations = [120, 120]
        elif cph == 5:
            choice = np.random.choice([0, 1, 2, 3])
            if choice == 0:
                visit_durations = [60, 60, 60, 60, 60]
            elif choice == 1:
                visit_durations = [90, 90, 60, 60]
            elif choice == 2:
                visit_durations = [120, 90, 90]
            else:
                visit_durations = [150, 150]

        if verbose:
            print(f"Care plan hours: {cph}, visit durations: {visit_durations}")

        # generate as many random days (all different) as there are visits
        days = np.random.choice(np.arange(n_days), len(visit_durations), replace=False).tolist()

        if verbose:
            print(f"Days: {days}")

        care_plan_visit_durations.append(visit_durations)
        care_plan_days.append(days)

        tries = 0
        ok = False

        # while loop to be interrupted either if tries >= MAX_TRIES or if ok == True
        while tries < c.MAX_TRIES and not ok:
            # propose a time for the visits
            time = int(np.random.choice(np.arange(c.DEF_PAT_START_TIME, c.DEF_PAT_END_TIME - max(visit_durations) + 1, c.TIME_UNIT)))
            ok = True

            if verbose:
                print(f"Proposed time: {time}")
            
            # get its index in the visit matrix array
            t_index = (time - c.DEF_PAT_START_TIME) // c.TIME_UNIT

            for i in range(len(days)):
                # retrieve how many operators are available at that time
                op_av_array = s.operator_availability_matrix(days[i])

                if verbose:
                    print(f"Check for day {days[i]} and visit duration {visit_durations[i]}")
                
                # for each of the time units that the visit lasts, check if there are enough operators available
                for j in range(t_index, t_index + (visit_durations[i] // c.TIME_UNIT)):
                    if verbose:
                        print(f"Index j: {j}")
                        print(f"Number of overlapping visits in that time unit: {visit_matrix[days[i]][j]}")
                        print(f"Number of available operators in that time unit: {op_av_array[j]}")
                    if visit_matrix[days[i]][j] == op_av_array[j]:
                        ok = False
            
            if ok == False:
                tries += 1

        if tries == c.MAX_TRIES:
            print(visit_matrix)
            raise ValueError("Could not find a suitable time for the care plan")
        else:
            for i in range(len(days)):
                for j in range(t_index, t_index + (visit_durations[i] // c.TIME_UNIT)):
                    visit_matrix[days[i]][j] += 1
        
        care_plan_times.append(time)
    
    return list(zip(care_plan_visit_durations, care_plan_days, care_plan_times))


def generate_uniform_premium(n_patients, premium_perc):
    premium_numbers = [n_patients - int(premium_perc * n_patients), int(premium_perc * n_patients)]
    premium = []

    for i, pn in enumerate(premium_numbers):
        premium.extend([i] * pn)

    random.shuffle(premium)

    return premium


def generate_care_plans(
    uniform_cph=True,
    care_plan_hours_distr=c.DEF_CARE_PLAN_DISTR,
    care_plan_hours=None,
    uniform_premium=True,
    premium_perc=c.DEF_PREMIUM_PERC,
    premium=None,
    verbose=True
):
    n_patients = m.get_num_patients()
    if verbose:
        print(f"Generating {n_patients} care plans")

    # each patient gets assigned a number of care plan hours from 1 to 4
    n_days = m.get_num_days()

    if care_plan_hours is None:
        if uniform_cph:
            care_plan_hours = generate_uniform_care_plan_hours(n_patients, care_plan_hours_distr)
        else:
            care_plan_hours = np.random.choice(np.arange(len(care_plan_hours_distr)), n_patients, p=care_plan_hours_distr).tolist()

    care_plan_info = generate_care_plan_info(care_plan_hours, n_days)

    # each patient is either a premium patient or not
    if premium is None:
        if uniform_premium:
            premium = generate_uniform_premium(n_patients, premium_perc)
        else:
            premium = np.random.choice([0, 1], n_patients, p=[1 - premium_perc, premium_perc]).tolist()

    care_plans = list(zip(care_plan_info, premium))

    if verbose:
        print(f"Generated {n_patients} care plans")

    return care_plans


def random_increase_skills(n_patients, n_days, requests, skills, n_increases, verbose=False):
    if verbose:
        print(f"Increasing {n_increases} visit skills")

    to_be_increased = []

    for i in range(n_increases):
        increased = False

        while not increased:
            # pick a random patient
            patient = np.random.choice(np.arange(n_patients))
            # pick a random day
            day = np.random.choice(np.arange(n_days))
            if requests[patient][day] == 1 and skills[patient][day] == 0:
                to_be_increased.append((patient, day))
                increased = True
    
    return to_be_increased


def generate_visits_from_care_plans(
    uniform_cph=True,
    care_plan_hours_distr=c.DEF_CARE_PLAN_DISTR,
    care_plan_hours=None,
    uniform_premium=True,
    premium_perc=c.DEF_PREMIUM_PERC,
    premium=None,
    n_increases=c.DEF_N_INCREASES,
    verbose=False
):
    if verbose:
        print(f"Generating visits from care plans")

    n_patients = m.get_num_patients()
    n_days = m.get_num_days()

    care_plans = generate_care_plans(uniform_cph, care_plan_hours_distr, care_plan_hours, uniform_premium, premium_perc, premium, verbose)

    requests = []
    skills = []
    start_times = []
    end_times = []

    for i in range(n_patients):
        care_plan_info, premium = care_plans[i]
        care_plan_visit_durations, care_plan_days, care_plan_times = care_plan_info
        
        # patient requests: array of lenght n_days with 1s at indexes in care plan days and 0 otherwise
        patient_requests = [0] * n_days
        for d in care_plan_days:
            patient_requests[d] = 1
        
        patient_skills = [r * premium for r in patient_requests]
        patient_start_times = [r * care_plan_times for r in patient_requests]
        
        patient_end_times = []
        for i, r in enumerate(patient_requests):
            duration_index = 0
            if r:
                patient_end_times.append(patient_start_times[i] + care_plan_visit_durations[duration_index])
                duration_index += 1
            else:
                patient_end_times.append(0)

        requests.append(patient_requests)
        skills.append(patient_skills)
        start_times.append(patient_start_times)
        end_times.append(patient_end_times)

    to_be_increased = random_increase_skills(n_patients, n_days, requests, skills, n_increases, verbose)

    for patient, day in to_be_increased:
        skills[patient][day] = 1

    visit_values = [requests, skills, start_times, end_times]

    visit_data = {}

    for i, v in enumerate(c.VISIT_PARAMS):
        visit_data[v] = visit_values[i]

    u.save_JSON(visit_data, c.VISIT_JSON)

    if verbose:
        print(f"Generated visits")

# --------------- END VISITS --------------- #

# --------------- PREVIOUS ASSIGNMENT --------------- #

def check_feasibility(n_patients, verbose=False):
    feasible_patients = s.operator_feasible_patients()
    feasible = True

    for p in range(n_patients):
        if sum([fp[p] for fp in feasible_patients]) == 0:
            if verbose:
                print(f"Patient {p} has no feasible operator")
            feasible = False
            break
    
    return feasible, feasible_patients


def generate_previous_assignments(n_patients, n_operators, feasible_patients, ass_perc=c.DEF_ASS_PERC, verbose=False):
    n_previous_assignments = int(ass_perc * n_patients)

    # choose ass_perc random indexes in range(n_patients)
    ass_indexes = random.sample(range(n_patients), n_previous_assignments)

    previous_assignments = []
    visit_skills = m.get_visit_param(c.VISIT_SKILL)
    op_skills = m.get_operator_param(c.OP_SKILL)

    for p in range(n_patients):
        if p in ass_indexes:
            patient_potential_operators = [fp[p] for fp in feasible_patients]
            # keep only one value to 1 at random and convert all the other to 0
            indexes = [i for i, val in enumerate(patient_potential_operators) if val == 1]
            
            chosen = False
            while not chosen:
                random_index = random.choice(indexes)
                max_skill = max(visit_skills[p])
                if max_skill == op_skills[random_index] or max_skill < min([op_skills[i] for i in indexes]):
                    chosen = True

            pat_prev_ass = [1 if i == random_index else 0 for i in range(n_operators)]
        else:
            pat_prev_ass = [0] * n_operators

        previous_assignments.append(pat_prev_ass)

    if verbose:
        print(f"Generated {n_previous_assignments} previous assignments")

    return previous_assignments


def write_assignments(feasible_patients, previous_assignments):
    ass_data = {}
    ass_data[c.FEASIBLE_PATIENTS] = feasible_patients
    ass_data[c.PREV_ASS] = previous_assignments

    u.save_JSON(ass_data, c.ASS_JSON)

# --------------- END PREVIOUS ASSIGNMENT --------------- #


# --------------- TEST --------------- #

def run_test(
    n_patients,
    n_operators,
    n_days=c.DEF_NUM_DAYS,
    n_municipalities=c.DEF_NUM_MUNICIPALITIES,
    # HYPERPARAMS
    gen_hyperparams=True,
    Cw=c.DEF_C_WAGE,
    Cm=c.DEF_C_MOVEMENT,
    Co=c.DEF_C_OVERSKILL,
    Cx=c.DEF_C_EXECUTION,
    bigM=c.DEF_BIG_M,
    sigma0=c.DEF_SIGMA0,
    sigma1=c.DEF_SIGMA1,
    omega=c.DEF_OMEGA,
    # MUNICIPALITIES
    gen_municipalities=True,
    min_time_dist=c.DEF_MIN_DIST,
    max_time_dist=c.DEF_MAX_DIST,
    municipalities=None,
    # PATIENTS
    gen_patients=True, 
    pat_uniform_mun=True,
    pat_municipality_prob_distr=None,
    pat_municipalities=None,
    # OPERATORS
    gen_operators=True,
    # municipalities
    op_uniform_mun=True,
    op_municipality_prob_distr=None,
    op_municipalities=None,
    # skills
    op_uniform_skill=True,
    op_skill_prob_distr=c.DEF_SKILL_DISTR,
    op_skills=None,
    # time
    op_uniform_time=True,
    op_min_base_time=c.DEF_MIN_BASE_TIME,
    op_max_base_time=c.DEF_MAX_BASE_TIME,
    op_times=None,
    # max time
    op_max_time=c.DEF_MAX_TIME,
    # availability
    op_uniform_av=True,
    op_av_perc=c.DEF_AV_PERC,
    op_availabilities=None,
    # start time and end time
    op_uniform_st=True,
    op_uniform_et=True,
    op_time_pert=c.DEF_TIME_PERT,
    op_start_time_pert_distr=c.DEF_START_TIME_PERT_DISTR,
    op_end_time_pert_distr=c.DEF_END_TIME_PERT_DISTR,
    op_start_times=None,
    op_end_times=None,
    # VISITS
    gen_visits=True,
    uniform_cph=True,
    care_plan_hours_distr=c.DEF_CARE_PLAN_DISTR,
    care_plan_hours=None,
    uniform_premium=True,
    premium_perc=c.DEF_PREMIUM_PERC,
    premium=None,
    n_increases=c.DEF_N_INCREASES,
    # PREVIOIUS ASSIGNMENT
    gen_assignments=True,
    ass_perc=c.DEF_ASS_PERC,
    verbose=False
):
    if verbose:
        print("Running test")

    if gen_hyperparams:
        generate_hyperparams(
            Cw,
            Cm,
            Co,
            Cx,
            bigM,
            sigma0,
            sigma1,
            omega,
            n_days,
            n_municipalities,
            verbose
        )

    if gen_municipalities:
        generate_municipalities(
            n_municipalities,
            min_time_dist,
            max_time_dist,
            municipalities,
            verbose
        )

    if gen_patients:
        generate_patients(
            n_patients,
            pat_uniform_mun,
            pat_municipality_prob_distr,
            pat_municipalities,
            verbose
        )

    if gen_operators:
        generate_operators(
            n_operators,
            op_uniform_mun,
            op_municipality_prob_distr,
            op_municipalities,
            op_uniform_skill,
            op_skill_prob_distr,
            op_skills,
            op_uniform_time,
            op_min_base_time,
            op_max_base_time,
            op_times,
            op_max_time,
            op_uniform_av,
            op_av_perc,
            op_availabilities,
            op_uniform_st,
            op_uniform_et,
            op_time_pert,
            op_start_time_pert_distr,
            op_end_time_pert_distr,
            op_start_times,
            op_end_times,
            verbose
        )

    feasible = False
    while not feasible:
        if gen_visits:
            generate_visits_from_care_plans(
                uniform_cph,
                care_plan_hours_distr,
                care_plan_hours,
                uniform_premium,
                premium_perc,
                premium,
                n_increases,
                verbose
            )

        feasible, feasible_patients = check_feasibility(n_patients, verbose)

        if not feasible:
            if verbose:
                print("Infeasible instance, generating new visits")
        else:
            if verbose:
                print("Feasible instance")
                
    if gen_assignments:
        previous_assignments = generate_previous_assignments(n_patients, n_operators, feasible_patients, ass_perc, verbose)

        write_assignments(feasible_patients, previous_assignments)

    obj, opt_gap, exec_time = p.run(verbose)

    return obj, opt_gap, exec_time


def report_stats(archive_folder=c.DEF_ARCHIVE_FOLDER, file_name=c.OP_STATS_CSV, verbose=False):
    if verbose:
        print("Reporting stats")

    n_operators = m.get_num_operators()

    op_skill = m.get_operator_param(c.OP_SKILL)
    n_overskilled_operators = sum(op_skill)     # skills can only be 0 and 1

    op_time = m.get_operator_param(c.OP_TIME)
    op_max_time = m.get_operator_param(c.OP_MAX_TIME)

    if verbose:
        print("Retrieved operator parameters")

    # operator workload
    op_workload = s.operator_workload()
    if verbose:
        print("Retrieved operator workload")

    # operator overtime
    op_overtime = s.operator_overtime()
    if verbose:
        print("Retrieved operator overtime")

    # operator overskill
    op_overskill = s.operator_overskill()
    if verbose:
        print("Retrieved operator overskill")

    # travel time
    op_travel_time, op_inter_mun_travel_time, _, _ = s.operator_travel_time()
    if verbose:
        print("Retrieved operator travel time")

    # number of assigned visits and patients per operator
    op_assigned_patients = s.operator_assignment()
    op_n_assigned_patients = [len(a) for a in op_assigned_patients]
    if verbose:
        print("Retrieved operator assignment")
    
    op_total_visits = s.operator_total_visits()
    op_not_executed_visits = s.operator_not_executed_visits()
    if verbose:
        print("Retrieved operator visits")

    # create CSV file
    if verbose:
        print(f"Creating CSV file {file_name}")
    
    with open(file_name, 'w') as f:
        writer = csv.writer(f)

        # write header
        writer.writerow(c.STATS_HEADER)

        # write operator rows
        for o in range(n_operators):
            writer.writerow([
                o,
                op_skill[o],
                op_time[o],
                op_max_time[o],
                op_n_assigned_patients[o],
                op_total_visits[o],
                op_not_executed_visits[o],
                op_workload[o],
                op_overtime[o],
                op_travel_time[o],
                op_inter_mun_travel_time[o],
                f"{op_overskill[o][0]} - ({op_overskill[o][1]:.2f})%",
                f"{op_overskill[o][2]} - ({op_overskill[o][3]:.2f})%"
            ])

        # insert an empty row
        writer.writerow([])

        mean_row = [
            'mean',
            '-',
            round(np.mean(op_time), 2),
            round(np.mean(op_max_time), 2),
            round(np.mean(op_n_assigned_patients), 2),
            round(np.mean(op_total_visits), 2),
            round(np.mean(op_not_executed_visits), 2),
            round(np.mean(op_workload), 2),
            round(np.mean(op_overtime), 2),
            round(np.mean(op_travel_time), 2),
            round(np.mean(op_inter_mun_travel_time), 2),
            f"{round(np.sum(o[0] for o in op_overskill) / n_overskilled_operators, 2)} - ({round(np.sum(o[1] for o in op_overskill) / n_overskilled_operators, 2)}%)",
            f"{round(np.sum(o[2] for o in op_overskill) / n_overskilled_operators, 2)} - ({round(np.sum(o[3] for o in op_overskill) / n_overskilled_operators, 2)}%)"
        ]

        min_row = [
            'min',
            '-',
            np.min(op_time),
            '-',
            np.min(op_n_assigned_patients),
            np.min(op_total_visits),
            np.min(op_not_executed_visits),
            np.min(op_workload),
            np.min(op_overtime),
            np.min(op_travel_time),
            np.min(op_inter_mun_travel_time),
            f"{np.min([o[0] for o in op_overskill if op_skill[op_overskill.index(o)] > 0])} - ({np.min([o[1] for o in op_overskill if op_skill[op_overskill.index(o)] > 0]):.2f}%)",
            f"{np.min([o[2] for o in op_overskill if op_skill[op_overskill.index(o)] > 0])} - ({np.min([o[3] for o in op_overskill if op_skill[op_overskill.index(o)] > 0]):.2f}%)"
        ]
            
        f_quartile_row = [
            '25th percentile',
            '-',
            round(np.percentile(op_time, 25), 2),
            '-',
            round(np.percentile(op_n_assigned_patients, 25), 2),
            round(np.percentile(op_total_visits, 25), 2),
            round(np.percentile(op_not_executed_visits, 25), 2),
            round(np.percentile(op_workload, 25), 2),
            round(np.percentile(op_overtime, 25), 2),
            round(np.percentile(op_travel_time, 25), 2),
            round(np.percentile(op_inter_mun_travel_time, 25), 2),
            f"{round(np.percentile([o[0] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 25), 2)} - ({round(np.percentile([o[1] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 25), 2)}%)",
            f"{round(np.percentile([o[2] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 25), 2)} - ({round(np.percentile([o[3] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 25), 2)}%)"
        ]
        
        t_quartile_row = [
            '75th percentile',
            '-',
            round(np.percentile(op_time, 75), 2),
            '-',
            round(np.percentile(op_n_assigned_patients, 75), 2),
            round(np.percentile(op_total_visits, 75), 2),
            round(np.percentile(op_not_executed_visits, 75), 2),
            round(np.percentile(op_workload, 75), 2),
            round(np.percentile(op_overtime, 75), 2),
            round(np.percentile(op_travel_time, 75), 2),
            round(np.percentile(op_inter_mun_travel_time, 75), 2),
            f"{round(np.percentile([o[0] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 75), 2)} - ({round(np.percentile([o[1] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 75), 2)}%)",
            f"{round(np.percentile([o[2] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 75), 2)} - ({round(np.percentile([o[3] for o in op_overskill if op_skill[op_overskill.index(o)] > 0], 75), 2)}%)"
        ]

        max_row = [
            'max',
            '-',
            np.max(op_time),
            '-',
            np.max(op_n_assigned_patients),
            np.max(op_total_visits),
            np.max(op_not_executed_visits),
            np.max(op_workload),
            np.max(op_overtime),
            np.max(op_travel_time),
            np.max(op_inter_mun_travel_time),
            f"{np.max([o[0] for o in op_overskill if op_skill[op_overskill.index(o)] > 0])} - ({np.max([o[1] for o in op_overskill if op_skill[op_overskill.index(o)] > 0]):.2f}%)",
            f"{np.max([o[2] for o in op_overskill if op_skill[op_overskill.index(o)] > 0])} - ({np.max([o[3] for o in op_overskill if op_skill[op_overskill.index(o)] > 0]):.2f}%)"
        ]

        total_row = [
            'total',
            '-',
            np.sum(op_time),
            np.sum(op_max_time),
            np.sum(op_n_assigned_patients),
            np.sum(op_total_visits),
            np.sum(op_not_executed_visits),
            np.sum(op_workload),
            np.sum(op_overtime),
            np.sum(op_travel_time),
            np.sum(op_inter_mun_travel_time),
            np.sum(o[0] for o in op_overskill),
            np.sum(o[2] for o in op_overskill)
        ]

        writer.writerow(mean_row)
        writer.writerow(min_row)
        writer.writerow(f_quartile_row)
        writer.writerow(t_quartile_row)
        writer.writerow(max_row)
        writer.writerow(total_row)

    archive_path = c.ARCHIVE_FOLDER + archive_folder

    if verbose:
        print(f"Report completed. Saving it in {archive_path}")

    # if directory does not exist, create it
    if not os.path.exists(archive_path):
        os.makedirs(archive_path)

    # move file to archive folder
    os.system(f"mv {file_name} {archive_path}")

    if verbose:
        print("Report saved")

    return mean_row, total_row


def execute_test(
    n_patients,
    n_operators,
    n_days=c.DEF_NUM_DAYS,
    n_municipalities=c.DEF_NUM_MUNICIPALITIES,
    # HYPERPARAMS
    gen_hyperparams=True,
    Cw=c.DEF_C_WAGE,
    Cm=c.DEF_C_MOVEMENT,
    Co=c.DEF_C_OVERSKILL,
    Cx=c.DEF_C_EXECUTION,
    bigM=c.DEF_BIG_M,
    sigma0=c.DEF_SIGMA0,
    sigma1=c.DEF_SIGMA1,
    omega=c.DEF_OMEGA,
    # MUNICIPALITIES
    gen_municipalities=True,
    min_time_dist=c.DEF_MIN_DIST,
    max_time_dist=c.DEF_MAX_DIST,
    municipalities=None,
    # PATIENTS
    gen_patients=True, 
    pat_uniform_mun=True,
    pat_municipality_prob_distr=None,
    pat_municipalities=None,
    # OPERATORS
    gen_operators=True,
    # municipalities
    op_uniform_mun=True,
    op_municipality_prob_distr=None,
    op_municipalities=None,
    # skills
    op_uniform_skill=True,
    op_skill_prob_distr=c.DEF_SKILL_DISTR,
    op_skills=None,
    # time
    op_uniform_time=True,
    op_min_base_time=c.DEF_MIN_BASE_TIME,
    op_max_base_time=c.DEF_MAX_BASE_TIME,
    op_times=None,
    # max time
    op_max_time=c.DEF_MAX_TIME,
    # availability
    op_uniform_av=True,
    op_av_perc=c.DEF_AV_PERC,
    op_availabilities=None,
    # start time and end time
    op_uniform_st=True,
    op_uniform_et=True,
    op_time_pert=c.DEF_TIME_PERT,
    op_start_time_pert_distr=c.DEF_START_TIME_PERT_DISTR,
    op_end_time_pert_distr=c.DEF_END_TIME_PERT_DISTR,
    op_start_times=None,
    op_end_times=None,
    # VISITS
    gen_visits=True,
    uniform_cph=True,
    care_plan_hours_distr=c.DEF_CARE_PLAN_DISTR,
    care_plan_hours=None,
    uniform_premium=True,
    premium_perc=c.DEF_PREMIUM_PERC,
    premium=None,
    n_increases=c.DEF_N_INCREASES,
    # PREVIOIUS ASSIGNMENT
    gen_assignments=True,
    ass_perc=c.DEF_ASS_PERC,
    # report
    archive_folder=c.DEF_ARCHIVE_FOLDER,
    file_name=c.OP_STATS_CSV,
    verbose=False
):
    if verbose:
        print("Executing test")

    obj = False    
    while obj == False:
        obj, opt_gap, exec_time = run_test(
            n_patients,
            n_operators,
            n_days,
            n_municipalities,
            # HYPERPARAMS
            gen_hyperparams,
            Cw,
            Cm,
            Co,
            Cx,
            bigM,
            sigma0,
            sigma1,
            omega,
            # MUNICIPALITIES
            gen_municipalities,
            min_time_dist,
            max_time_dist,
            municipalities,
            # PATIENTS
            gen_patients,
            pat_uniform_mun,
            pat_municipality_prob_distr,
            pat_municipalities,
            # OPERATORS
            gen_operators,
            # municipalities
            op_uniform_mun,
            op_municipality_prob_distr,
            op_municipalities,
            # skills
            op_uniform_skill,
            op_skill_prob_distr,
            op_skills,
            # time
            op_uniform_time,
            op_min_base_time,
            op_max_base_time,
            op_times,
            # max time
            op_max_time,
            # availability
            op_uniform_av,
            op_av_perc,
            op_availabilities,
            # start time and end time
            op_uniform_st,
            op_uniform_et,
            op_time_pert,
            op_start_time_pert_distr,
            op_end_time_pert_distr,
            op_start_times,
            op_end_times,
            # VISITS
            gen_visits,
            uniform_cph,
            care_plan_hours_distr,
            care_plan_hours,
            uniform_premium,
            premium_perc,
            premium,
            n_increases,
            # PREVIOIUS ASSIGNMENT
            gen_assignments,
            ass_perc,
            verbose
        )

    # archive all JSONs in archive_folder
    for j in c.INPUT_JSON_PATHS:
        u.archive_file(j, archive_folder)
    
    u.archive_file(c.OUTPUT_JSON, archive_folder)
    u.archive_file(c.SETUP_FILE, archive_folder)

    mean_row, total_row = report_stats(archive_folder=archive_folder, file_name=file_name, verbose=verbose)

    if verbose:
        print("Test completed")
        print()
    
    return mean_row, total_row, obj, opt_gap, exec_time


def execute_batch_tests(
    n_tests,
    n_patients,
    n_operators,
    n_days=c.DEF_NUM_DAYS,
    n_municipalities=c.DEF_NUM_MUNICIPALITIES,
    # HYPERPARAMS
    gen_hyperparams=True,
    Cw=c.DEF_C_WAGE,
    Cm=c.DEF_C_MOVEMENT,
    Co=c.DEF_C_OVERSKILL,
    Cx=c.DEF_C_EXECUTION,
    bigM=c.DEF_BIG_M,
    sigma0=c.DEF_SIGMA0,
    sigma1=c.DEF_SIGMA1,
    omega=c.DEF_OMEGA,
    # MUNICIPALITIES
    gen_municipalities=True,
    min_time_dist=c.DEF_MIN_DIST,
    max_time_dist=c.DEF_MAX_DIST,
    municipalities=None,
    # PATIENTS
    gen_patients=True, 
    pat_uniform_mun=True,
    pat_municipality_prob_distr=None,
    pat_municipalities=None,
    # OPERATORS
    gen_operators=True,
    # municipalities
    op_uniform_mun=True,
    op_municipality_prob_distr=None,
    op_municipalities=None,
    # skills
    op_uniform_skill=True,
    op_skill_prob_distr=c.DEF_SKILL_DISTR,
    op_skills=None,
    # time
    op_uniform_time=True,
    op_min_base_time=c.DEF_MIN_BASE_TIME,
    op_max_base_time=c.DEF_MAX_BASE_TIME,
    op_times=None,
    # max time
    op_max_time=c.DEF_MAX_TIME,
    # availability
    op_uniform_av=True,
    op_av_perc=c.DEF_AV_PERC,
    op_availabilities=None,
    # start time and end time
    op_uniform_st=True,
    op_uniform_et=True,
    op_time_pert=c.DEF_TIME_PERT,
    op_start_time_pert_distr=c.DEF_START_TIME_PERT_DISTR,
    op_end_time_pert_distr=c.DEF_END_TIME_PERT_DISTR,
    op_start_times=None,
    op_end_times=None,
    # VISITS
    gen_visits=True,
    uniform_cph=True,
    care_plan_hours_distr=c.DEF_CARE_PLAN_DISTR,
    care_plan_hours=None,
    uniform_premium=True,
    premium_perc=c.DEF_PREMIUM_PERC,
    premium=None,
    n_increases=c.DEF_N_INCREASES,
    # PREVIOIUS ASSIGNMENT
    gen_assignments=True,
    ass_perc=c.DEF_ASS_PERC,
    # report
    archive_folder=c.DEF_ARCHIVE_FOLDER,
    file_name=c.OP_STATS_CSV,
    # summary
    summary_file_name=c.SUMMARY_CSV,
    verbose=False
):
    archive_folder_path = c.ARCHIVE_FOLDER + archive_folder
    total_obj = []
    total_opt_gap = []
    total_exec_time = []

    total_mean_stats = []
    total_total_stats = []

    if verbose:
        print(f"Executing tests for {archive_folder}")

    for test in range(n_tests):
        if verbose:
            print(f"Executing test {test+1} of {n_tests}")

        test_archive_folder = archive_folder + f"{test}/"

        mean_row, total_row, obj, opt_gap, exec_time = execute_test(
            n_patients,
            n_operators,
            n_days,
            n_municipalities,
            # HYPERPARAMS
            gen_hyperparams,
            Cw,
            Cm,
            Co,
            Cx,
            bigM,
            sigma0,
            sigma1,
            omega,
            # MUNICIPALITIES
            gen_municipalities,
            min_time_dist,
            max_time_dist,
            municipalities,
            # PATIENTS
            gen_patients, 
            pat_uniform_mun,
            pat_municipality_prob_distr,
            pat_municipalities,
            # OPERATORS
            gen_operators,
            # municipalities
            op_uniform_mun,
            op_municipality_prob_distr,
            op_municipalities,
            # skills
            op_uniform_skill,
            op_skill_prob_distr,
            op_skills,
            # time
            op_uniform_time,
            op_min_base_time,
            op_max_base_time,
            op_times,
            # max time
            op_max_time,
            # availability
            op_uniform_av,
            op_av_perc,
            op_availabilities,
            # start time and end time
            op_uniform_st,
            op_uniform_et,
            op_time_pert,
            op_start_time_pert_distr,
            op_end_time_pert_distr,
            op_start_times,
            op_end_times,
            # VISITS
            gen_visits,
            uniform_cph,
            care_plan_hours_distr,
            care_plan_hours,
            uniform_premium,
            premium_perc,
            premium,
            n_increases,
            # PREVIOIUS ASSIGNMENT
            gen_assignments,
            ass_perc,
            # report
            test_archive_folder,
            file_name,
            verbose
        )

        if mean_row is False:
            total_no_solutions += 1
            total_mean_stats.append(False)
            total_total_stats.append(False)
        else:
            total_mean_stats.append(mean_row)
            total_total_stats.append(total_row)

        total_obj.append(obj)
        total_opt_gap.append(opt_gap)
        total_exec_time.append(exec_time)

        if verbose:
            print(f"Test {test+1} of {n_tests} completed")

    # create a CSV called "summary.csv" in archive_folder
    if verbose:
        print(f"Creating summary {summary_file_name}")

    summary_file_path = archive_folder_path + summary_file_name

    # create CSV file
    if not os.path.exists(summary_file_path):
        os.system(f"touch {summary_file_path}")
    
    with open(summary_file_path, 'w') as f:
        writer = csv.writer(f)

        writer.writerow(c.SUMMARY_HEADER)

        for i in range(n_tests):
            writer.writerow([i] + total_mean_stats[i] + [total_obj[i], total_opt_gap[i], total_exec_time[i]])
            
        writer.writerow([])

        for i in range(n_tests):
            writer.writerow([i] + total_total_stats[i] + [total_obj[i], total_opt_gap[i], total_exec_time[i]])

    if verbose:
        print(f"Summary {summary_file_name} created")
        print()
        print()
    
    return True
