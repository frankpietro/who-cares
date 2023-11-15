/*********************************************
 * OPL 22.1.1.0 Model
 * Author: frankp
 * Creation Date: May 13, 2023 at 9:51:04 PM
 *********************************************/

/****************************************************************
	CONSTANTS
****************************************************************/

int bigM = ...;
int WL = ...;

/****************************************************************
	END CONSTANTS
****************************************************************/


/****************************************************************
	SETS AND PROPERTIES
****************************************************************/

// time slots
int numDays = ...;
range Days = 1..numDays;

// patients
int numPatients = ...;
range Patients = 1..numPatients;

// operators
int numOperators = ...;
range Operators = 1..numOperators;
int operatorSkill[Operators] = ...;					// s_{o}
int operatorTime[Operators] = ...;					// h_{o}
float operatorWage[Operators] = ...;				// c_{o}
int operatorAvailability[Operators][Days] = ...;	// r_{od}
int operatorStartTime[Operators][Days] = ...;		// t_{od}^{1}		
int operatorEndTime[Operators][Days] = ...;			// t_{od}^{2}

// visits - indexed by patient and day
int visitRequest[Patients][Days] = ...;				// r_{pd}
int visitSkill[Patients][Days] = ...;				// s_{pd}
int visitStartTime[Patients][Days] = ...;			// t_{pd}^{1}		
int visitEndTime[Patients][Days] = ...;				// t_{pd}^{2}

// logistic network
int numNodes = numPatients + numOperators;
range Nodes = 1..numNodes;
int commutingTime[Nodes][Nodes] = ...;				// a_{ij}
float commutingCost = ...;							// gamma

/****************************************************************
	END SETS AND PROPERTIES
****************************************************************/

/****************************************************************
	PREPROCESSING PARAMETERS
****************************************************************/

// print info in a more readable way
int visitsPerPatient[Patients];
int patientRequiredTime[Patients];

// support for the computations
int feasiblePatients[Operators][Patients];

/****************************************************************
	END PREPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	PREPROCESSING
****************************************************************/

execute PATIENT_STATS {	
	for(var p in Patients){
		for(var d in Days){
			visitsPerPatient[p] += visitRequest[p][d];
			patientRequiredTime[p] += visitRequest[p][d] * (visitEndTime[p][d] - visitStartTime[p][d]);
		}
	}
	
	writeln("Visits per patient:", visitsPerPatient);
	writeln("Time required by patients:", patientRequiredTime);
}	


execute FEASIBLE_PATIENTS {
	for(var o in Operators){
		for(var p in Patients){
			var feasible = 1;
			for(var d in Days){
				// r_{pd} == 1 and r_{od} == 0 ==> unfeasible
				if(visitRequest[p][d] > operatorAvailability[o][d]){
					feasible = 0;
				}
				else if(visitRequest[p][d] == 1) {
				 	// t_{pd}^{1} < t_{od}^{1} + a_{op} ==> unfeasible
					if(visitStartTime[p][d] < operatorStartTime[o][d] + commutingTime[numPatients + o][p]){
						feasible = 0;
					}
					// t_{od}^{2} < t_{pd}^{2} + a_{po} ==> unfeasible
					if(operatorEndTime[o][d] < visitEndTime[p][d] + commutingTime[p][numPatients + o]){
						feasible = 0;
					}
					
				}
			}
			
			feasiblePatients[o][p] = feasible;
		}
	}
	
	writeln("Feasible patients per operator:");
	for(var o in Operators){
		writeln("Operator ", o, ":", feasiblePatients[o]);
	}
	
}

/****************************************************************
	END PREPROCESSING
****************************************************************/


/****************************************************************
	DECISION VARIABLES AND EXPRESSIONS
****************************************************************/

// decision variables
dvar boolean assignment[Patients][Operators];
dvar boolean movement[Nodes][Nodes][Operators][Days];
dvar int operatorWorkload[Operators];

// objective function: cost
dexpr float costs = sum(o in Operators)(
	sum(p in Patients)(
		assignment[p][o] * operatorWage[o] * sum(d in Days)(visitEndTime[p][d] - visitStartTime[p][d])
	) + commutingCost * sum(i in Nodes, j in Nodes)(
		commutingTime[i][j] * sum(d in Days)(movement[i][j][o][d])
	)) + WL * (max(o in Operators)(operatorWorkload[o]) - min(o in Operators)(operatorWorkload[o]));

