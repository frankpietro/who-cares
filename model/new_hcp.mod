/*********************************************
 * OPL 22.1.1.0 Model
 * Author: frankp
 * Creation Date: May 13, 2023 at 9:51:04 PM
 *********************************************/

/****************************************************************
	CONSTANTS
****************************************************************/

int bigM = ...;
float Cm = ...;
float Cw = ...;
float Cx = ...;
float Co = ...;

float sigma0 = ...;
float sigma1 = ...;
float omega = ...;

/****************************************************************
	END CONSTANTS
****************************************************************/


/****************************************************************
	SETS AND PROPERTIES
****************************************************************/

// time slots
int numDays = ...;											// W
range Days = 1..numDays;

// districts
int numMunicipalities = ...;
range Municipalities = 1..numMunicipalities;
int municipalityLatitude[Municipalities] = ...;
int municipalityLongitude[Municipalities] = ...;
int commutingTime[Municipalities][Municipalities] = ...;	// a_{m_{1}m_{2}}

// patients
int numPatients = ...;										// P
range Patients = 1..numPatients;
int patientMunicipality[Patients] = ...;					// m_{p}

// operators
int numOperators = ...;										// O
range Operators = 1..numOperators;
int operatorMunicipality[Operators] = ...;					// m_{o}
int operatorSkill[Operators] = ...;							// s_{o}
int operatorTime[Operators] = ...;							// h_{o}
int operatorMaxTime[Operators] = ...;						// \bar{h}_{o}
int operatorAvailability[Operators][Days] = ...;			// r_{od}
int operatorStartTime[Operators][Days] = ...;				// t_{od}^{1}
int operatorEndTime[Operators][Days] = ...;					// t_{od}^{2}

int previousAssignment[Patients][Operators] = ...;			// b_{po}

// visits - indexed by patient and day
int visitRequest[Patients][Days] = ...;						// r_{pd}
int visitSkill[Patients][Days] = ...;						// s_{pd}
int visitStartTime[Patients][Days] = ...;					// t_{pd}^{1}		
int visitEndTime[Patients][Days] = ...;						// t_{pd}^{2}

int feasiblePatients[Operators][Patients] = ...;			// F_{o}

int numNodes = numPatients + numOperators;
range Nodes = 1..numNodes;

/****************************************************************
	END SETS AND PROPERTIES
****************************************************************/

/****************************************************************
	DECISION VARIABLES AND EXPRESSIONS
****************************************************************/

// decision variables
dvar boolean assignment[Patients][Operators];				// x_{po}
dvar boolean movement[Nodes][Nodes][Operators][Days];		// y_{ij}^{od}
dvar boolean visitExecution[Operators][Patients][Days];		// z_{opd}

dvar int+ operatorWorkload[Operators];						// w_{o}
dvar int+ operatorOvertime[Operators];						// q_{o}

// objective function
dexpr float objective =
	Cm * (
		sum(o in Operators)(
			sum(d in Days, p1 in Patients, p2 in Patients : patientMunicipality[p1] != patientMunicipality[p2])(
				commutingTime[patientMunicipality[p1]][patientMunicipality[p2]] * movement[p1][p2][o][d]
			)
		)
	) +
	Cw * (
		sum(o in Operators)(
			(sigma0 + operatorSkill[o] * sigma1) * (operatorWorkload[o] + omega * operatorOvertime[o])
		)
	) +
	Cx * (
		sum(p in Patients, d in Days)(
			visitRequest[p][d] - sum(o in Operators) visitExecution[o][p][d]
		)
	) +
	Co * (
		sum(o in Operators, p in Patients, d in Days : visitSkill[p][d] < operatorSkill[o]) visitExecution[o][p][d]
	);

/****************************************************************
	END DECISION VARIABLES AND EXPRESSIONS
****************************************************************/


/****************************************************************
	COMPUTATION
****************************************************************/

minimize objective;

