import src.constants as c
import src.utilities as u


# --------------- GETS --------------- #

# INPUT
def get_numeric_param(parameter):
    input_data = u.merge_JSON_files(c.INPUT_JSON_PATHS)
    if parameter in c.NUMERIC_PARAMS:
        return input_data[parameter]


def get_num_days():
    hp = u.retrieve_JSON(c.HYPERPARAMS_JSON)
    return hp[c.N_DAYS]


def get_num_patients():
    patient_data = u.retrieve_JSON(c.PATIENT_JSON)
    return patient_data[c.N_PATIENTS]


def get_num_operators():
    operator_data = u.retrieve_JSON(c.OPERATOR_JSON)
    return operator_data[c.N_OPERATORS]


def get_num_municipalities():
    hp_data = u.retrieve_JSON(c.HYPERPARAMS_JSON)
    return hp_data[c.N_MUNICIPALITIES]


def get_patient_param(parameter, patient=None):
    patient_data = u.retrieve_JSON(c.PATIENT_JSON)
    
    if parameter in c.PAT_PARAMS:
        if patient is None:
            return patient_data[parameter]
        else:
            return patient_data[parameter][patient]


def get_operator_param(parameter, operator=None):
    operator_data = u.retrieve_JSON(c.OPERATOR_JSON)
    
    if parameter in c.OP_PARAMS:
        if operator is None:
            return operator_data[parameter]
        else:
            return operator_data[parameter][operator]


def get_operator_daily_param(parameter, operator=None, day=None):
    operator_data = u.retrieve_JSON(c.OPERATOR_JSON)
    
    if parameter in c.OP_DAILY_PARAMS:
        if operator is None:
            return operator_data[parameter]
        else:
            if day is None:
                return operator_data[parameter][operator]
            else:
                return operator_data[parameter][operator][day]
    

def get_visit_param(parameter, patient=None, day=None):
    visit_data = u.retrieve_JSON(c.VISIT_JSON)
    
    if parameter in c.VISIT_PARAMS:
        if patient is None and day is None:
            return visit_data[parameter]
        elif patient is None and day is not None:
            res = []
            for patient in range(get_num_patients()):
                res.append(visit_data[parameter][patient][day])
            return res
        elif patient is not None and day is None:
            return visit_data[parameter][patient]
        else:
            return visit_data[parameter][patient][day]


def get_feasibility(operator=None, patient=None):
    ass_data = u.retrieve_JSON(c.ASS_JSON)
    feasibility = ass_data[c.FEASIBLE_PATIENTS]

    if operator == None and patient == None:
        return feasibility
    
    elif operator != None and patient == None:
        return feasibility[operator]
    
    elif operator == None and patient != None:
        return [op_feasibility[patient] for op_feasibility in feasibility]
    
    else:
        return feasibility[operator][patient]


def get_previous_assignment(patient=None, operator=None):
    ass_data = u.retrieve_JSON(c.ASS_JSON)
    prev_ass = ass_data[c.PREV_ASS]

    if patient == None and operator == None:
        return prev_ass
    
    elif patient != None and operator == None:
        return prev_ass[patient]

    elif patient == None and operator != None:
        return [pat_prev_ass[operator] for pat_prev_ass in prev_ass]

    else:
        return prev_ass[patient][operator]


def get_municipality_param(parameter, municipality=None):
    mun_data = u.retrieve_JSON(c.MUNICIPALITY_JSON)

    if parameter in c.MUN_PARAMS:
        if municipality is None:
            return mun_data[parameter]
        else:
            return mun_data[parameter][municipality]


def get_commuting_times(from_mun=None, to_mun=None):
    comm_data = u.retrieve_JSON(c.COMM_JSON)
    mun_distances = comm_data[c.COMM_TIME]

    if from_mun == None and to_mun == None:
        return mun_distances
    
    elif from_mun == None and to_mun != None:
        return [d[to_mun] for d in mun_distances]
    
    elif from_mun != None and to_mun == None:
        return mun_distances[from_mun]
    
    else:
        return mun_distances[from_mun][to_mun]