/****************************************************************
	END DECISION VARIABLES AND EXPRESSIONS
****************************************************************/


/****************************************************************
	COMPUTATION
****************************************************************/

minimize costs;

subject to {
	// each patient must be assigned to exactly one operator
	forall (p in Patients){
		sum(o in Operators) assignment[p][o] == 1;
	}
	
	// each patient assigned to an operator must be in the feasible patients set for that operator
	forall (p in Patients, o in Operators){
		assignment[p][o] <= feasiblePatients[o][p];
	}
	
	// no operator works more than their contract states
	forall (o in Operators) {
		operatorWorkload[o] == sum(p in Patients)
			(assignment[p][o] * sum(d in Days)
				(visitRequest[p][d] * (visitEndTime[p][d] - visitStartTime[p][d])
			)
		);
		
		operatorWorkload[o] <= operatorTime[o];
	}
	
	
	/*
		OPERATOR MOVEMENT
	*/
	
	// no self loops
	forall(n in Nodes, o in Operators, d in Days){
		movement[n][n][o][d] == 0;
	}
	
	forall(o in Operators, d in Days){
		sum(p in Patients : feasiblePatients[o][p] == 1) movement[numPatients + o][p][o][d] <= 1;
		sum(p in Patients : feasiblePatients[o][p] == 1) movement[p][numPatients + o][o][d] <= 1;
	}
	
	// prevent both loops and unfeasible tours
	forall (o in Operators, d in Days, p1 in Patients : feasiblePatients[o][p1] == 1, p2 in Patients : feasiblePatients[o][p2] == 1 && p1 != p2 && visitRequest[p1][d] == 1 && visitRequest[p2][d] == 1) {
		visitEndTime[p1][d] + commutingTime[p1][p2] <= visitStartTime[p2][d] + bigM * (1 - movement[p1][p2][o][d]);
	}
	
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) {
		// operators that visit patients must arrive and left exactly once
		movement[numPatients + o][p][o][d] + sum(i in Patients : feasiblePatients[o][i] == 1) movement[i][p][o][d] == assignment[p][o] * visitRequest[p][d];
		movement[p][numPatients + o][o][d] + sum(j in Patients : feasiblePatients[o][j] == 1) movement[p][j][o][d] == assignment[p][o] * visitRequest[p][d];
		
		// operators must start by visiting one patients and end by visiting one patient
		operatorStartTime[o][d] + commutingTime[numPatients + o][p] <= visitStartTime[p][d] + bigM * (1 - movement[numPatients + o][p][o][d]);
		visitEndTime[p][d] + commutingTime[p][numPatients + o] <= operatorEndTime[o][d] + bigM * (1 - movement[p][numPatients + o][o][d]);
	}
};

/****************************************************************
	END COMPUTATION
****************************************************************/


/****************************************************************
	POSTPROCESSING PARAMETERS
****************************************************************/

//int shifts[Operators][Days];

/****************************************************************
	END POSTPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	POSTPROCESSING
****************************************************************/


execute OP_ASS {
	writeln("OPERATOR ASSIGNMENTS");
	for(var o in Operators){
		writeln("Operator ", o);
		for(var p in Patients){
			if(assignment[p][o] == 1){
				writeln("Assigned patient ", p)
			}
		}
		writeln("Workload: ", operatorWorkload[o]);
		writeln();
	}
	writeln();
}


execute MOV_COUNT {
	writeln("MOVEMENT COUNT");
    for (var o in Operators) {
    	writeln("Operator ", o)
    	for (var d in Days) {
    	  	writeln("Movements of day ", d);
    		for (var i in Nodes) {
    			for(var j in Nodes){
	    			if (movement[i][j][o][d] == 1){
	    				if(i<=numPatients && j<=numPatients){
	    					writeln("Movement from patient ", i, " to patient ", j);
	    				}
	    				if(i>numPatients && j<=numPatients) {
	    					writeln("Movement from operator ", i - numPatients, " to patient ", j);
	    				}
	    				if(i<=numPatients && j>numPatients) {
	    					writeln("Movement from patient ", i, " to operator ", j - numPatients);
	    				}
	    				if(i>numPatients && j>numPatients) {
	    					writeln("Movement from operator ", i - numPatients, " to operator ", j - numPatients)
	    				}
      				}	    			
      			}
       		}      			
    	}
    	writeln();
    }
}


/****************************************************************
	END POSTPROCESSING
****************************************************************/
