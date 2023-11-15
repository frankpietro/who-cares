import src.constants as c
import src.utilities as u
import src.stats as s
import src.manipulation as m

import numpy as np

from scipy.spatial import distance_matrix


# retrieve every slot where a visit can be scheduled
def daily_operator_slots(operator, patient, duration, day, daily_schedule, input_data, verbose=False):
    op_index = input_data['numPatients'] + operator

    if verbose:
        print(f"----- DAY {day} -----")
        print(f"Operator {operator} schedule: {daily_schedule}")
    
    slots = []

    # if patient is alrewady visited on that day, skip
    if any([x[0] == patient for x in daily_schedule]):
        if verbose:
            print("Already visited")
        
        return slots

    if input_data['operatorAvailability'][operator][day] == 0:
        if verbose:
            print("Operator not available")
        
        return slots
        
    # if there are no visits on that day, each moment is free
    elif len(daily_schedule) == 0:
        if verbose:
            print(f"No visits scheduled for operator {operator} on day {day}")
        
        slot_start = input_data['operatorStartTime'][operator][day] + input_data['commutingTime'][op_index][patient]
        slot_end = input_data['operatorEndTime'][operator][day] - input_data['commutingTime'][patient][op_index] - duration

        slot_start = np.ceil(slot_start / c.TIME_UNIT) * c.TIME_UNIT
        slot_end = np.floor(slot_end / c.TIME_UNIT) * c.TIME_UNIT

        if slot_start <= slot_end:
            slot_price = input_data['operatorWage'][operator] * duration + input_data['commutingCost'] * (input_data['commutingTime'][op_index][patient] + input_data['commutingTime'][patient][op_index])
            slot_price = np.round(slot_price, 2)

            if verbose:
                print(f"Slot: {slot_start} - {slot_end}, at {slot_price}")
            
            slots.append((slot_start, slot_end, slot_price))
        
        else:
            if verbose:
                print(f"Slot: not enough time ({slot_start} - {slot_end})")

    # otherwise, check for free slots
    else:
        # first slot
        first_slot_start = input_data['operatorStartTime'][operator][day] + input_data['commutingTime'][op_index][patient]
        first_slot_end = daily_schedule[0][c.START_TIME] - input_data['commutingTime'][patient][op_index] - duration

        # round to 15 by excess first slot start
        first_slot_start = np.ceil(first_slot_start / c.TIME_UNIT) * c.TIME_UNIT
        # round to 15 by defect first slot end
        first_slot_end = np.floor(first_slot_end / c.TIME_UNIT) * c.TIME_UNIT
        
        if first_slot_start <= first_slot_end:
            first_patient = daily_schedule[0][c.PATIENT]
            first_slot_price = input_data['operatorWage'][operator] * duration + input_data['commutingCost'] * (input_data['commutingTime'][op_index][patient] + input_data['commutingTime'][patient][first_patient] - input_data['commutingTime'][op_index][first_patient])
            first_slot_price = np.round(first_slot_price, 2)

            if verbose:
                print(f"First slot: {first_slot_start} - {first_slot_end} at {first_slot_price}")
            
            slots.append((first_slot_start, first_slot_end, first_slot_price))
        
        else:
            if verbose:
                print(f"First slot: not enough time ({first_slot_start} - {first_slot_end})")

        # central slots
        for i in range(len(daily_schedule) - 1):
            previous_patient = daily_schedule[i][c.PATIENT]
            next_patient = daily_schedule[i+1][c.PATIENT]

            slot_start = daily_schedule[i][c.END_TIME] + input_data['commutingTime'][previous_patient][patient]
            slot_end = daily_schedule[i+1][c.START_TIME] - input_data['commutingTime'][patient][next_patient] - duration
            
            slot_start = np.ceil(slot_start / c.TIME_UNIT) * c.TIME_UNIT
            slot_end = np.floor(slot_end / c.TIME_UNIT) * c.TIME_UNIT

            if slot_start <= slot_end:
                slot_price = input_data['operatorWage'][operator] * duration + input_data['commutingCost'] * (input_data['commutingTime'][previous_patient][patient] + input_data['commutingTime'][patient][next_patient] - input_data['commutingTime'][previous_patient][next_patient])
                slot_price = np.round(slot_price, 2)

                if verbose:
                    print(f"Slot {i+1}: {slot_start} - {slot_end} at {slot_price}")
                
                slots.append((slot_start, slot_end, slot_price))

            else:
                if verbose:
                    print(f"Slot {i+1}: not enough time ({slot_start} - {slot_end})")

        # last slot
        last_patient = daily_schedule[-1][c.PATIENT]

        last_slot_start = daily_schedule[-1][c.END_TIME] + input_data['commutingTime'][last_patient][patient]
        last_slot_end = input_data['operatorEndTime'][operator][day] - input_data['commutingTime'][patient][op_index] - duration

        last_slot_start = np.ceil(last_slot_start / c.TIME_UNIT) * c.TIME_UNIT
        last_slot_end = np.floor(last_slot_end / c.TIME_UNIT) * c.TIME_UNIT

        if last_slot_start <= last_slot_end:
            last_slot_price = input_data['operatorWage'][operator] * duration + input_data['commutingCost'] * (input_data['commutingTime'][last_patient][patient] + input_data['commutingTime'][patient][op_index] - input_data['commutingTime'][last_patient][op_index])
            last_slot_price = np.round(last_slot_price, 2)
            
            if verbose:
                print(f"Last slot: {last_slot_start} - {last_slot_end} at {last_slot_price}")
            
            slots.append((last_slot_start, last_slot_end, last_slot_price))

        else:
            if verbose:
                print(f"Last slot: not enough time ({last_slot_start} - {last_slot_end})")

    return slots


