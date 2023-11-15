import src.constants as c
import src.stats as s
import src.utilities as u

import os
import json
import numpy as np


def get_average_exec_time(folder):
    # retrieve the summary file from the folder
    summary_file = f'{c.ARCHIVE_FOLDER}{folder}{c.SUMMARY_CSV}'

    if os.path.exists(summary_file):
        # read the summary file
        with open(summary_file, 'r') as f:
            lines = f.readlines()
        
        # remove empty lines
        lines = [line for line in lines if line != '\n']

        # retrieve the execution time (last column of each line)
        exec_times = [float(line.split(',')[-1]) for line in lines[1:]]
        
        return sum(exec_times) / len(exec_times)

    else:
        return False


def get_average_obj_value(folder):
    # retrieve the summary file from the folder
    summary_file = f'{c.ARCHIVE_FOLDER}{folder}{c.SUMMARY_CSV}'

    # read the summary file
    with open(summary_file, 'r') as f:
        lines = f.readlines()
    
    # remove empty lines
    lines = [line for line in lines if line != '\n']

    # retrieve the execution time (last column of each line)
    obj_values = [float(line.split(',')[-3]) for line in lines[1:]]
    
    return sum(obj_values) / len(obj_values)


def get_average_gap(folder):
    # retrieve the summary file from the folder
    summary_file = f'{c.ARCHIVE_FOLDER}{folder}{c.SUMMARY_CSV}'

    # read the summary file
    with open(summary_file, 'r') as f:
        lines = f.readlines()
    
    # remove empty lines
    lines = [line for line in lines if line != '\n']

    # retrieve the execution time (last column of each line)
    gaps = [float(line.split(',')[-2]) for line in lines[1:]]
    
    return sum(gaps) / len(gaps)


def get_average_utilization_by_skill(folder):
    # for each subfolder in that folder, read the operator stats file
    subfolders = [f for f in os.listdir(f'{c.ARCHIVE_FOLDER}{folder}') if os.path.isdir(f'{c.ARCHIVE_FOLDER}{folder}{f}')]
    operator_stats_files = [f'{c.ARCHIVE_FOLDER}{folder}{f}/{c.OP_STATS_CSV}' for f in subfolders]

    # read the operator stats files
    operator_util = []
    for operator_stats_file in operator_stats_files:
        # print(operator_stats_file)
        with open(operator_stats_file, 'r') as f:
            lines = f.readlines()
        
        # remove empty lines
        lines = [line for line in lines if line != '\n']
        
        # get the column with c.WORKLOAD as header
        contract_time_column = lines[0].split(',').index(c.CONTRACT_TIME)
        workload_column = lines[0].split(',').index(c.WORKLOAD)
        skill_column = lines[0].split(',').index(c.SKILL)
        
        # get both the skill and the workload
        skill_workload = [(line.split(',')[skill_column], float(line.split(',')[workload_column]), float(line.split(',')[contract_time_column])) for line in lines[1:]]
        skill_workload = [entry for entry in skill_workload if entry[0] != '-']

        # add to each entry a new field with workload/contract_time
        skill_util = [(entry[0], entry[1] / entry[2]) for entry in skill_workload]

        low_skill_util = [entry[1] for entry in skill_util if entry[0] == '0']
        high_skill_util = [entry[1] for entry in skill_util if entry[0] == '1']

        avgs = [sum(low_skill_util) / len(low_skill_util), sum(high_skill_util) / len(high_skill_util)]

        # add to the list of operator_util
        operator_util.append(avgs)
    
    # average the workload for each skill
    tot_low = sum([entry[0] for entry in operator_util]) / len(operator_util)
    tot_high = sum([entry[1] for entry in operator_util]) / len(operator_util)
    
    return [tot_low, tot_high]