# OUTPUT
def get_objective():
    output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    try:
        objective = output_data[c.OBJECTIVE]
        return objective
    except KeyError:
        return False


def get_efficiency_metrics():
    output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    try:
        objective = output_data[c.OBJECTIVE]
        optimality_gap = output_data[c.OPTIMALITY_GAP]
        return objective, optimality_gap
    except KeyError:
        return False, False
    

def get_movement(node_1, node_2, operator=None, day=None):
    output_data = u.retrieve_JSON(c.OUTPUT_JSON)

    if not operator:
        return output_data[c.MOVEMENT][node_1][node_2]
    elif not day:
        return output_data[c.MOVEMENT][node_1][node_2][operator]
    else:
        return output_data[c.MOVEMENT][node_1][node_2][operator][day]


def get_assignment(patient=None, operator=None):
    output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    ass = output_data[c.ASSIGNMENT]

    if patient == None and operator == None:
        return ass
    
    elif patient != None and operator == None:
        return ass[patient]

    elif patient == None and operator != None:
        return [pat_ass[operator] for pat_ass in ass]

    else:
        return ass[patient][operator]


def get_visit_execution(operator=None, patient=None, day=None):
    output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    visit_exec = output_data[c.VISIT_EXEC]

    if operator == None and patient == None:
        return visit_exec
    
    elif operator != None:
        if patient == None:
            return visit_exec[operator]
        
        else:
            if day != None:
                return visit_exec[operator][patient][day]

    else:
        if day != None:
            return [op_visit_exec[patient][day] for op_visit_exec in visit_exec]
        
        else:
            return [op_visit_exec[patient] for op_visit_exec in visit_exec]


def get_operator_workload(operator=None):
    output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    op_workload = output_data[c.OP_WORKLOAD]

    if operator == None:
        return op_workload
    
    else:
        return op_workload[operator]
    

def get_operator_overtime(operator=None):
    output_data = u.retrieve_JSON(c.OUTPUT_JSON)
    op_overtime = output_data[c.OP_OVERTIME]

    if operator == None:
        return op_overtime
    
    else:
        return op_overtime[operator]

# --------------- END GETS --------------- #

# --------------- OPERATORS --------------- #

def add_operator(mun, skill, time, max_time):
    operator_data = u.retrieve_JSON(c.OPERATOR_JSON)

    operator_data[c.OP_MUNICIPALITY].append(mun)
    operator_data[c.OP_SKILL].append(skill)
    operator_data[c.OP_TIME].append(time)
    operator_data[c.OP_MAX_TIME].append(max_time)

    operator_data[c.N_OPERATORS] += 1

    # any parameter indexed also by days can provide the number of days
    n_days = len(operator_data[c.OP_AVAILABILITY][0])

    # defalut: always available for max time
    operator_data[c.OP_AVAILABILITY].append([c.DEF_OP_AV]*n_days)
    operator_data[c.OP_START_TIME].append([c.DEF_OP_START_TIME]*n_days)
    operator_data[c.OP_END_TIME].append([c.DEF_OP_END_TIME]*n_days)

    u.save_JSON(operator_data, c.OPERATOR_JSON)

    # change commuting matrix
    u.generate_commuting_matrix()


def remove_operator(operator):
    operator_data = u.retrieve_JSON(c.OPERATOR_JSON)
    
    for param in c.OP_PARAMS + c.OP_DAILY_PARAMS:
        operator_data[param].pop(operator)
    
    operator_data[c.N_OPERATORS] -= 1

    u.save_JSON(operator_data, c.OPERATOR_JSON)

    # change commuting matrix
    u.generate_commuting_matrix()


