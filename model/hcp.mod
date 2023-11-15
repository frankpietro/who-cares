/*********************************************
 * OPL 22.1.1.0 Model
 * Author: frankp
 * Creation Date: May 13, 2023 at 9:51:04 PM
 *********************************************/

/****************************************************************
	CONSTANTS
****************************************************************/

int bigM = ...;
int Cw = ...;
int Cx = ...;

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
float patientLatitude[Patients] = ...;
float patientLongitude[Patients] = ...;

// operators
int numOperators = ...;
range Operators = 1..numOperators;
int operatorSkill[Operators] = ...;					// s_{o}
int operatorTime[Operators] = ...;					// h_{o}
float operatorWage[Operators] = ...;				// c_{o}
int operatorAvailability[Operators][Days] = ...;	// r_{od}
int operatorStartTime[Operators][Days] = ...;		// t_{od}^{1}		
int operatorEndTime[Operators][Days] = ...;			// t_{od}^{2}
float operatorLatitude[Operators] = ...;
float operatorLongitude[Operators] = ...;


// visits - indexed by patient and day
int visitRequest[Patients][Days] = ...;				// r_{pd}
int visitSkill[Patients][Days] = ...;				// s_{pd}
int visitStartTime[Patients][Days] = ...;			// t_{pd}^{1}		
int visitEndTime[Patients][Days] = ...;				// t_{pd}^{2}
int visitPriority[Patients][Days] = ...;

/****************************************************************
	END SETS AND PROPERTIES
****************************************************************/

/****************************************************************
	PREPROCESSING PARAMETERS
****************************************************************/

// logistic network
int numNodes = numPatients + numOperators;
range Nodes = 1..numNodes;
float commutingTime[Nodes][Nodes] = ...;			// a_{ij}
float commutingCost = ...;							// gamma

// support for the computations
int feasiblePatients[Operators][Patients];

/****************************************************************
	END PREPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	PREPROCESSING
****************************************************************/

/*
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
*/


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
	
	write("feasiblePatients = [");
	for(var o in Operators){
		writeln(feasiblePatients[o], ",");
	}
	
	writeln("]");
//	writeln("feasiblePatients = ", feasiblePatients);
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
dvar boolean visitExecution[Operators][Patients][Days];

// objective function: cost
dexpr float objective = sum(o in Operators)(
//	operatorWage[o] * sum(p in Patients)(
//		 sum(d in Days)(visitExecution[o][p][d] * (visitEndTime[p][d] - visitStartTime[p][d]))) + 
	commutingCost * sum(i in Nodes, j in Nodes)(
		commutingTime[i][j] * sum(d in Days)(movement[i][j][o][d])
	))
//	+ Cw * (max(o in Operators)(operatorWorkload[o]) - min(o in Operators)(operatorWorkload[o]))
	+ Cx * (sum(p in Patients, d in Days) (visitRequest[p][d] - sum(o in Operators) visitExecution[o][p][d]));

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
		sum(o in Operators) assignment[p][o] == 1;
	
	
	// each patient assigned to an operator must be in the feasible patients set for that operator
	forall (p in Patients, o in Operators) patientFeasibilityConstraint :
		assignment[p][o] <= feasiblePatients[o][p];
	
	
	// operators must execute requested visits
	forall (o in Operators, p in Patients, d in Days) visitExecutionConstraint :
		visitExecution[o][p][d] <= assignment[p][o] * visitRequest[p][d];
	
	
	// no operator works more than their contract states
	forall (o in Operators) workloadComputation :
		operatorWorkload[o] == sum(p in Patients, d in Days)
			(visitExecution[o][p][d] * (visitEndTime[p][d] - visitStartTime[p][d]));
	
		
	forall (o in Operators) workloadConstraint :
		operatorWorkload[o] <= operatorTime[o];
	
	/*
		OPERATOR MOVEMENT
	*/
	
	// no self loops
	forall(n in Nodes, o in Operators, d in Days) selfLoopConstraint :
		movement[n][n][o][d] == 0;
		
	
	forall(o in Operators, d in Days) homeStartConstraint :
		sum(p in Patients : feasiblePatients[o][p] == 1) movement[numPatients + o][p][o][d] <= 1;
		
		
	forall(o in Operators, d in Days) homeEndConstraint :
		sum(p in Patients : feasiblePatients[o][p] == 1) movement[p][numPatients + o][o][d] <= 1;
	
	
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) patientArrivalConstraint :
		// operators that visit patients must arrive and left exactly once
		movement[numPatients + o][p][o][d] + sum(i in Patients : feasiblePatients[o][i] == 1) movement[i][p][o][d] == visitExecution[o][p][d];
	
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) patientDepartureConstraint :
		movement[p][numPatients + o][o][d] + sum(j in Patients : feasiblePatients[o][j] == 1) movement[p][j][o][d] == visitExecution[o][p][d];
		
	
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) visitStartConstraint :
		// operators must start by visiting one patients and end by visiting one patient
		operatorStartTime[o][d] + commutingTime[numPatients + o][p] <= visitStartTime[p][d] + bigM * (1 - movement[numPatients + o][p][o][d]);
	
	forall (o in Operators, d in Days, p in Patients : feasiblePatients[o][p] == 1) visitEndConstraint :
		visitEndTime[p][d] + commutingTime[p][numPatients + o] <= operatorEndTime[o][d] + bigM * (1 - movement[p][numPatients + o][o][d]);
	
	
	// prevent both loops and unfeasible tours
	forall (o in Operators, d in Days, p1 in Patients : feasiblePatients[o][p1] == 1, p2 in Patients : feasiblePatients[o][p2] == 1 && p1 != p2 && visitRequest[p1][d] == 1 && visitRequest[p2][d] == 1) visitFeasibilityConstraint :
		visitEndTime[p1][d] + commutingTime[p1][p2] <= visitStartTime[p2][d] + bigM * (1 - movement[p1][p2][o][d]);

};