def get_average_workload_by_skill(folder):
    # for each subfolder in that folder, read the operator stats file
    subfolders = [f for f in os.listdir(f'{c.ARCHIVE_FOLDER}{folder}') if os.path.isdir(f'{c.ARCHIVE_FOLDER}{folder}{f}')]
    operator_stats_files = [f'{c.ARCHIVE_FOLDER}{folder}{f}/{c.OP_STATS_CSV}' for f in subfolders]

    # read the operator stats files
    operator_workload = []
    for operator_stats_file in operator_stats_files:
        # print(operator_stats_file)
        with open(operator_stats_file, 'r') as f:
            lines = f.readlines()
        
        # remove empty lines
        lines = [line for line in lines if line != '\n']
        
        # get the column with c.WORKLOAD as header
        workload_column = lines[0].split(',').index(c.WORKLOAD)
        skill_column = lines[0].split(',').index(c.SKILL)

        # get both the skill and the workload
        skill_workload = [(line.split(',')[skill_column], float(line.split(',')[workload_column])) for line in lines[1:]]
        skill_workload = [entry for entry in skill_workload if entry[0] != '-']

        low_skill_workload = [entry[1] for entry in skill_workload if entry[0] == '0']
        high_skill_workload = [entry[1] for entry in skill_workload if entry[0] == '1']

        avgs = [sum(low_skill_workload), sum(high_skill_workload)]

        # add to the list of operator_workload
        operator_workload.append(avgs)

    # average the workload for each skill
    tot_low = sum([entry[0] for entry in operator_workload]) / len(operator_workload)
    tot_high = sum([entry[1] for entry in operator_workload]) / len(operator_workload)

    return [tot_low, tot_high]


def get_average_overtime_by_skill(folder):
    # for each subfolder in that folder, read the operator stats file
    subfolders = [f for f in os.listdir(f'{c.ARCHIVE_FOLDER}{folder}') if os.path.isdir(f'{c.ARCHIVE_FOLDER}{folder}{f}')]
    operator_stats_files = [f'{c.ARCHIVE_FOLDER}{folder}{f}/{c.OP_STATS_CSV}' for f in subfolders]

    # read the operator stats files
    operator_ot = []
    for operator_stats_file in operator_stats_files:
        # print(operator_stats_file)
        with open(operator_stats_file, 'r') as f:
            lines = f.readlines()
        
        # remove empty lines
        lines = [line for line in lines if line != '\n']
        
        # get the column with c.OVERTIME
        ot_column = lines[0].split(',').index(c.OVERTIME)
        skill_column = lines[0].split(',').index(c.SKILL)

        # get both the skill and the overtime
        skill_ot = [(line.split(',')[skill_column], float(line.split(',')[ot_column])) for line in lines[1:]]
        skill_ot = [entry for entry in skill_ot if entry[0] != '-']

        low_skill_ot = [entry[1] for entry in skill_ot if entry[0] == '0']
        high_skill_ot = [entry[1] for entry in skill_ot if entry[0] == '1']

        avgs = [sum(low_skill_ot), sum(high_skill_ot)]

        operator_ot.append(avgs)

    # average the overtime for each skill
    tot_low = sum([entry[0] for entry in operator_ot]) / len(operator_ot)
    tot_high = sum([entry[1] for entry in operator_ot]) / len(operator_ot)

    return [tot_low, tot_high]


