import src.constants as c
import src.utilities as u

import src.manipulation as m

import numpy as np


# --------------- OPERATORS --------------- #

def operator_assignment(operator=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} assignment --")

        assignment = m.get_assignment(operator=operator)

        # get array with indexes of ones of assignment array
        assigned_patients = [index for index, value in enumerate(assignment) if value == 1]
    
        if verbose:
            # no patients assigned
            if len(assigned_patients) == 0:
                print(f"No patients assigned to operator {operator}")
            # one patient assigned
            elif len(assigned_patients) == 1:
                print(f"Patient {assigned_patients[0]}")
            # more than one patient assigned
            else:
                print(f"Patients {assigned_patients[0]}", end='')
                for p in assigned_patients[1:]:
                    print(f", {p}", end='')
            
            print()

        return assigned_patients
    
    else:
        if verbose:
            print("-- All operators assignment --")
        
        operators = m.get_num_operators()

        assignments = []
        for o in range(operators):
            assignment = operator_assignment(o, verbose=False)
            if verbose:
                print(f"Operator {o}: {assignment}")
            assignments.append(assignment)
        
        return assignments


def operator_unit_wage(operator=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} unit wage --")

        # wage multiplier: sigma0 + op_skill * sigma1
        op_skill = m.get_operator_param(c.OP_SKILL, operator)
        sigma0 = m.get_numeric_param(c.SIGMA0)
        sigma1 = m.get_numeric_param(c.SIGMA1)

        unit_wage = sigma0 + op_skill * sigma1

        if verbose:
            print(f"Operator skill: {op_skill}")
            print(f"Sigma0: {sigma0}")
            print(f"Sigma1: {sigma1}")
            print(f"Unit wage: {unit_wage}€")
        
        return unit_wage
    
    else:
        if verbose:
            print("-- All operators unit wage --")
        
        operators = m.get_num_operators()

        unit_wages = []
        for o in range(operators):
            unit_wage = operator_unit_wage(o, verbose=False)
            if verbose:
                print(f"Operator {o}: {unit_wage}€")
            unit_wages.append(unit_wage)
            
        return unit_wages


def operator_not_executed_schedule(operator=None, input_data=None, output_data=None, verbose=False, condensed=True):
    if input_data is None:
        input_data = u.merge_JSON_files(c.INPUT_JSON_PATHS)
    
    if output_data is None:
        output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    
    days = m.get_num_days()
    patients = m.get_num_patients()

    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} schedule --")

        schedule = []

        for d in range(days):
            for p in range(patients):
                if input_data[c.VISIT_REQUEST][p][d] == 1 and output_data[c.ASSIGNMENT][p][operator] == 1 and output_data[c.VISIT_EXEC][operator][p][d] == 0:
                    # order of info: patient, day, skill, start time, end time
                    visit_info = (p, d, input_data[c.VISIT_SKILL][p][d], input_data[c.VISIT_START_TIME][p][d], input_data[c.VISIT_END_TIME][p][d])
                    
                    schedule.append(visit_info)
        
        schedule.sort(key=lambda x: (x[c.SCH_DAY], x[c.SCH_START_TIME]))

        if verbose:
            for d in range(days):
                print(f"Day {d}: ", end='')

                # daily schedule
                ds = [x for x in schedule if x[c.SCH_DAY] == d]
                if condensed:
                    print("[", end='')
                    for i in range(len(ds)):
                        if i == len(ds) - 1:
                            print(f"{ds[i][c.SCH_START_TIME]} - {ds[i][c.SCH_END_TIME]}", end='')
                        else:
                            print(f"{ds[i][c.SCH_START_TIME]} - {ds[i][c.SCH_END_TIME]}", end=' --> ')
                    print("]")
                
                else:
                    # cases
                    if len(ds) == 0:
                        print("No visits")
                    else:
                        for i in range(len(ds)):
                            if i == len(ds) - 1:
                                print(f"Patient {ds[i][c.SCH_PATIENT]} with skill {ds[i][c.SCH_SKILL]} on day {ds[i][c.SCH_DAY]} from {ds[i][c.SCH_START_TIME]} to {ds[i][c.SCH_END_TIME]}")
                            else:
                                print(f"Patient {ds[i][c.SCH_PATIENT]} with skill {ds[i][c.SCH_SKILL]} on day {ds[i][c.SCH_DAY]} from {ds[i][c.SCH_START_TIME]} to {ds[i][c.SCH_END_TIME]}", end=', ')

            print()        

        return schedule
    
    else:
        if verbose:
            print("-- All operators schedule --")

        operators = m.get_num_operators()
        input_data = u.merge_JSON_files(c.INPUT_JSON_PATHS)
        output_data = u.retrieve_JSON(c.OUTPUT_JSON)
        
        schedules = []
        for o in range(operators):
            schedule = operator_not_executed_schedule(o, input_data, output_data, verbose=False)
            if verbose:
                print(f"Operator {o}: {schedule}")
            schedules.append(schedule)

        return schedules


