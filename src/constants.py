# folders
ARCHIVE_FOLDER = 'sim-data/'
# ARCHIVE_FOLDER = 'no-overskill/'
DATA_FOLDER = 'data/'
MODEL_FOLDER = 'model/'
SRC_FOLDER = 'src/'
SCRIPTS_FOLDER = 'scripts/'

DEF_ARCHIVE_FOLDER = 'prova/'

# data folder
OUTPUT_DATA = f'{DATA_FOLDER}output_data.py'
TMP_FILE = 'tmp.output'
SETUP_FILE = f'{MODEL_FOLDER}setup.output'
OP_STATS_CSV = 'operator_stats.csv'
SUMMARY_CSV = 'summary.csv'

HYPERPARAMS_JSON = f'{DATA_FOLDER}hyperparams.json'
MUNICIPALITY_JSON = f'{DATA_FOLDER}municipalities.json'
PATIENT_JSON = f'{DATA_FOLDER}patients.json'
OPERATOR_JSON = f'{DATA_FOLDER}operators.json'
VISIT_JSON = f'{DATA_FOLDER}visits.json'
COMM_JSON = f'{DATA_FOLDER}commuting.json'
ASS_JSON = f'{DATA_FOLDER}assignment.json'
OUTPUT_JSON = f'{DATA_FOLDER}output_data.json'

INPUT_JSON_PATHS = [
    HYPERPARAMS_JSON,
    MUNICIPALITY_JSON,
    PATIENT_JSON,
    OPERATOR_JSON,
    VISIT_JSON,
    COMM_JSON,
    ASS_JSON
]

# scripts folder
OUT_TO_PY = f'{SCRIPTS_FOLDER}out_to_py.sh'

# model folder
MOD_FILE = f'{MODEL_FOLDER}new_hcp.mod'
DAT_FILE = f'{MODEL_FOLDER}new_hcp.dat'

# OPL command
OPLRUN = '/home/frankp/ibm/ILOG/CPLEX_Studio2211/opl/bin/x86-64_linux/oplrun'
RUN_CONFIG = 'version-5'
EXECUTION_COMMAND = f'{OPLRUN} -p {MODEL_FOLDER} {RUN_CONFIG} >> {TMP_FILE}'

# indexes in daily schedule
SCH_PATIENT = 0
SCH_DAY = 1
SCH_SKILL = 2
SCH_START_TIME = 3
SCH_END_TIME = 4

# time
TIME_UNIT = 15
INTRA_MUN_TIME = 15

# default values for insertion
DEF_OP_AV = 1
DEF_OP_START_TIME = 0
DEF_OP_END_TIME = 840      # 14 hours, from 6.30 to 20.30
DEF_OP_DAY_DURATION = DEF_OP_END_TIME - DEF_OP_START_TIME

DEF_PAT_START_TIME = 30
DEF_PAT_END_TIME = 810
DEF_PAT_DAY_DURATION = DEF_PAT_END_TIME - DEF_PAT_START_TIME

MAX_TRIES = 10

# --------------- PARAMETER NAMES --------------- #

# INPUT
# hyperparameters
C_WAGE = 'Cw'
C_EXECUTION = 'Cx'
C_OVERSKILL = 'Co'
C_MOVEMENT = 'Cm'
BIG_M = 'bigM'

SIGMA0 = 'sigma0'
SIGMA1 = 'sigma1'
OMEGA = 'omega'

# COMM_COST = 'commutingCost'
N_DAYS = 'numDays'

N_MUNICIPALITIES = 'numMunicipalities'
MUN_LATITUDE = 'municipalityLatitude'
MUN_LONGITUDE = 'municipalityLongitude'
COMM_TIME = 'commutingTime'

# patients
N_PATIENTS = 'numPatients'
PAT_MUNICIPALITY = 'patientMunicipality'