subject to {
	// each patient must be assigned to exactly one operator
	forall (p in Patients) assignmentConstraint :
		sum(o in Operators : feasiblePatients[o][p] == 1) assignment[p][o] == 1;
		
	forall (p in Patients) assignmentConsistency :
		sum(o in Operators : feasiblePatients[o][p] == 0) assignment[p][o] == 0;

	
	// if a patient was previously assigned to an operator, the assignment must stay
	forall (o in Operators, p in Patients : feasiblePatients[o][p] == 1) previousAssignmentConstraint :
		assignment[p][o] >= previousAssignment[p][o];
		
		
	// operators must execute requested visits
	forall (o in Operators, p in Patients, d in Days) visitExecutionConstraint :
		visitExecution[o][p][d] <= assignment[p][o] * visitRequest[p][d];
	
	
	// no operator works more than the maximum allowed
	forall (o in Operators) workloadComputation :
		operatorWorkload[o] == sum(p in Patients : feasiblePatients[o][p] == 1, d in Days)
			(visitExecution[o][p][d] * (visitEndTime[p][d] - visitStartTime[p][d]));
	
	forall (o in Operators) maxWorkloadConstraint :
		operatorWorkload[o] <= operatorMaxTime[o];
	
	
	// the overtime is computed in order to minimize it in the objective function	
	forall (o in Operators) overtimeComputation :
		operatorOvertime[o] >= operatorWorkload[o] - operatorTime[o];
		
	/*
		OPERATOR MOVEMENT
	*/
	
	// operators start their day from their homes and return there
	forall(o in Operators, d in Days : operatorAvailability[o][d] == 1) homeStartConstraint :
		sum(p in Patients : feasiblePatients[o][p] == 1) movement[numPatients + o][p][o][d] <= 1;
		
	forall(o in Operators, d in Days) homeEndConstraint :
		sum(p in Patients : feasiblePatients[o][p] == 1) movement[p][numPatients + o][o][d] <= 1;
	
	
	// operators that visit patients must arrive and left exactly once
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) patientArrivalConstraint :
		movement[numPatients + o][p][o][d] + sum(i in Patients : feasiblePatients[o][i] == 1 && i != p) movement[i][p][o][d] == visitExecution[o][p][d];
		
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) patientDepartureConstraint :
		movement[p][numPatients + o][o][d] + sum(j in Patients : feasiblePatients[o][j] == 1 && j != p) movement[p][j][o][d] == visitExecution[o][p][d];
	
	
	// operators must start by visiting one patients and end by visiting one patient
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) visitStartConstraint :
		operatorStartTime[o][d] + commutingTime[operatorMunicipality[o]][patientMunicipality[o]] <= visitStartTime[p][d] + bigM * (1 - movement[numPatients + o][p][o][d]);
	
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) visitEndConstraint :
		visitEndTime[p][d] + commutingTime[patientMunicipality[p]][operatorMunicipality[o]] <= operatorEndTime[o][d] + bigM * (1 - movement[p][numPatients + o][o][d]);
	
	
	// prevent both loops and unfeasible tours
	forall (o in Operators, d in Days, p1 in Patients : feasiblePatients[o][p1] == 1, p2 in Patients : feasiblePatients[o][p2] == 1 && p1 != p2 && visitRequest[p1][d] == 1 && visitRequest[p2][d] == 1) visitFeasibilityConstraint :
		visitEndTime[p1][d] + commutingTime[patientMunicipality[p1]][patientMunicipality[p2]] <= visitStartTime[p2][d] + bigM * (1 - movement[p1][p2][o][d]);
	
};

/****************************************************************
	END COMPUTATION
****************************************************************/


/****************************************************************
	POSTPROCESSING
****************************************************************/

execute PRINT_GAP{
}

execute PRINT_VARS {
	var gap = cplex.getMIPRelativeGap();
	writeln("optimalityGap = ", gap);
	writeln();
	writeln("assignment = [");
	for(var p in Patients){
		writeln(assignment[p], ",")
	}
	writeln("]");
	
	writeln("movement = [");
	for(var i in Nodes){
		writeln("[");
		for(var j in Nodes){
			writeln("[");
			for(var o in Operators){
				writeln(movement[i][j][o], ",");
			}
			writeln("],");
		}
		writeln("],");
	}
	writeln("]");
	
	
	writeln("operatorWorkload = ", operatorWorkload);
	writeln();
	
	writeln("operatorOvertime = ", operatorOvertime);
	writeln();
	
	writeln("visitExecution = [");
	for(var o in Operators){
		writeln("[");
		for(var p in Patients){
			writeln(visitExecution[o][p], ",")
		}
		writeln("],");
	}
	writeln("]");
}

/****************************************************************
	END POSTPROCESSING
****************************************************************/