def operator_schedule(operator=None, input_data=None, output_data=None, verbose=False, condensed=True):
    if input_data is None:
        input_data = u.merge_JSON_files(c.INPUT_JSON_PATHS)
    
    if output_data is None:
        output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    
    days = m.get_num_days()
    patients = m.get_num_patients()

    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} schedule --")

        schedule = []

        for d in range(days):
            for p in range(patients):
                if output_data[c.VISIT_EXEC][operator][p][d] == 1:
                    # order of info: patient, day, skill, start time, end time
                    visit_info = (p, d, input_data[c.VISIT_SKILL][p][d], input_data[c.VISIT_START_TIME][p][d], input_data[c.VISIT_END_TIME][p][d])
                    
                    schedule.append(visit_info)
        
        schedule.sort(key=lambda x: (x[c.SCH_DAY], x[c.SCH_START_TIME]))

        if verbose:
            for d in range(days):
                print(f"Day {d}: ", end='')

                # daily schedule
                ds = [x for x in schedule if x[c.SCH_DAY] == d]
                if condensed:
                    print("[", end='')
                    for i in range(len(ds)):
                        if i == len(ds) - 1:
                            print(f"{ds[i][c.SCH_START_TIME]} - {ds[i][c.SCH_END_TIME]}", end='')
                        else:
                            print(f"{ds[i][c.SCH_START_TIME]} - {ds[i][c.SCH_END_TIME]}", end=' --> ')
                    print("]")
                
                else:
                    # cases
                    if len(ds) == 0:
                        print("No visits")
                    else:
                        for i in range(len(ds)):
                            if i == len(ds) - 1:
                                print(f"Patient {ds[i][c.SCH_PATIENT]} with skill {ds[i][c.SCH_SKILL]} on day {ds[i][c.SCH_DAY]} from {ds[i][c.SCH_START_TIME]} to {ds[i][c.SCH_END_TIME]}")
                            else:
                                print(f"Patient {ds[i][c.SCH_PATIENT]} with skill {ds[i][c.SCH_SKILL]} on day {ds[i][c.SCH_DAY]} from {ds[i][c.SCH_START_TIME]} to {ds[i][c.SCH_END_TIME]}", end=', ')

            print()        

        return schedule
    
    else:
        if verbose:
            print("-- All operators schedule --")

        operators = m.get_num_operators()
        input_data = u.merge_JSON_files(c.INPUT_JSON_PATHS)
        output_data = u.retrieve_JSON(c.OUTPUT_JSON)
        
        schedules = []
        for o in range(operators):
            schedule = operator_schedule(o, input_data, output_data, verbose=False)
            if verbose:
                print(f"Operator {o}: {schedule}")
            schedules.append(schedule)

        return schedules


def operator_subschedule(operator, day, from_time=c.DEF_OP_START_TIME, to_time=c.DEF_OP_END_TIME, verbose=False):
    if verbose:
        print(f"-- Operator {operator} subschedule for day {day} from {from_time} to {to_time} --")
    
    schedule = operator_schedule(operator, verbose=False)
    subschedule = [x for x in schedule if x[c.SCH_DAY] == day and x[c.SCH_END_TIME] >= from_time and x[c.SCH_START_TIME] <= to_time]
    
    if verbose:
        print("[", end='')
        for i in range(len(subschedule)):
            if i == len(subschedule) - 1:
                print(f"{subschedule[i][c.SCH_START_TIME]} - {subschedule[i][c.SCH_END_TIME]}", end='')
            else:
                print(f"{subschedule[i][c.SCH_START_TIME]} - {subschedule[i][c.SCH_END_TIME]}", end=' --> ')
        print("]")

    return subschedule