# operators
N_OPERATORS = 'numOperators'
OP_MUNICIPALITY = 'operatorMunicipality'
OP_SKILL = 'operatorSkill'
OP_TIME = 'operatorTime'
OP_MAX_TIME = 'operatorMaxTime'
OP_AVAILABILITY = 'operatorAvailability'
OP_START_TIME = 'operatorStartTime'
OP_END_TIME = 'operatorEndTime'

PREV_ASS = 'previousAssignment'

# visits
VISIT_REQUEST = 'visitRequest'
VISIT_SKILL = 'visitSkill'
VISIT_START_TIME = 'visitStartTime'
VISIT_END_TIME = 'visitEndTime'

# useful sets of params
HYPERPARAMS = [C_WAGE, C_MOVEMENT, C_OVERSKILL, C_EXECUTION, BIG_M, SIGMA0, SIGMA1, OMEGA, N_DAYS, N_MUNICIPALITIES]
PAT_PARAMS = [PAT_MUNICIPALITY]
OP_PARAMS = [OP_MUNICIPALITY, OP_SKILL, OP_TIME, OP_MAX_TIME]
OP_DAILY_PARAMS = [OP_AVAILABILITY, OP_START_TIME, OP_END_TIME]
ALL_OP_PARAMS = [OP_MUNICIPALITY, OP_SKILL, OP_TIME, OP_MAX_TIME, OP_AVAILABILITY, OP_START_TIME, OP_END_TIME]
VISIT_PARAMS = [VISIT_REQUEST, VISIT_SKILL, VISIT_START_TIME, VISIT_END_TIME]
MUN_PARAMS = [MUN_LATITUDE, MUN_LONGITUDE]

NUMERIC_PARAMS = [C_WAGE, C_MOVEMENT, C_OVERSKILL, C_EXECUTION, BIG_M, SIGMA0, SIGMA1, OMEGA, N_DAYS, N_MUNICIPALITIES, N_PATIENTS, N_OPERATORS]

# DERIVED PARAMS
FEASIBLE_PATIENTS = 'feasiblePatients'

# OUTPUT
OBJECTIVE = 'objective'
ASSIGNMENT = 'assignment'
MOVEMENT = 'movement'
VISIT_EXEC = 'visitExecution'
OP_WORKLOAD = 'operatorWorkload'
OP_OVERTIME = 'operatorOvertime'

EXECUTION_TIME = 'executionTime'
OPTIMALITY_GAP = 'optimalityGap'

# --------------- END PARAMETER NAMES --------------- #


# --------------- DATA GENERATION --------------- #

# HYPERPARAMETERS
DEF_C_WAGE = 1
DEF_C_EXECUTION = 1000
DEF_C_OVERSKILL = 0
DEF_C_MOVEMENT = 1
DEF_BIG_M = 1000
DEF_SIGMA0 = 0.3
DEF_SIGMA1 = 0.1
DEF_OMEGA = 0.27
DEF_NUM_DAYS = 5
DEF_NUM_MUNICIPALITIES = 11

# MUNICIPALITIES
DEF_MIN_DIST = 20
DEF_MAX_DIST = 40

# OPERATORS
DEF_SKILL_DISTR = [0.75, 0.25]
DEF_MIN_BASE_TIME = 900
DEF_MAX_BASE_TIME = 2160
DEF_BASE_TIME_UNIT = 60
DEF_MAX_TIME = 2280

DEF_AV_PERC = 0.85
DEF_TIME_PERT = 60
DEF_START_TIME_PERT_DISTR = [0.85, 0.12, 0.03]
DEF_END_TIME_PERT_DISTR = [0.85, 0.12, 0.03]

# ASSIGNMENT
DEF_ASS_PERC = 0

# VISITS
DEF_CARE_PLAN_DISTR = [0.2, 0.2, 0.2, 0.2, 0.2]
DEF_PREMIUM_PERC = 0.15
DEF_N_INCREASES = 0