def new_visit_existing_patient(p_id, skill, duration, input_data, output_data, verbose=False):
    if verbose:
        print(f"----- PATIENT {p_id}, SKILL {skill}, DURATION {duration} -----")

    # retrieve empty slots in the schedule of their assigned operator
    assigned_operator = output_data['assignment'][p_id].index(1)

    operators = [i for i in range(input_data['numOperators']) if input_data['operatorSkill'][i] >= skill]
    schedules = {}
    for o in operators:
        schedules[o] = s.operator_schedule(input_data, output_data, o, False)

    free_slots_same_op = {}
    free_slots_new_op = {}

    # if skill mismatch, propose just other operators
    if skill > input_data['operatorSkill'][assigned_operator]:
        if verbose:
            print("Skill mismatch")
            print("Visit will be executed by a different operator")
        
        for d in range(input_data['numDays']):
            free_slots_new_op[d] = {}
            for o in operators:
                daily_schedule = [x for x in schedules[o] if x[1] == d]
                free_slots_new_op[d][o] = daily_operator_slots(o, p_id, duration, d, daily_schedule, input_data, verbose)
        
        return free_slots_same_op, free_slots_new_op
    
    # otherwise, propose slots from assigned operator
    else:
        for d in range(input_data['numDays']):
            free_slots_same_op[d] = {}
            free_slots_new_op[d] = {}

            daily_op_schedule = [x for x in schedules[assigned_operator] if x[1] == d]
            free_slots_same_op[d][assigned_operator] = daily_operator_slots(assigned_operator, p_id, duration, d, daily_op_schedule, input_data, verbose)

            for o in range(input_data['numOperators']):
                if o != assigned_operator:
                    daily_schedule = [x for x in schedules[o] if x[1] == d and o != assigned_operator]
                    free_slots_new_op[d][o] = daily_operator_slots(o, p_id, duration, d, daily_schedule, input_data, verbose)

        return free_slots_same_op, free_slots_new_op


def new_visit_new_patient(p_lat, p_lon, skill, duration, input_data, output_data, verbose=False):
    # create new JSON for commuting data, adding one last row and last column to it with the new patient
    lats = input_data['patientLatitude'] + input_data['operatorLatitude'] + [p_lat]
    lons = input_data['patientLongitude'] + input_data['operatorLongitude'] + [p_lon]
    
    # use lats and lons to compute the values of last row and last column
    input_data['commutingTime'] = distance_matrix(np.array([lats, lons]).T, np.array([lats, lons]).T).tolist()

    # retrieve empty slots in the schedule of all operators
    free_slots = {}

    # retrieve all operators with skill >= skill required
    operators = [i for i in range(input_data['numOperators']) if input_data['operatorSkill'][i] >= skill]
    schedules = {}
    for o in operators:
        schedules[o] = s.operator_schedule(input_data, output_data, o, False)    

    for d in range(input_data['numDays']):
        free_slots[d] = {}
        for o in operators:
            daily_schedule = [x for x in schedules[o] if x[1] == d]
            free_slots[d][o] = daily_operator_slots(o, -1, duration, d, daily_schedule, input_data, verbose)
    
    return free_slots


def change_operator_availability(operator, day, from_time, to_time, input_data, output_data, verbose=False):
    # change the availability of the operator in the day with new start and end time
    
    # retrieve visits that can no longer be executed by the operator
    subschedule = s.operator_subschedule(input_data, output_data, operator, day, from_time, to_time, False)

    # these visits need to be rescheduled