def get_average_executed_visits(folder):
    # retrieve the summary file from the folder
    summary_file = f'{c.ARCHIVE_FOLDER}{folder}{c.SUMMARY_CSV}'

    # read the summary file
    with open(summary_file, 'r') as f:
        lines = f.readlines()
    
    # remove empty lines
    lines = [line for line in lines if line != '\n']

    # retrieve the execution time (last column of each line)
    ex_v_index = lines[0].split(',').index(c.TOTAL_VISITS)
    n_ex_v_index = lines[0].split(',').index(c.NOT_EXECUTED_VISITS)

    executed_visits = [(float(line.split(',')[ex_v_index]), float(line.split(',')[n_ex_v_index])) for line in lines[1:]]

    # remove first half of the array
    executed_visits = executed_visits[len(executed_visits) // 2:]

    # average the values
    executed_visits = [sum([entry[0] for entry in executed_visits]) / len(executed_visits), sum([entry[1] for entry in executed_visits]) / len(executed_visits)]

    return executed_visits


def get_average_overskill_time(folder):
    # retrieve the summary file from the folder
    summary_file = f'{c.ARCHIVE_FOLDER}{folder}{c.SUMMARY_CSV}'

    # read the summary file
    with open(summary_file, 'r') as f:
        lines = f.readlines()
    
    # remove empty lines
    lines = [line for line in lines if line != '\n']

    ovsk_time_index = lines[0].split(',').index(c.OVERSKILL_TIME)

    ovsk_time = [line.split(',')[ovsk_time_index] for line in lines[1:]]

    # remove first half of the array
    ovsk_time = ovsk_time[-len(ovsk_time) // 2:]

    ovsk_time = [int(t) for t in ovsk_time]

    return sum(ovsk_time) / len(ovsk_time)


# def get_average_distance_between_cities(folder):
    # retrieve the commuting.json file from each subfolder of the folder
    subfolders = [f for f in os.listdir(f'{c.ARCHIVE_FOLDER}{folder}') if os.path.isdir(f'{c.ARCHIVE_FOLDER}{folder}{f}')]
    commuting_files = [f'{c.ARCHIVE_FOLDER}{folder}{f}/commuting.json' for f in subfolders]

    # read the commuting files
    commuting_distances = []
    for commuting_file in commuting_files:
        with open(commuting_file, 'r') as f:
            commuting = json.load(f)
        
        print(commuting)


def count_total_movements(folder):
    subfolders = [f for f in os.listdir(f'{c.ARCHIVE_FOLDER}{folder}') if os.path.isdir(f'{c.ARCHIVE_FOLDER}{folder}{f}')]

    total_counts = []

    for sf in subfolders:
        subfolder = f'{folder}{sf}/'
        u.restore_scenario(subfolder)

        _,_,tc,_ = s.operator_travel_time()
        tc0 = sum(t[0] for t in tc)
        tc1 = sum(t[1] for t in tc)
        total_counts.append([tc0, tc1])

    # get average of total counts
    avg0 = sum([tc[0] for tc in total_counts]) / len(total_counts)
    avg1 = sum([tc[1] for tc in total_counts]) / len(total_counts)

    return [avg0, avg1]


def count_movements_per_length(folder):
    subfolders = [f for f in os.listdir(f'{c.ARCHIVE_FOLDER}{folder}') if os.path.isdir(f'{c.ARCHIVE_FOLDER}{folder}{f}')]

    ttd = {}

    for sf in subfolders:
        subfolder = f'{folder}{sf}/'
        u.restore_scenario(subfolder)

        _,_,_,td = s.operator_travel_time()
    
        for key in td:
            if key not in ttd:
                ttd[key] = td[key]
            else:
                ttd[key] += td[key]
        
    # sort ttd by keys
    ttd = {k: v for k, v in sorted(ttd.items(), key=lambda item: float(item[0]))}
    return ttd


def get_travel_times(folder):
    summary_file = f'{c.ARCHIVE_FOLDER}{folder}{c.SUMMARY_CSV}'

    # read the summary file
    with open(summary_file, 'r') as f:
        lines = f.readlines()

    # remove empty lines
    lines = [line for line in lines if line != '\n']

    travel_time_index = lines[0].split(',').index(c.TRAVEL_TIME)
    inter_travel_time_index = lines[0].split(',').index(c.INTER_TRAVEL_TIME)

    travel_times = [(float(line.split(',')[travel_time_index]), float(line.split(',')[inter_travel_time_index])) for line in lines[1:]]
    travel_times = travel_times[len(travel_times) // 2:]

    avg_travel_time = sum([tt[0] for tt in travel_times]) / len(travel_times)
    avg_inter_travel_time = sum([tt[1] for tt in travel_times]) / len(travel_times)

    r0 = round(avg_travel_time,0)
    r1 = round(avg_inter_travel_time,0)

    return [r0, r1]


def get_average_duration_of_unexecuted_visits(folder):
    subfolders = [f for f in os.listdir(f'{c.ARCHIVE_FOLDER}{folder}') if os.path.isdir(f'{c.ARCHIVE_FOLDER}{folder}{f}')]

    total_durations = []

    for sf in subfolders:
        subfolder = f'{folder}{sf}/'
        u.restore_scenario(subfolder)

        nes = s.operator_not_executed_schedule()
        # de-nest the list of lists
        nes = [item for sublist in nes for item in sublist]
        durations = [ne[c.SCH_END_TIME] - ne[c.SCH_START_TIME] for ne in nes]
        total_durations.append(durations)

    # de-nest
    total_durations = [item for sublist in total_durations for item in sublist]

    # average the duration of the visits
    avg_duration = sum(total_durations) / len(total_durations)

    return avg_duration
