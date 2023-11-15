/*********************************************
 * OPL 22.1.1.0 Model
 * Author: frankp
 * Creation Date: May 13, 2023 at 9:51:04 PM
 *********************************************/

/****************************************************************
	CONSTANTS
****************************************************************/

int timeSlotDuration = ...;
int maxSkill = ...;
int minSkill = ...;
range Skills = minSkill..maxSkill;

/****************************************************************
	END CONSTANTS
****************************************************************/


/****************************************************************
	SETS AND PROPERTIES
****************************************************************/

// time slots
int numDays = ...;
range Days = 1..numDays;
int numTimeSlots = ...;
range TimeSlots = 1..numTimeSlots;

// patients
int numPatients = ...;
range Patients = 1..numPatients;

// operators
int numOperators = ...;
range Operators = 1..numOperators;
int operatorSkill[Operators] = ...;
float operatorWage[Operators] = ...;
int operatorTime[Operators] = ...;
int operatorAvailability[Operators][Days][TimeSlots] = ...;

// visits
int numVisits = ...;
range Visits = 1..numVisits;
int visitSkill[Visits] = ...;
int visitDuration[Visits] = ...;

// single visits - useful for indexing them
tuple SingleVisitT {
	int id;
	int patient;
	int visit;
	int day;
	int timeSlot;
}

// logistic network
int numNodes = numPatients + numOperators;
range Nodes = 1..numNodes;
int commutingTime[Nodes][Nodes] = ...;
float commutingCost = ...;

/****************************************************************
	END SETS AND PROPERTIES
****************************************************************/

/****************************************************************
	PARAMETERS
****************************************************************/

// requests
//int requests[Patients][TimeSlots][Visits] = ...;
{SingleVisitT} Requests = ...;

/****************************************************************
	END PARAMETERS
****************************************************************/


/****************************************************************
	PREPROCESSING PARAMETERS
****************************************************************/

// print info in a more readable way
int visitsPerPatient[Patients];
int visitsPerTimeSlot[Days][TimeSlots];
int patientRequiredTime[Patients];
int patientReqTimePerSkill[Patients][Skills];

int visitsPerVisitType[Visits];

// support for the computations
int requestsPerTimeSlot[Patients][Days][TimeSlots];
int feasiblePatients[Operators][Patients];

/****************************************************************
	END PREPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	PREPROCESSING
****************************************************************/

execute PATIENT_STATS {	
	for(var r in Requests){
		visitsPerPatient[r.patient] += 1;
		patientRequiredTime[r.patient] += visitDuration[r.visit];
		patientReqTimePerSkill[r.patient][visitSkill[r.visit]] += visitDuration[r.visit];
		requestsPerTimeSlot[r.patient][r.day][r.timeSlot] = 1;
		visitsPerTimeSlot[r.day][r.timeSlot] += 1;
		visitsPerVisitType[r.visit] += 1;
	}
	
	writeln("Visits per patient:", visitsPerPatient);
	writeln("Time required by patients:", patientRequiredTime);
	writeln("Time required by patients per skill:", patientReqTimePerSkill);
	writeln("Requests per time slot:", requestsPerTimeSlot);
	writeln("Visits per time slot:", visitsPerTimeSlot);
	writeln("Visits per type:", visitsPerVisitType);
}	