def operator_travel_time(
    operator=None,
    commuting_times=None,
    pat_municipalities=None,
    op_municipality=None,
    op_schedule=None,
    verbose=False
):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} travel time --")

        days = m.get_num_days()

        if commuting_times is None:
            commuting_times = m.get_commuting_times()
        
        if pat_municipalities is None:
            pat_municipalities = m.get_patient_param(c.PAT_MUNICIPALITY)
        
        if op_municipality is None:
            op_municipality = m.get_operator_param(c.OP_MUNICIPALITY, operator)

        travel_time = 0
        inter_only_travel_time = 0

        travel_count = [0,0]

        travel_durations = {}

        if op_schedule is None:
            op_schedule = operator_schedule(operator, verbose=False)

        for d in range(days):
            subschedule = [x for x in op_schedule if x[c.SCH_DAY] == d]
            if subschedule == []:
                if verbose:
                    print(f"No visits on day {d}")
                continue
            else:
                tt = commuting_times[op_municipality-1][pat_municipalities[subschedule[0][c.SCH_PATIENT]]-1]

                inter_only_daily_travel_time = 0
                if pat_municipalities[subschedule[0][c.SCH_PATIENT]] != op_municipality:
                    travel_count[1] += 1
                    inter_only_daily_travel_time += tt
                else:
                    travel_count[0] += 1
                
                daily_travel_time = tt

                travel_index = str(tt // 5)
                if travel_index in travel_durations:
                    travel_durations[travel_index] += 1
                else:
                    travel_durations[travel_index] = 1
                
                for i in range(len(subschedule)):
                    if i == len(subschedule) - 1:
                        tt = commuting_times[pat_municipalities[subschedule[i][c.SCH_PATIENT]]-1][op_municipality-1]
                        if pat_municipalities[subschedule[i][c.SCH_PATIENT]] != op_municipality:
                            travel_count[1] += 1
                            inter_only_daily_travel_time += tt
                        else:
                            travel_count[0] += 1
                        daily_travel_time += tt

                        travel_index = str(tt // 5)
                        if travel_index in travel_durations:
                            travel_durations[travel_index] += 1
                        else:
                            travel_durations[travel_index] = 1
                    else:
                        tt = commuting_times[pat_municipalities[subschedule[i][c.SCH_PATIENT]]-1][pat_municipalities[subschedule[i+1][c.SCH_PATIENT]]-1]
                        if pat_municipalities[subschedule[i][c.SCH_PATIENT]] != pat_municipalities[subschedule[i+1][c.SCH_PATIENT]]:
                            travel_count[1] += 1
                            inter_only_daily_travel_time += tt
                        else:
                            travel_count[0] += 1
                        daily_travel_time += tt

                        travel_index = str(tt // 5)
                        if travel_index in travel_durations:
                            travel_durations[travel_index] += 1
                        else:
                            travel_durations[travel_index] = 1
                        
                if verbose:
                    print(f"Travel time on day {d}: {daily_travel_time} minutes")
                    print(f"Inter-municipal travel time on day {d}: {inter_only_daily_travel_time} minutes")

                travel_time += daily_travel_time
                inter_only_travel_time += inter_only_daily_travel_time

        travel_time = round(travel_time, 2)
        inter_only_travel_time = round(inter_only_travel_time, 2)
        
        if verbose:
            print(f"Total travel time: {travel_time} minutes")
            print(f"Total inter-municipal travel time: {inter_only_travel_time} minutes")

        return travel_time, inter_only_travel_time, travel_count, travel_durations

    else:
        if verbose:
            print("-- All operators travel time --")
        
        travel_times = []
        inter_only_travel_times = []
        travel_counts = []
        tot_travel_durations = {}

        operators = m.get_num_operators()

        commuting_times = m.get_commuting_times()
        pat_municipalities = m.get_patient_param(c.PAT_MUNICIPALITY)
        op_municipalities = m.get_operator_param(c.OP_MUNICIPALITY)
        op_schedules = operator_schedule()

        for o in range(operators):
            travel_time, inter_only_travel_time, travel_count, travel_durations = operator_travel_time(o, commuting_times, pat_municipalities, op_municipalities[o], op_schedules[o], verbose=False)
            if verbose:
                print(f"Operator {o}: {travel_time} minutes")
                print(f"Operator {o} inter-municipal: {inter_only_travel_time} minutes")
            
            travel_times.append(travel_time)
            inter_only_travel_times.append(inter_only_travel_time)
            travel_counts.append(travel_count)
            
            for key in travel_durations:
                if key in tot_travel_durations:
                    tot_travel_durations[key] += travel_durations[key]
                else:
                    tot_travel_durations[key] = travel_durations[key]
        
        return travel_times, inter_only_travel_times, travel_counts, tot_travel_durations


def operator_utilization(operator=None, verbose=False):
    # visit time + travel time / total time
    if operator is None:
        if verbose:
            print("-- All operators utilization (visit time + travel time) / (total_time) --")
    
        operators = m.get_num_operators()
        
        utilizations = []
        for o in range(operators):
            utilization = operator_utilization(o, verbose=False)
            if verbose:
                print(f"Operator {o}: {utilization}%")
            utilizations.append(utilization)
        
        return utilizations
    
    else:
        if verbose:
            print(f"-- Operator {operator} utilization (visit time + travel time) / (total_time) --")

        op_time = m.get_operator_param(c.OP_TIME, operator)

        op_travel_time = operator_travel_time(operator, verbose=False)
        op_workload = m.get_operator_workload(operator)

        utilization = (op_workload + op_travel_time) / op_time
        utilization = round(utilization*100, 2)

    if verbose:
        print(f"Total time: {op_time} minutes")
        print(f"Workload: {op_workload} minutes")
        print(f"Travel time: {op_travel_time} minutes")
        print(f"Utilization: {utilization}%")

    return utilization


def operator_workload(operator=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} workload --")

        op_workload = m.get_operator_workload(operator)
        
        if verbose:
            print(f"Workload: {op_workload} minutes")

        return op_workload

    else:
        if verbose:
            print("-- All operators workload --")
        
        operators = m.get_num_operators()

        op_workloads = []
        for o in range(operators):
            op_workload = operator_workload(o, verbose=False)
            if verbose:
                print(f"Operator {o}: {op_workload} minutes")
            op_workloads.append(op_workload)
        
        return op_workloads


def operator_total_wage(operator=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} total wage --")

        op_workload = m.get_operator_workload(operator)
        op_unit_wage = operator_unit_wage(operator, verbose=False)

        w = op_workload * op_unit_wage
        w = round(w, 2)

        # pad with zeros if not enough decimals
        w_str = f"{w:.2f}"
        op_unit_wage_str = f"{op_unit_wage:.2f}"

        if verbose:
            print(f"Total workload: {op_workload} minutes")
            print(f"Unitary wage: {op_unit_wage_str}€ per minute")
            print(f"Total wage: {w_str}€")

        return w
    
    else:
        if verbose:
            print("-- All operators total wage --")
        
        operators = m.get_num_operators()

        wages = []
        for o in range(operators):
            w = operator_total_wage(o, verbose=False)
            if verbose:
                print(f"Operator {o}: {w}€")
            wages.append(w)
        
        return wages


def operator_total_visits(operator=None, op_schedule=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} total visits --")

        if op_schedule is None:
            op_schedule = operator_schedule(operator, verbose=False)

        op_total_visits = len(op_schedule)

        if verbose:
            print(f"Total visits: {total_visits}")

        return op_total_visits

    else:
        if verbose:
            print("-- All operators total visits --")
        
        operators = m.get_num_operators()
        op_schedules = operator_schedule()

        total_visits = []
        for o in range(operators):
            op_total_visits = operator_total_visits(o, op_schedules[o], verbose=False)
            if verbose:
                print(f"Operator {o}: {op_total_visits}")
            total_visits.append(op_total_visits)            
        
        return total_visits


def operator_overtime(operator=None, op_workload=None, op_time=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} overtime --")

        if op_workload is None:
            op_workload = m.get_operator_workload(operator)
        
        if op_time is None:
            op_time = m.get_operator_param(c.OP_TIME, operator)

        op_overtime = max(0, op_workload - op_time)

        if verbose:
            print(f"Total workload: {op_workload} minutes")
            print(f"Total time: {op_time} minutes")
            print(f"Overtime: {op_overtime} minutes")

        return op_overtime
    
    else:
        if verbose:
            print("-- All operators overtime --")
        
        operators = m.get_num_operators()

        op_overtimes = []

        op_workloads = operator_workload()
        op_times = m.get_operator_param(c.OP_TIME)

        for o in range(operators):
            op_overtime = operator_overtime(o, op_workloads[o], op_times[o], verbose=False)
            if verbose:
                print(f"Operator {o}: {op_overtime} minutes")
            op_overtimes.append(op_overtime)
        
        return op_overtimes


def operator_overskill(
    operator=None,
    n_days=None,
    n_patients=None,
    visit_exec=None,
    visit_skill=None,
    op_assignment=None,
    op_availability=None,
    visit_d=None,
    op_tot_visits=None,
    op_workload=None,    
    verbose=False
):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} overskill --")
        
        op_skill = m.get_operator_param(c.OP_SKILL, operator)
        if op_skill == 0:
            if verbose:
                print("Operator cannot execute overskilled visits")
            return [0,0,0,0]

        if n_days is None:
            n_days = m.get_num_days()
        
        if n_patients is None:
            n_patients = m.get_num_patients()

        if visit_exec is None:
            visit_exec = m.get_visit_execution(operator)
        
        if visit_skill is None:
            visit_skill = m.get_visit_param(c.VISIT_SKILL)

        if op_assignment is None:
            op_assignment = m.get_assignment(operator=operator)
        
        if op_availability is None:
            op_availability = m.get_operator_daily_param(c.OP_AVAILABILITY, operator)

        if visit_d is None:
            visit_d = visit_duration(verbose=False)

        # for each day and patient, check if visitSkill < operatorSkill
        overskill_visits = 0
        overskill_time = 0
        for d in range(n_days):
            if verbose:
                print(f"Day {d}")
            # if operator is available on day d
            if op_availability[d] == 1:
                for p in range(n_patients):
                    # if patient is assigned to operator
                    if op_assignment[p] == 1 and visit_exec[p][d] == 1 and visit_skill[p][d] < op_skill:
                        overskill_visits += 1
                        overskill_time += visit_d[p][d]
            if verbose:
                print(f"Overskill visits: {overskill_visits}")
                print(f"Overskill time: {overskill_time} minutes")

        # if the operator has no visits, overskill is 0
        if op_tot_visits is None:
            op_tot_visits = operator_total_visits(operator, verbose=False)

        if op_workload is None:
            op_workload = operator_workload(operator, verbose=False)

        if op_tot_visits > 0:
            overskill_perc = overskill_visits / op_tot_visits
            overskill_perc = round(100*overskill_perc, 2)
            overskill_time_perc = overskill_time / op_workload
            overskill_time_perc = round(100*overskill_time_perc, 2)

        if verbose:
            print(f"Total visits: {op_tot_visits}")
            print(f"Total workload: {op_workload} minutes")
            print(f"Overskill visits: {overskill_visits} ({overskill_perc}%)")
            print(f"Overskill time: {overskill_time} minutes ({overskill_time_perc}%)")

        return [overskill_visits, overskill_perc, overskill_time, overskill_time_perc]
        
    else:
        if verbose:
            print("-- All operators overskill --")
        
        operators = m.get_num_operators()

        overskill = []
        
        n_days = m.get_num_days()
        n_patients = m.get_num_patients()
        visit_execs = m.get_visit_execution()
        visit_skill = m.get_visit_param(c.VISIT_SKILL)
        op_assignments = m.get_assignment()
        op_availabilities = m.get_operator_daily_param(c.OP_AVAILABILITY)
        visit_ds = visit_duration()
        total_visits = operator_total_visits()
        op_workloads = operator_workload()

        op_assignments = list(map(list, zip(*op_assignments)))

        for o in range(operators):
            op_overskill = operator_overskill(o, n_days, n_patients, visit_execs[o], visit_skill, op_assignments[o], op_availabilities[o], visit_ds, total_visits[o], op_workloads[o], verbose=False)
            if verbose:
                print(f"Operator {o}: {op_overskill[0]} visits ({op_overskill[1]}%); {op_overskill[2]} minutes ({op_overskill[3]}%)")
            overskill.append(op_overskill)
        
        return overskill


def operator_availability(operator=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} availability --")

        op_availability = m.get_operator_daily_param(c.OP_AVAILABILITY, operator)

        if verbose:
            print(f"Availability: {op_availability}")

        return op_availability

    else:
        if verbose:
            print("-- All operators availability --")
        
        operators = m.get_num_operators()

        availabilities = []
        for o in range(operators):
            op_availability = operator_availability(o, verbose=False)
            if verbose:
                print(f"Operator {o}: {op_availability}")
            availabilities.append(op_availability)
        
        return availabilities        


def operator_times(operator=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} times --")
    
        op_start_times = m.get_operator_daily_param(c.OP_START_TIME, operator)
        op_end_times = m.get_operator_daily_param(c.OP_END_TIME, operator)

        if verbose:
            print(f"Start times: {op_start_times}")
            print(f"End times: {op_end_times}")

        return op_start_times, op_end_times
    
    else:
        if verbose:
            print("-- All operators times --")
        
        operators = m.get_num_operators()

        start_times = []
        end_times = []
        for o in range(operators):
            op_start_times, op_end_times = operator_times(o, verbose=False)
            start_times.append(op_start_times)
            end_times.append(op_end_times)
            if verbose:
                print(f"Operator {o}: {op_start_times} - {op_end_times}")
        
        return start_times, end_times


def operator_efficiency(operator=None, inter_only=False, verbose=False):
    # efficiency = workload / (workload + travel time)
    if operator is not None:
        if verbose:
            if inter_only:
                print(f"-- Operator {operator} inter-only efficiency - workload / (workload + inter-municipality travel time)--")
            else:
                print(f"-- Operator {operator} efficiency - workload / (workload + travel time)--")

        op_workload = m.get_operator_workload(operator)
        op_travel_time = operator_travel_time(operator, inter_only, verbose=False)

        efficiency = op_workload / (op_workload + op_travel_time)        
        efficiency = round(efficiency*100, 2)

        if verbose:
            print(f"Workload: {op_workload} minutes")
            print(f"Travel time: {op_travel_time} minutes")
            print(f"Efficiency: {efficiency}%")

        return efficiency

    else:
        if verbose:
            if inter_only:
                print("-- All operators inter-only efficiency - workload / (workload + inter-municipality travel time) --")
            else:
                print("-- All operators efficiency - workload / (workload + travel time) --")
        
        operators = m.get_num_operators()

        efficiencies = []
        for o in range(operators):
            op_efficiency = operator_efficiency(o, inter_only, verbose=False)
            if verbose:
                print(f"Operator {o}: {op_efficiency}%")
            efficiencies.append(op_efficiency)
        
        return efficiencies


def operator_not_executed_visits(operator=None, verbose=False):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} unexecuted visits --")

        # unexecuted visits: sum of its requests - sum of its executed visits
        visit_req = m.get_visit_param(c.VISIT_REQUEST)

        pat_assignment = patient_assignment()
        pat_assignment = [p == operator for p in pat_assignment]

        op_total_requests = sum(sum(vr for vr in visit_req[p]) * pat_assignment[p] for p in range(len(pat_assignment)))
        op_total_visits = operator_total_visits(operator, verbose=False)

        op_not_executed_visits = op_total_requests - op_total_visits

        if verbose:
            print(f"Total requests: {op_total_requests}")
            print(f"Total visits: {op_total_visits}")
            print(f"Unexecuted visits: {op_not_executed_visits}")

        return op_not_executed_visits

    else:
        if verbose:
            print("-- All operators unexecuted visits --")
        
        operators = m.get_num_operators()

        not_executed_visits = []
        for o in range(operators):
            op_not_executed_visits = operator_not_executed_visits(o, verbose=False)
            if verbose:
                print(f"Operator {o}: {op_not_executed_visits}")
            not_executed_visits.append(op_not_executed_visits)
        
        return not_executed_visits


def operator_feasible_patients(
    operator=None,
    visit_requests=None,
    visit_start_times=None,
    visit_end_times=None,
    visit_skills=None,
    op_municipality=None,
    pat_municipalities=None,
    commuting_times=None,
    op_availability=None,
    op_start_times=None,
    op_end_times=None,
    op_skill=None,
    verbose=False
):
    if operator is not None:
        if verbose:
            print(f"-- Operator {operator} feasible patients --")

        n_patients = m.get_num_patients()
        n_days = m.get_num_days()
        # feasible patients: patients that could be assigned to operators

        # criterion 1: operators must be available for each request of the patient
        # criterion 2: operators must be available for the whole time window of the patient
        # criterion 3: operators must be able to reach the patient within the time window

        if visit_requests is None:
            visit_requests = m.get_visit_param(c.VISIT_REQUEST)
        
        if visit_start_times is None and visit_end_times is None:
            visit_start_times = m.get_visit_param(c.VISIT_START_TIME)
            visit_end_times = m.get_visit_param(c.VISIT_END_TIME)

        if visit_skills is None:
            visit_skills = m.get_visit_param(c.VISIT_SKILL)

        if op_municipality is None:
            op_municipality = m.get_operator_param(c.OP_MUNICIPALITY, operator)

        if pat_municipalities is None:
            pat_municipalities = m.get_patient_param(c.PAT_MUNICIPALITY)

        if commuting_times is None:
            commuting_times = m.get_commuting_times()

        if op_availability is None:
            op_availability = operator_availability(operator, verbose=False)

        if op_start_times is None and op_end_times is None:
            op_start_times, op_end_times = operator_times(operator, verbose=False)
        
        if op_skill is None:
            op_skill = m.get_operator_param(c.OP_SKILL, operator)

        feasible_patients = [1] * n_patients

        for p in range(n_patients):
            for d in range(n_days):
                if visit_requests[p][d] > 0:
                    if not op_availability[d]:
                        feasible_patients[p] = 0
                        break
                    if visit_skills[p][d] > op_skill:
                        feasible_patients[p] = 0
                        break
                    if visit_start_times[p][d] < op_start_times[d] + commuting_times[op_municipality-1][pat_municipalities[p]-1]:
                        feasible_patients[p] = 0
                        break
                    if visit_end_times[p][d] > op_end_times[d] - commuting_times[op_municipality-1][pat_municipalities[p]-1]:
                        feasible_patients[p] = 0
                        break
        
        if verbose:
            print(f"Number of feasible patients: {sum(feasible_patients)}")
            print(f"Feasible patients: {feasible_patients}")

        return feasible_patients
    
    else:
        if verbose:
            print("-- All operators feasible patients --")

        n_operators = m.get_num_operators()

        visit_requests = m.get_visit_param(c.VISIT_REQUEST)        
        visit_start_times = m.get_visit_param(c.VISIT_START_TIME)
        visit_end_times = m.get_visit_param(c.VISIT_END_TIME)
        visit_skills = m.get_visit_param(c.VISIT_SKILL)

        op_municipalities = m.get_operator_param(c.OP_MUNICIPALITY)
        pat_municipalities = m.get_patient_param(c.PAT_MUNICIPALITY)
        commuting_times = m.get_commuting_times()

        op_availabilities = operator_availability(verbose=False)
        op_start_times, op_end_times = operator_times(verbose=False)
        op_skills = m.get_operator_param(c.OP_SKILL)

        feasible_patients = []
        for o in range(n_operators):
            op_feasible_patients = operator_feasible_patients(
                o,
                visit_requests,
                visit_start_times,
                visit_end_times,
                visit_skills,
                op_municipalities[o],
                pat_municipalities,
                commuting_times,
                op_availabilities[o],
                op_start_times[o],
                op_end_times[o],
                op_skills[o]
            )

            if verbose:
                print(f"Operator {o}: {op_feasible_patients}")
            feasible_patients.append(op_feasible_patients)
        
        return feasible_patients
        
# --------------- END OPERATORS --------------- #


# --------------- PATIENTS --------------- #

def patient_assignment(patient=None, ass=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} assignment --")

        if ass is None:
            ass = m.get_assignment(patient)
        # assigned operator: index of 1 (there is only one 1) in ass
        assigned_operator = ass.index(1)

        if verbose:
            print(f"Patient {patient} assigned to operator {assigned_operator}")

        return assigned_operator
    
    else:
        if verbose:
            print("-- All patient assignments --")

        patients = m.get_num_patients()

        assigned_operators = []

        tot_ass = m.get_assignment()

        for p in range(patients):
            pat_assigned_operator = patient_assignment(p, tot_ass[p], verbose=False)
            if verbose:
                print(f"Patient {p} assigned to operator {pat_assigned_operator}")

            assigned_operators.append(pat_assigned_operator)
        
        if verbose:
            print(f"Assigned operators: {assigned_operators}")

        return assigned_operators        


def patient_total_time(patient=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} total time --")

        days = m.get_num_days()
        operators = m.get_num_operators()
        visit_exec = m.get_visit_execution(patient=patient)

        total_time = 0
        for d in range(days):
            for o in range(operators):
                if visit_exec[o][d] == 1:
                    total_time += visit_duration(patient, d)
        
        if verbose:
            print(f"Total time: {total_time} minutes")

        return total_time
    
    else:
        if verbose:
            print("-- All patients total time --")
        
        patients = m.get_num_patients()

        total_times = []
        for p in range(patients):
            pat_total_time = patient_total_time(p, verbose=False)
            if verbose:
                print(f"Patient {p} total time: {pat_total_time} minutes")
            total_times.append(pat_total_time)
        
        return total_times


def patient_expense(patient=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} expense --")

        days = m.get_num_days()
        operators = m.get_num_operators()
        visit_exec = m.get_visit_execution(patient=patient)
        op_unit_wages = operator_unit_wage(verbose=False)

        expense = 0
        for d in range(days):
            for o in range(operators):
                if visit_exec[o][d] == 1:
                    expense += visit_duration(patient, d) * op_unit_wages[o]
        
        expense = round(expense, 2)
        expense_str = f"{expense:.2f}"

        if verbose:
            print(f"Total expense: {expense_str}€")

        return expense

    else:
        if verbose:
            print("-- All patients expense --")
        
        patients = m.get_num_patients()

        expenses = []
        for p in range(patients):
            pat_expense = patient_expense(p, verbose=False)
            pat_expense_str = f"{pat_expense:.2f}"
            if verbose:
                print(f"Patient {p} expense: {pat_expense_str}€")
            expenses.append(pat_expense)
        
        return expenses


def patient_total_requests(patient=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} total requests --")

        total_requests = sum(m.get_visit_param(c.VISIT_REQUEST, patient))

        if verbose:
            print(f"Total requests: {total_requests}")

        return total_requests
    
    else:
        if verbose:
            print("-- All patients total requests --")
        
        patients = m.get_num_patients()

        total_requests = []
        for p in range(patients):
            pat_total_requests = patient_total_requests(p, verbose=False)
            if verbose:
                print(f"Patient {p} total requests: {pat_total_requests}")
            total_requests.append(pat_total_requests)
        
        return total_requests


def patient_visits_per_skill(patient=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} visits per skill --")

        days = m.get_num_days()
        operators = m.get_num_operators()

        visit_exec = m.get_visit_execution(patient=patient)
        visit_skill = m.get_visit_param(c.VISIT_SKILL, patient)

        visits_per_skill = {}
        for d in range(days):
            for o in range(operators):
                if visit_exec[o][d] == 1:
                    if visit_skill[d] not in visits_per_skill:
                        visits_per_skill[visit_skill[d]] = 1
                    else:
                        visits_per_skill[visit_skill[d]] += 1
        
        if verbose:
            print(f"visits per skill: {visits_per_skill}")

        return visits_per_skill
    
    else:
        if verbose:
            print("-- All patients visits per skill --")
        
        patients = m.get_num_patients()

        visits_per_skill = []
        for p in range(patients):
            pat_visits_per_skill = patient_visits_per_skill(p, verbose=False)
            if verbose:
                print(f"Patient {p} visits per skill: {pat_visits_per_skill}")
            visits_per_skill.append(pat_visits_per_skill)
        
        return visits_per_skill


def patient_requests_per_skill(patient=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} requests per skill --")

        days = m.get_num_days()
        operators = m.get_num_operators()

        visit_req = m.get_visit_param(c.VISIT_REQUEST, patient=patient)
        visit_skill = m.get_visit_param(c.VISIT_SKILL, patient)

        requests_per_skill = {}
        for d in range(days):
            if visit_req[d] == 1:
                if visit_skill[d] not in requests_per_skill:
                    requests_per_skill[visit_skill[d]] = 1
                else:
                    requests_per_skill[visit_skill[d]] += 1
        
        if verbose:
            print(f"requests per skill: {requests_per_skill}")

        return requests_per_skill
    
    else:
        if verbose:
            print("-- All patients requests per skill --")
        
        patients = m.get_num_patients()

        requests_per_skill = []
        for p in range(patients):
            pat_requests_per_skill = patient_requests_per_skill(p, verbose=False)
            if verbose:
                print(f"Patient {p} requests per skill: {pat_requests_per_skill}")
            requests_per_skill.append(pat_requests_per_skill)
        
        return requests_per_skill


def patient_total_visits(patient=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} total visits --")

        visit_exec = m.get_visit_execution(patient=patient)

        total_visits = sum(sum(visit_exec, []))
        
        if verbose:
            print(f"Total visits: {total_visits}")

        return total_visits
    
    else:
        if verbose:
            print("-- All patients total visits --")
        
        patients = m.get_num_patients()

        total_visits = []
        for p in range(patients):
            pat_total_visits = patient_total_visits(p, verbose=False)
            if verbose:
                print(f"Patient {p} total visits: {pat_total_visits}")
            total_visits.append(pat_total_visits)
        
        return total_visits


def patient_not_executed_visits(patient=None, verbose=False):
    if patient is not None:
        if verbose:
            print(f"-- Patient {patient} unexecuted visits --")

        visit_req = m.get_visit_param(c.VISIT_REQUEST, patient)
        visit_exec = m.get_visit_execution(patient=patient)

        not_executed_visits = sum(visit_req) - sum(sum(visit_exec, []))
        
        if verbose:
            print(f"Unexecuted visits: {not_executed_visits}")

        return not_executed_visits
    
    else:
        if verbose:
            print("-- All patients unexecuted visits --")
        
        patients = m.get_num_patients()

        not_executed_visits = []
        for p in range(patients):
            pat_not_executed_visits = patient_not_executed_visits(p, verbose=False)
            if verbose:
                print(f"Patient {p} unexecuted visits: {pat_not_executed_visits}")
            not_executed_visits.append(pat_not_executed_visits)
        
        return not_executed_visits

# --------------- END PATIENTS --------------- #


# --------------- VISITS --------------- #

def visit_duration(patient=None, day=None):
    visit_end_times = m.get_visit_param(c.VISIT_END_TIME)
    visit_start_times = m.get_visit_param(c.VISIT_START_TIME)
        
    durations = np.subtract(visit_end_times, visit_start_times)

    if patient is None and day is None:
        return durations
    elif patient is not None and day is None:
        return durations[patient]
    elif patient is None and day is not None:
        return [d[day] for d in durations]
    else:
        return durations[patient][day]


def total_not_executed_visits(verbose=False):
    if verbose:
        print("-- Not executed visits --")

    visit_exec = m.get_visit_execution()
    visit_request = m.get_visit_param(c.VISIT_REQUEST)

    total_exec = sum(sum(sum(visit_exec, []), []))
    total_request = sum(sum(visit_request, []))

    total_not_exec = total_request - total_exec

    if verbose:
        print(f"Not executed visits: {total_not_exec}")

    return total_not_exec

# --------------- END VISITS --------------- #


# --------------- MUNICIPALITIES --------------- #

def municipality_operators(municipality=None, verbose=False):
    if municipality is not None:
        if verbose:
            print(f"-- Municipality {municipality} operators --")

        operators = m.get_num_operators()
        op_municipalities = m.get_operator_param(c.OP_MUNICIPALITY)

        mun_operators = 0
        for o in range(operators):
            if op_municipalities[o] == municipality:
                mun_operators += 1
        
        if verbose:
            print(f"Operators: {mun_operators}")

        return mun_operators
    
    else:
        if verbose:
            print("-- All municipalities operators --")
        
        municipalities = m.get_num_municipalities()

        tot_mun_operators = []
        for mun in range(1, municipalities+1):
            mun_operators = municipality_operators(mun, verbose=False)
            if verbose:
                print(f"Municipality {mun} operators: {mun_operators}")
            tot_mun_operators.append(mun_operators)
        
        return tot_mun_operators


def municipality_patients(municipality=None, verbose=False):
    if municipality is not None:
        if verbose:
            print(f"-- Municipality {municipality} patients --")

        patients = m.get_num_patients()
        pat_municipalities = m.get_patient_param(c.PAT_MUNICIPALITY)

        mun_patients = 0
        for p in range(patients):
            if pat_municipalities[p] == municipality:
                mun_patients += 1
        
        if verbose:
            print(f"Patients: {mun_patients}")

        return mun_patients
    
    else:
        if verbose:
            print("-- All municipalities patients --")
        
        municipalities = m.get_num_municipalities()
        
        tot_mun_patients = []
        for mun in range(1, municipalities+1):
            mun_patients = municipality_patients(mun, verbose=False)
            if verbose:
                print(f"Municipality {mun} patients: {mun_patients}")
            tot_mun_patients.append(mun_patients)
        
        return tot_mun_patients


def municipality_requests(municipality=None, verbose=False):
    if municipality is not None:
        if verbose:
            print(f"-- Municipality {municipality} requests --")

        patients = m.get_num_patients()

        pat_municipality = m.get_patient_param(c.PAT_MUNICIPALITY)
        visit_requests = m.get_visit_param(c.VISIT_REQUEST)


        mun_requests = 0
        for p in range(patients):
            if pat_municipality[p] == municipality:
                mun_requests += sum(visit_requests[p])
        
        if verbose:
            print(f"Requests: {mun_requests}")

        return mun_requests
    
    else:
        if verbose:
            print("-- All municipalities requests --")
        
        municipalities = m.get_num_municipalities()

        tot_mun_requests = []
        for mun in range(1, municipalities+1):
            mun_requests = municipality_requests(mun, verbose=False)
            if verbose:
                print(f"Municipality {mun} requests: {mun_requests}")
            tot_mun_requests.append(mun_requests)
        
        return tot_mun_requests


def municipality_visits(municipality=None, verbose=False):
    if municipality is not None:
        if verbose:
            print(f"-- Municipality {municipality} visits --")

        patients = m.get_num_patients()
        visit_exec = m.get_visit_execution()
        pat_municipality = m.get_patient_param(c.PAT_MUNICIPALITY)

        mun_visits = 0
        for p in range(patients):
            if pat_municipality[p] == municipality:
                mun_visits += sum([sum(v[p]) for v in visit_exec])
        
        if verbose:
            print(f"Visits: {mun_visits}")

        return mun_visits
    
    else:
        if verbose:
            print("-- All municipalities visits --")
        
        municipalities = m.get_num_municipalities()
        
        tot_mun_visits = []
        for mun in range(1, municipalities+1):
            mun_visits = municipality_visits(mun, verbose=False)
            if verbose:
                print(f"Municipality {mun} visits: {mun_visits}")
            tot_mun_visits.append(mun_visits)

        return tot_mun_visits

    
def municipality_time_from_others(municipality=None, commuting_times=None, verbose=False):
    if municipality is not None:
        if verbose:
            print(f"-- Municipality {municipality} distance from others --")

        n_municipalities = m.get_num_municipalities()

        if commuting_times is None:
            commuting_times = m.get_commuting_times()

        mun_distances = []
        for mun in range(1, n_municipalities+1):
            if mun != municipality:
                mun_distances.append(commuting_times[municipality-1][mun-1])
        
        avg_distance = sum(mun_distances) / len(mun_distances)
        avg_distance = round(avg_distance, 2)

        if verbose:
            print(f"Distances: {mun_distances}; average: {avg_distance} minutes")

        return mun_distances, avg_distance
    
    else:
        if verbose:
            print("-- All municipalities distance from others --")
        
        n_municipalities = m.get_num_municipalities()
        
        tot_mun_distances = []
        avg_distances = []
        for mun in range(1, n_municipalities+1):
            mun_distances, avg_distance = municipality_time_from_others(mun, verbose=False)
            if verbose:
                print(f"Municipality {mun} distances: {mun_distances}; average: {avg_distance} minutes")
            tot_mun_distances.append(mun_distances)
            avg_distances.append(avg_distance)

        return tot_mun_distances, avg_distances

# --------------- END MUNICIPALITIES --------------- #

def operator_availability_matrix(day=None):
    time_units = u.get_time_units()
    n_days = m.get_num_days()    
    n_operators = m.get_num_operators()

    availability_matrix = []    
    for d in range(n_days):
        daily_availability_array = [0] * time_units
        for op_id in range(n_operators):
            op_times = operator_times(op_id)
            st_time = op_times[0][d]
            end_time = op_times[1][d]

            if st_time != c.DEF_OP_START_TIME:
                st_time += c.TIME_UNIT
            else:
                st_time = c.DEF_PAT_START_TIME
            
            if end_time != c.DEF_OP_END_TIME:
                end_time -= c.TIME_UNIT
            else:
                end_time = c.DEF_PAT_END_TIME
                        
            for t in range(st_time, end_time, c.TIME_UNIT):
                t_index = (t - c.DEF_PAT_START_TIME) // c.TIME_UNIT
                daily_availability_array[t_index] += 1

        availability_matrix.append(daily_availability_array)

    if day is None:
        return availability_matrix
    else:
        return availability_matrix[day]