def set_operator_param(parameter, new_value, operator=None):
    if parameter in c.OP_PARAMS:
        operator_data = u.retrieve_JSON(c.OPERATOR_JSON)
        
        if operator is None:
            operator_data[parameter] = new_value
        else:
            operator_data[parameter][operator] = new_value
        
        u.save_JSON(operator_data, c.OPERATOR_JSON)

        # change commuting matrix
        if parameter == c.OP_MUNICIPALITY:
            u.generate_commuting_matrix()
    
    else:
        raise Exception(f'Parameter {parameter} not valid')


def set_operator_daily_param(operator, parameter, day, new_value):
    if parameter in c.OP_DAILY_PARAMS:
        operator_data = u.retrieve_JSON(c.OPERATOR_JSON)
        operator_data[parameter][operator][day] = new_value
        u.save_JSON(operator_data, c.OPERATOR_JSON)

    else:
        raise Exception(f'Parameter {parameter} not valid')

# --------------- END OPERATORS --------------- #

# --------------- PATIENTS --------------- #

def add_patient(mun):
    patient_data = u.retrieve_JSON(c.PATIENT_JSON)
    
    patient_data[c.PAT_MUNICIPALITY].append(mun)
    patient_data[c.N_PATIENTS] += 1

    u.save_JSON(patient_data, c.PATIENT_JSON)

    # change commuting matrix
    u.generate_commuting_matrix()

    # change visits data
    visit_data = u.retrieve_JSON(c.VISIT_JSON)
    
    n_days = len(visit_data[c.VISIT_REQUEST][0])

    for param in visit_data:
        # default: no visits
        visit_data[param].append([0]*n_days)
    
    u.save_JSON(visit_data, c.VISIT_JSON)


def remove_patient(patient):
    patient_data = u.retrieve_JSON(c.PATIENT_JSON)
    
    for field in c.PAT_PARAMS:
        patient_data[field].pop(patient)

    patient_data[c.N_PATIENTS] -= 1
    
    u.save_JSON(patient_data, c.PATIENT_JSON)

    # change commuting matrix
    u.generate_commuting_matrix()

    # change visits data
    visit_data = u.retrieve_JSON(c.VISIT_JSON)
    for field in visit_data:
        visit_data[field].pop(patient)
    u.save_JSON(visit_data, c.VISIT_JSON)


def set_patient_param(parameter, new_value, patient=None):
    if parameter in c.PAT_PARAMS:
        patient_data = u.retrieve_JSON(c.PATIENT_JSON)
        if patient is None:
            patient_data[parameter] = new_value
        else:
            patient_data[parameter][patient] = new_value
        
        u.save_JSON(patient_data, c.PATIENT_JSON)

        # change commuting matrix
        u.generate_commuting_matrix()

# --------------- END PATIENTS --------------- #

# --------------- VISITS --------------- #

def add_visit_request(patient, day, skill, start_time, end_time):
    visit_data = u.retrieve_JSON(c.VISIT_JSON)
    
    visit_data[c.VISIT_REQUEST][patient][day] = 1

    visit_data[c.VISIT_SKILL][patient][day] = skill
    visit_data[c.VISIT_START_TIME][patient][day] = start_time
    visit_data[c.VISIT_END_TIME][patient][day] = end_time

    u.save_JSON(visit_data, c.VISIT_JSON)


def remove_visit_request(patient, day):
    visit_data = u.retrieve_JSON(c.VISIT_JSON)
    
    visit_data[c.VISIT_REQUEST][patient][day] = 0

    # reset other fields (not mandatory, but more elegant)
    for param in c.VISIT_PARAMS:
        visit_data[param][patient][day] = 0

    u.save_JSON(visit_data, c.VISIT_JSON)


def set_visit_param(patient, day, parameter, new_value):
    if parameter in c.VISIT_PARAMS:
        visit_data = u.retrieve_JSON(c.VISIT_JSON)
        visit_data[parameter][patient][day] = new_value
        u.save_JSON(visit_data, c.VISIT_JSON)
    
    else:
        raise Exception(f'Parameter {parameter} not valid')

# --------------- END VISITS --------------- #
