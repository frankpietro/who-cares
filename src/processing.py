import os
import json
import time

import src.constants as c
import src.utilities as u
import src.manipulation as m


def JSON_to_dat(dat_file, json_file=None, json_data=None):    
    def write_value(val, tabs=0, comma=False):
        write_str = ''
        if isinstance(val, list):
            write_str += '\t'*tabs
            write_str += '[\n' + '\t'*(tabs+1)
            for i, item in enumerate(val):
                comma = True if i != len(val) - 1 else False
                write_str += write_value(item, tabs+1, comma)
                
            write_str += '\n' + '\t'*tabs + '],\n'
        else:
            write_str += f"{val}"
            write_str += ',' if comma else ' '

        return write_str

    if json_file:
        with open(json_file, 'r') as file:
            data = json.load(file)
    else:
        data = json_data

    with open(dat_file, 'w') as file:
        for key, value in data.items():
            file.write(f'{key} = ')
            write_str = write_value(value)
            # delete one char before the semicolon
            if write_str[-2] == ',':
                write_str = write_str[:-2]
            else:
                write_str = write_str[:-1]

            # convert every "],\n\n]" to "]\n]"
            write_str = write_str.replace('],\n\n]', ']\n]')
            # convert every "[\n\t\t[" to "[\n\t["
            write_str = write_str.replace('[\n\t\t[', '[\n\t[')

            file.write(write_str)
            file.write(";\n\n")


def preprocess(verbose=False):
    if verbose:
        print("Start preprocessing...")
    
    # compute commuting matrix and save as a .json file
    # u.generate_commuting_matrix()

    if verbose:
        print("Generated commuting matrix")

    # save all data in a .dat file
    input_data = u.merge_JSON_files(c.INPUT_JSON_PATHS)
    JSON_to_dat(c.DAT_FILE, json_data=input_data)

    if verbose:
        print("Generated .dat file")
    

def run_solver(verbose=False):
    if verbose:
        print("Start running solver...")
    
    # run the IBM solver
    os.system(c.EXECUTION_COMMAND)

    if verbose:
        print("Run ended")


def postprocess(exec_time=None, verbose=False):
    if verbose:
        print("Start postprocessing...")
    
    # retrieve output data and create a file in the data folder
    os.system(f'{c.OUT_TO_PY} {c.TMP_FILE} {c.SETUP_FILE} {c.OUTPUT_DATA}')

    # save the output data in a .json file
    with open(c.OUTPUT_DATA, 'r') as f:
        python_data = f.read()
    
    data = {}
    exec(python_data, data)
    json_data = {var_name: var_value for var_name, var_value in data.items() if not var_name.startswith('__')}

    if exec_time is not None:
        json_data[c.EXECUTION_TIME] = exec_time

    u.save_JSON(json_data, c.OUTPUT_JSON)

    if verbose:
        print("Output data saved")

    # remove the src file
    os.remove(c.TMP_FILE)
    os.remove(c.OUTPUT_DATA)
    os.system(f"touch {c.OUTPUT_DATA}")

    if verbose:
        print("Cleaning completed")
        print("Postprocessing completed")


def run(verbose=False):
    # clean eventual tmp files from previous runs
    if os.path.exists(c.TMP_FILE):
        os.remove(c.TMP_FILE)

    if os.path.exists(c.SETUP_FILE):
        os.remove(c.SETUP_FILE)

    if os.path.exists(c.OUTPUT_DATA):
        os.remove(c.OUTPUT_DATA)
        os.system(f"touch {c.OUTPUT_DATA}")

    preprocess(verbose)

    start_time = time.time()
    run_solver(verbose)
    end_time = time.time()

    exec_time = end_time - start_time
    # round to two decimals
    exec_time = round(exec_time, 2)

    if verbose:
        print(f"Execution time: {exec_time} s")

    postprocess(exec_time=exec_time, verbose=verbose)

    objective, optimality_gap = m.get_efficiency_metrics()

    if objective:
        if verbose:
            print(f"Objective: {objective}")
        return objective, optimality_gap, exec_time
    else:
        if verbose:
            print("No solution found")
        return False, False, exec_time