execute FEASIBLE_PATIENTS {
	for(var o in Operators){
		for(var p in Patients){
			var feasible = 1;
			for(var d in Days){
				for(var t in TimeSlots){
					if(requestsPerTimeSlot[p][d][t] > operatorAvailability[o][d][t]){
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


execute TIME_STATS {
	// total required and available time
	var requiredTime = 0;
	for(var v in visitsPerVisitType){
		requiredTime += visitsPerVisitType[v] * visitDuration[v];
	}
	writeln("Required time: ", requiredTime);
	
	var availableTime = 0;
	for(var o in Operators){
		var maxAvailability = 0;
		for(var d in Days){
			for(var t in TimeSlots){
				maxAvailability += operatorAvailability[o][d][t] * timeSlotDuration;
			}
		}		
		if(maxAvailability > operatorTime[o]){
			availableTime += operatorTime[o];
		}
		else {
			availableTime += maxAvailability;
		}
		
	}
	writeln("Available time: ", availableTime);
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

// objective function: cost
dexpr float costs = sum(o in Operators)(
	sum(p in Patients)(
		assignment[p][o] * operatorWage[o] * sum(r in Requests : r.patient == p)(visitDuration[r.visit])
	) + commutingCost * sum(i in Nodes, j in Nodes)(
		commutingTime[i][j] * sum(d in Days)(movement[i][j][o][d])
	)
);

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
    
    // each operator can handle maximum one request per time slot   
    forall (o in Operators, d in Days, t in TimeSlots){
    	sum(p in Patients)(assignment[p][o] * requestsPerTimeSlot[p][d][t]) <= operatorAvailability[o][d][t];
    }
    
	// no operator works more than their contract states
	forall (o in Operators) {
		sum(p in Patients)(assignment[p][o] * sum(r in Requests : r.patient == p)(visitDuration[r.visit])) <= operatorTime[o];
	}
	
	// operators move between patients
//	forall (o in Operators, p1 in Patients, p2 in Patients, d in Days, t1 in TimeSlots, t2 in TimeSlots : t1 < t2){
//		assignment[p1][o] * requestsPerTimeSlot[p1][d][t1] == 1 && assignment[p2][o] * requestsPerTimeSlot[p2][d][t2] == 1 && sum(t in t1+1..t2-1)(sum(p in Patients)(assignment[p][o] * requestsPerTimeSlot[p][d][t])) == 0 => movement[p1][p2][o][d] == 1;
//	}
//	
//	forall (o in Operators, p1 in Patients, d in Days, t1 in TimeSlots){
//		assignment[p1][o] * requestsPerTimeSlot[p1][d][t1] == 1 && sum(t in t1+1..numTimeSlots)(sum(p in Patients)(assignment[p][o] * requestsPerTimeSlot[p][d][t])) == 0 => movement[p1][numPatients + o][o][d] == 1;
//	}
//	
//	forall (o in Operators, p1 in Patients, d in Days, t1 in TimeSlots){
//		assignment[p1][o] * requestsPerTimeSlot[p1][d][t1] == 1 && sum(t in 1..t1-1)(sum(p in Patients)(assignment[p][o] * requestsPerTimeSlot[p][d][t])) == 0 => movement[numPatients + o][p1][o][d] == 1;
//	}

	// operator movement
	// prevent self loops
	forall (p in Patients, o in Operators, d in Days) {
		movement[p][p][o][d] == 0;
	}
	
	// prevents movements from one operator to another
	forall (o1 in Operators, o2 in Operators : o1 != o2, n in Nodes, d in Days) {
		movement[n][numPatients + o2][o1][d] == 0;
		movement[numPatients + o2][n][o1][d] == 0;
	}
	
	forall (p in Patients, o in Operators, d in Days, t in TimeSlots) {
		if (t == 1){
			movement[numPatients + o][p][o][d] == assignment[p][o] * requestsPerTimeSlot[p][d][t];
		}
		else {
			movement[numPatients + o][p][o][d] == assignment[p][o] * requestsPerTimeSlot[p][d][t] * (1 - sum(p1 in Patients)(assignment[p1][o] * requestsPerTimeSlot[p1][d][t-1]));
		}
	}
	
//	// if patient p has required a visit, someone must go there and then leave
//	forall (o in Operators, p in Patients, d in Days) {
//		sum(j in Nodes) movement[p][j][o][d] == sum(t in TimeSlots) assignment[p][o] * requestsPerTimeSlot[p][d][t];
//		sum(i in Nodes) movement[i][p][o][d] == sum(t in TimeSlots) assignment[p][o] * requestsPerTimeSlot[p][d][t];
//	}
//	
//	forall (o in Operators, d in Days) {
//		sum(j in Nodes) movement[numPatients + o][j][o][d] == 1;
//		sum(i in Nodes) movement[i][numPatients + o][o][d] == 1;
//	}
//	
//	// subtour elimination
//	forall (o in Operators, d in Days, p1 in Patients, p2 in Patients) {
//		movement[p1][p2][o][d] + movement[p2][p1][o][d] <= 1;
//	}
};

/****************************************************************
	END COMPUTATION
****************************************************************/


/****************************************************************
	POSTPROCESSING PARAMETERS
****************************************************************/

int shifts[Operators][Days][TimeSlots];

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
	}
	writeln();
}


execute OP_STATS {
	writeln("OPERATOR STATS");
	for(var o in Operators){
		writeln("Operator ", o);
		for(var d in Days){
			for(var t in TimeSlots){
				writeln("Day ", d, ", time slot ", t);
				var shift = 0;
				for(var r in Requests){
				  	if(assignment[r.patient][o] * requestsPerTimeSlot[r.patient][d][t] > 0 && r.day == d && r.timeSlot == t){
						shift += visitDuration[r.visit];
						writeln("Visited patient ", r.patient);
	   				}					
				}
			shifts[o][d][t] = shift;
			}
		}		
	}
	
	writeln("Total shifts per operator:");
	for(var o in Operators){
		writeln("Operator ", o, ": ", shifts[o]);
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