# --------------- END DATA GENERATION --------------- #

# --------------- STATS --------------- #

OPERATOR = 'operator'
SKILL = 'skill'
CONTRACT_TIME = 'contract time'
MAX_TIME = 'max time'
ASSIGNED_PATIENTS = 'assigned patients'
TOTAL_VISITS = 'total visits'
NOT_EXECUTED_VISITS = 'not executed visits'
WORKLOAD = 'workload'
OVERTIME = 'overtime'
TRAVEL_TIME = 'travel time'
INTER_TRAVEL_TIME = 'interm. travel time'
OVERSKILL_VISITS = 'overskill visits (%)'
OVERSKILL_TIME = 'overskill time (%)'

TEST_NUMBER = 'test number'
TYPE = 'type'
EXEC_TIME = 'execution time'
OPT_GAP = 'optimalityGap'

STATS_HEADER = [OPERATOR, SKILL, CONTRACT_TIME, MAX_TIME, ASSIGNED_PATIENTS, TOTAL_VISITS, NOT_EXECUTED_VISITS, WORKLOAD, OVERTIME, TRAVEL_TIME, INTER_TRAVEL_TIME, OVERSKILL_VISITS, OVERSKILL_TIME]
SUMMARY_HEADER = [TEST_NUMBER, TYPE, SKILL, CONTRACT_TIME, MAX_TIME, ASSIGNED_PATIENTS, TOTAL_VISITS, NOT_EXECUTED_VISITS, WORKLOAD, OVERTIME, TRAVEL_TIME, INTER_TRAVEL_TIME, OVERSKILL_VISITS, OVERSKILL_TIME, OBJECTIVE, OPT_GAP, EXEC_TIME]

# --------------- END STATS --------------- #


# --------------- MESA --------------- #

# id to be summed
PAT_BASE_ID = 0
OP_BASE_ID = 1000
VISIT_BASE_ID = 1000000

# operator states
IDLE = 0
TRAVELLING = 1
READY = 2
WORKING = 3
UNAVAILABLE = -1

OP_STATES = {
    IDLE: 'idle',
    TRAVELLING: 'travelling',
    READY: 'ready',
    WORKING: 'working',
    UNAVAILABLE: 'unavailable'
}

# visit states
NOT_SCHEDULED = 0
SCHEDULED = 1
EXECUTING = 2
EXECUTED = 3

VISIT_STATES = {
    NOT_SCHEDULED: 'not scheduled',
    SCHEDULED: 'scheduled',
    EXECUTING: 'executing',
    EXECUTED: 'executed'
}

# manager id
MANAGER_ID = 2208

# computation of criticity
SMOOTHING_CONSTANT = 0.1
TIME_OFFSET_CONSTANT = 5000
OBJ_CONSTANT = 1000

# time constants
MIN_NOTICE_TIME = 120
MAX_ALLOWED_DELAY = 60
SHORTENING_PERC = 0.15
BROKEN_TIME = 1110

# high-skill probability for low skill patients
HIGH_SKILL_PROB = 0.05

# how many per day unexpected events
NEW_VISIT_FREQUENCY = 4
SINGLE_CANCELLATION_FREQUENCY = 2
ALL_CANCELLATIONS_FREQUENCY = 0.2
NEW_PATIENT_FREQUENCY = 1
QUIT_DAY_FREQUENCY = 0.1
LATE_ENTRY_FREQUENCY = 1
EARLY_EXIT_FREQUENCY = 1

PROLONGED_VISIT_PROBABILITY = 0.1
PROLONGED_TRAVEL_PROBABILITY = 0.02
PROLONG_MIN = 10
PROLONG_MODE = 25
PROLONG_MAX = 60

NOISE_TIME = 5

# manager levels
DUMMY = 0
RANDOM = 1
OPTIMIZER = 2
ROBUST = 3

# --------------- END MESA --------------- #