/****************************************************************
	END COMPUTATION
****************************************************************/


/****************************************************************
	POSTPROCESSING
****************************************************************/

execute PRINT_VARS {
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
	
	
	writeln("workload = ", operatorWorkload);
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


//execute OP_ASS {
//	writeln("OPERATOR ASSIGNMENTS");
//	for(var o in Operators){
//		writeln("Operator ", o);
//		for(var p in Patients){
//			if(assignment[p][o] == 1){
//				writeln("Assigned patient ", p)
//			}
//		}
//		writeln("Workload: ", operatorWorkload[o]);
//		writeln();
//	}
//	writeln();
//}
//
//
//execute MOV_COUNT {
//	writeln("MOVEMENT COUNT");
//    for (var o in Operators) {
//    	writeln("Operator ", o)
//    	for (var d in Days) {
//    	  	writeln("Movements of day ", d);
//    		for (var i in Nodes) {
//    			for(var j in Nodes){
//	    			if (movement[i][j][o][d] == 1){
//	    				if(i<=numPatients && j<=numPatients){
//	    					writeln("Movement from patient ", i, " to patient ", j);
//	    				}
//	    				if(i>numPatients && j<=numPatients) {
//	    					writeln("Movement from operator ", i - numPatients, " to patient ", j);
//	    				}
//	    				if(i<=numPatients && j>numPatients) {
//	    					writeln("Movement from patient ", i, " to operator ", j - numPatients);
//	    				}
//	    				if(i>numPatients && j>numPatients) {
//	    					writeln("Movement from operator ", i - numPatients, " to operator ", j - numPatients)
//	    				}
//      				}	    			
//      			}
//       		}      			
//    	}
//    	writeln();
//    }
//}
//
//
//execute VISIT_EXEC {
//	writeln("VISIT EXECUTION");
//	var total_ex = 0;
//	var total_not_ex = 0;
//	for (var p in Patients) {
//		for (var d in Days) {
//			if (visitRequest[p][d] == 1){
//				writeln("Patient ", p , " requested visit on day ", d);
//				var executed = 0;
//				for (var o in Operators){
//					if (visitExecution[o][p][d] == 1){
//						writeln("Visit executed by operator ", o);
//						executed = 1;
//					}
//				}
//				if (executed == 0){
//					writeln("Visit not executed!");
//				}
//				total_ex += executed;
//				total_not_ex += (1 - executed);
// 			}
//		}
//	}
//	
//	writeln();
//	writeln("Total executed visits: ", total_ex);
//	writeln("Total not executed visits: ", total_not_ex);
//	writeln();
//}
//
//
//execute COSTS {
//	writeln("ACTUAL COSTS");
//	var costs = 0;
//	for (var p in Patients){
//		var patient_costs = 0;
//		for (var o in Operators){
//			for (var d in Days){
//				patient_costs += visitExecution[o][p][d] * (visitEndTime[p][d] - visitStartTime[p][d]);
//			}
//		}
//		costs += patient_costs;
//		writeln(patient_costs, " spent for patient ", p);
//	}
//	
//	var movement_costs = 0;
//	for (var i in Nodes){
//		for (var j in Nodes){
//			for (var o in Operators){
//				for (var d in Days){
//					movement_costs += movement[i][j][o][d] * commutingTime[i][j] * commutingCost;
//				}
//			}
//		}
//	}
//	writeln("Movement costs: ", movement_costs);
//	
//	costs += movement_costs;
//	writeln("Total costs: ", costs);
//}


/****************************************************************
	END POSTPROCESSING
****************************************************************/
