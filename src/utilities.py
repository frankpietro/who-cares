import os
import json
import numpy as np

import src.constants as c

import random
from scipy.spatial import distance_matrix


def get_time_units():
    return (c.DEF_PAT_END_TIME - c.DEF_PAT_START_TIME) // c.TIME_UNIT


# save a JSON to a location
def save_JSON(data, file_name):
    # save it in a .json file
    with open(file_name, 'w') as f:
        json.dump(data, f, indent=4)
    

# retrieve a JSON from a location - if it does not exist, create it
def retrieve_JSON(file_name):
    # if file_name does not exist, create it
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            f.write('{}')

    with open(file_name, 'r') as f:
        return json.load(f)
    

# read values from a JSON file
def read_values(json_file, var_names):
    json_data = retrieve_JSON(json_file)
    if isinstance(var_names, str):
        return json_data[var_names]
    else:
        return [json_data[var_name] for var_name in var_names]
    

# write values to a JSON file
def write_values(json_file, var_names, values):
    json_data = retrieve_JSON(json_file)
    if isinstance(var_names, str):
        json_data[var_names] = values
    else:
        for var_name, value in zip(var_names, values):
            json_data[var_name] = value

    save_JSON(json_data, json_file)


# merge a list of JSON files
def merge_JSON_files(json_paths):
    merged_json = {}
    for json_file in json_paths:
        json_data = retrieve_JSON(json_file)
        merged_json = {**merged_json, **json_data}

    return merged_json


# generate commuting matrix
def generate_commuting_matrix():
    municipality_data = retrieve_JSON(c.MUNICIPALITY_JSON)
    lats = municipality_data[c.MUN_LATITUDE]
    lons = municipality_data[c.MUN_LONGITUDE]

    # generate matrix with euclidean distances
    dm = distance_matrix(np.array([lats, lons]).T, np.array([lats, lons]).T)

    # convert all values to integers
    dm = dm.astype(int)
    
    # add intra-municipality time to diagonal
    np.fill_diagonal(dm, dm.diagonal() + c.INTRA_MUN_TIME)

    json_to_save = {"commutingTime": dm.tolist()}
    save_JSON(json_to_save, c.COMM_JSON)


# useful for visit generation
def generate_random_binary_matrix(rows, cols, num_ones):
    matrix = [[0] * cols for _ in range(rows)]  # Step 1: Initialize matrix with all ones

    indices = [(i, j) for i in range(rows) for j in range(cols)]  # Generate list of indices
    random.shuffle(indices)  # Shuffle the list of indices

    for index in indices[:num_ones]:  # Iterate through num_ones indices
        i, j = index
        matrix[i][j] = 1  # Set element to one

    return matrix


def archive_file(file_path, archive_folder_name):
    # if file does not exist, return
    if not os.path.exists(file_path):
        return False
    
    # create archive folder if it does not exist
    archive_folder = c.ARCHIVE_FOLDER + archive_folder_name
    if not os.path.exists(archive_folder):
        os.makedirs(archive_folder)

    archive_path = archive_folder + file_path.split('/')[-1]
    # copy file_path from its current location to archive_path
    os.system(f"cp {file_path} {archive_path}")

    return True


def restore_file(file_path, archive_folder_name):
    # create archive folder if it does not exist
    archive_folder = c.ARCHIVE_FOLDER + archive_folder_name
    if not os.path.exists(archive_folder):
        return False

    archive_path = archive_folder + file_path.split('/')[-1]
    # copy file_path from archive_path to its current location
    os.system(f"cp {archive_path} {file_path}")

    return True


def archive_scenario(folder_name):
    # check if folder exists
    if not os.path.exists(f"{c.ARCHIVE_FOLDER}{folder_name}"):
        os.makedirs(f"{c.ARCHIVE_FOLDER}{folder_name}")
    
    # copy each file in f"{c.DATA_FOLDER}" to f"{c.ARCHIVE_FOLDER}{folder_name}"
    for file_name in os.listdir(f"{c.DATA_FOLDER}"):
        # if it is a JSON
        if file_name.endswith('.json'):
            os.system(f"cp {c.DATA_FOLDER}{file_name} {c.ARCHIVE_FOLDER}{folder_name}")
    
    return True


def restore_scenario(folder_name):
    # check if folder exists
    if not os.path.exists(f"{c.ARCHIVE_FOLDER}{folder_name}"):
        return False
    
    # copy each file in f"{c.ARCHIVE_FOLDER}{folder_name}" to f"{c.DATA_FOLDER}"
    for file_name in os.listdir(f"{c.ARCHIVE_FOLDER}{folder_name}"):
        os.system(f"cp {c.ARCHIVE_FOLDER}{folder_name}{file_name} {c.DATA_FOLDER}")
    
    return True


def print_time_in_minutes(minutes):
    # 0: 6.30 a.m.; any number is 6.30 a.m. plus these minutes
    minutes += 390
    hours = minutes // 60
    minutes = minutes % 60
    
    return f"{hours:02d}:{minutes:02d}"


def print_day(day):
    if day == 0:
        return "Monday"
    elif day == 1:
        return "Tuesday"
    elif day == 2:
        return "Wednesday"
    elif day == 3:
        return "Thursday"
    elif day == 4:
        return "Friday"
    elif day == 5:
        return "Saturday"
    elif day == 6:
        return "Sunday"
    else:
        return "Invalid day"
