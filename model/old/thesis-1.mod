/*********************************************
 * OPL 22.1.1.0 Model
 * Author: frankp
 * Creation Date: May 13, 2023 at 9:51:04 PM
 *********************************************/

/****************************************************************
	CONSTANTS
****************************************************************/

int timeSlotDuration = ...;
int maxDailyTime  = ...;
int maxSkill = ...;
int minSkill = ...;
range Skills = minSkill..maxSkill;
float visitPercThreshold = ...;

/****************************************************************
	END CONSTANTS
****************************************************************/


/****************************************************************
	SETS AND PROPERTIES
****************************************************************/

// time slots
int numTimeSlots = ...;
range TimeSlots = 1..numTimeSlots;
range Days = 1..(numTimeSlots div 2);

// operators
int numOperators = ...;
range Operators = 1..numOperators;
int operatorSkill[Operators] = ...;
float operatorWage[Operators] = ...;
int operatorTime[Operators] = ...;
int operatorAvailability[Operators][TimeSlots] = ...;

// visits
int numVisits = ...;
range Visits = 1..numVisits;
int visitSkill[Visits] = ...;
int visitTime[Visits] = ...;

// patients
int numPatients = ...;
range Patients = 1..numPatients;
int commutingTime[Patients][Patients] = ...;
int initialCommutingTime[Patients] = ...;
int commutingCost = ...;

// single visits - useful for indexing them
tuple SingleVisitT {
	int id;
	int patient;
	int visit;
	int timeSlots[TimeSlots];
	int priority;
}

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

int visitsPerPatient[Patients];
int patientRequiredTime[Patients];
int patientReqTimePerSkill[Patients][Skills];

int minGlobalContinuity[Patients];

int visitsPerVisitType[Visits];

/****************************************************************
	END PREPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	PREPROCESSING
****************************************************************/

execute PATIENT_STATS {	
	for(var r in Requests){
		visitsPerPatient[r.patient] += 1;
		patientRequiredTime[r.patient] += visitTime[r.visit];
		patientReqTimePerSkill[r.patient][visitSkill[r.visit]] += visitTime[r.visit];
	}
		
	for(var p in Patients){
		minGlobalContinuity[p] = minSkill;
		// computing minimum global continuity
		for(var s in Skills){
			// if visits of a certain skill level
			// are above the percentage threshold,
			// continuity is enforced for all visits
			if(
				minGlobalContinuity[p] < s && (
					(patientReqTimePerSkill[p][s] / patientRequiredTime[p]) > visitPercThreshold ||
					(patientReqTimePerSkill[p][s] == patientRequiredTime[p] && patientRequiredTime[p] != 0)
				)
			){				
				minGlobalContinuity[p] = s;
			}
		}
	}
	
	writeln("Visits per patient:", visitsPerPatient);
	writeln("Time required by patients:", patientRequiredTime);
	writeln("Time required by patients per skill:", patientReqTimePerSkill);
	writeln("Minimum global continuity:", minGlobalContinuity);
}	


execute VISIT_PRE_STATS {
	// Visits per visit type
	for(var r in Requests){
		visitsPerVisitType[r.visit] += 1;
	}
	writeln("Visits per type:", visitsPerVisitType);
}


execute TIME_STATS {
	// total required and available time
	var requiredTime = 0;
	for(var v in visitsPerVisitType){
		requiredTime += visitsPerVisitType[v] * visitTime[v];
	}
	writeln("Required time: ", requiredTime);
	
	var availableTime = 0;
	for(var o in Operators){
		var maxAvailability = 0;
		for(var t in TimeSlots){
			maxAvailability += operatorAvailability[o][t] * timeSlotDuration;
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
dvar boolean scheduling[Requests][TimeSlots][Operators];
dvar boolean operatorMovement[Operators][TimeSlots][Patients][Patients];
dvar boolean startingPatient[Operators][TimeSlots][Patients];
//dvar boolean assignment[Patients][Operators];

// objective function: cost
dexpr float totalWage = sum(r in Requests, t in TimeSlots, o in Operators) (
	scheduling[r][t][o] * visitTime[r.visit] * operatorWage[o] + 
	sum(p1 in Patients, p2 in Patients) (operatorMovement[o][t][p1][p2] * commutingTime[p1][p2] * (operatorWage[o] + commutingCost)) + 
	sum(p in Patients) (startingPatient[o][t][p] * initialCommutingTime[p] * (operatorWage[o] + commutingCost))
);

/****************************************************************
	END DECISION VARIABLES AND EXPRESSIONS
****************************************************************/


/****************************************************************
	COMPUTATION
****************************************************************/

minimize totalWage;

subject to {
	// each visit must be done
	forall (r in Requests) {
        sum(t in TimeSlots, o in Operators) scheduling[r][t][o] == 1;
    }
    
    forall (r in Requests, t in TimeSlots, o in Operators){
    	// the time slot of each visit must be feasible
    	scheduling[r][t][o] == 1 => r.timeSlots[t] == 1;
	    // the operator must be available when handling the request
    	scheduling[r][t][o] == 1 => operatorAvailability[o][t] == 1;
    	// the skill of the operator must be g.e. than the skill required for the visit
    	scheduling[r][t][o] == 1 => operatorSkill[o] >= visitSkill[r.visit];
    	// minimum global continuity
		scheduling[r][t][o] * operatorSkill[o] >= scheduling[r][t][o] * minGlobalContinuity[r.patient];
    }
    
    // time spent by each operator during each time slot should be l.e. than the time slot duration
	forall (t in TimeSlots, o in Operators)	{
	    sum(r in Requests) (scheduling[r][t][o] * visitTime[r.visit]) +
	    sum(p1 in Patients, p2 in Patients : p1 != p2) (operatorMovement[o][t][p1][p2] * commutingTime[p1][p2]) + 
	    sum(p in Patients) (startingPatient[o][t][p] * initialCommutingTime[p])
	    <= timeSlotDuration;
	}
	
	// sum of visit times for all patients, time slots, and visits should be less than or equal to the available working time of the operator.
	forall (o in Operators)	{
	    sum(r in Requests, t in TimeSlots) (scheduling[r][t][o] * visitTime[r.visit]) +
	    sum(p1 in Patients, p2 in Patients : p1 != p2, t in TimeSlots) (operatorMovement[o][t][p1][p2] * commutingTime[p1][p2]) + 
	    sum(p in Patients, t in TimeSlots) (startingPatient[o][t][p] * initialCommutingTime[p])
	    <= operatorTime[o];
	}
	
	// no operator works more than its daily time
	forall (o in Operators, d in Days) {
	    sum(r in Requests, t in (2*d-1)..(2*d)) (scheduling[r][t][o] * visitTime[r.visit]) +
	    sum(p1 in Patients, p2 in Patients : p1 != p2, t in (2*d-1)..(2*d)) (operatorMovement[o][t][p1][p2] * commutingTime[p1][p2]) + 
	    sum(p in Patients, t in (2*d-1)..(2*d)) (startingPatient[o][t][p] * initialCommutingTime[p])
		<= maxDailyTime;
	}
	
	// operator movement between patients
	forall (o in Operators, t in TimeSlots, p1 in Patients, p2 in Patients : p1 != p2) {
	    operatorMovement[o][t][p1][p2] + operatorMovement[o][t][p2][p1] <= 1;  // Ensure at most one movement between two patients in a time slot by an operator
	}
	
	// operator movement consistency with scheduling
	forall (r1 in Requests, r2 in Requests, t in TimeSlots, o in Operators : r1.patient != r2.patient) {
	    scheduling[r1][t][o] + scheduling[r2][t][o] == 2 => operatorMovement[o][t][r1.patient][r2.patient] + operatorMovement[o][t][r2.patient][r1.patient] == 1;
	}
	
	// operator movement consistency within time slots
	forall (t in TimeSlots, o in Operators, p1 in Patients) {
	    sum(p2 in Patients : p1 != p2) operatorMovement[o][t][p1][p2] <= 1;  // Operator can move to at most one patient from patient p1 within a time slot
	}
	
	// operators must start from just one patient
	forall (o in Operators, t in TimeSlots) {
	    sum(p in Patients) startingPatient[o][t][p] <= 1;
	}
	
	// operators do not move to the starting patient
	forall (o in Operators, t in TimeSlots, p1 in Patients, p2 in Patients : p1 != p2) {
	    startingPatient[o][t][p1] == 1 => operatorMovement[o][t][p2][p1] == 0;
	}
		
	
	// care continuity constraint for same skill level visits
//	forall (p in Patients){
//		sum(
//			r1 in Requests,
//			r2 in Requests : visitSkill[r1.visit] == visitSkill[r2.visit] || (minGlobalContinuity[p] > visitSkill[r1.visit] || minGlobalContinuity[p] > visitSkill[r2.visit]),
//			t1 in TimeSlots,
//			t2 in TimeSlots : t1 != t2,
//			o1 in Operators,
//			o2 in Operators : o1 != o2)(scheduling[r1][t1][o1] * scheduling[r2][t2][o2]) <= 0;
//	}
};

/****************************************************************
	END COMPUTATION
****************************************************************/


/****************************************************************
	POSTPROCESSING PARAMETERS
****************************************************************/

int shifts[Operators][TimeSlots];
int operatorCount[Patients][Operators];
int visitedOperators[Patients];

int visitsPerTimeSlot[TimeSlots];

/****************************************************************
	END POSTPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	POSTPROCESSING
****************************************************************/



execute VISIT_POST_STATS {
	// Visits per time slot
	for(var t in TimeSlots){
		var vpts = 0;
		for(var r in Requests){
			for(var o in Operators){
				vpts += scheduling[r][t][o];
			}
		}
		visitsPerTimeSlot[t] = vpts;
	}
	writeln("Visits per time slot:", visitsPerTimeSlot);
}

execute OP_STATS {
	for(var o in Operators){
		for(var t in TimeSlots){
			var shift = 0;
			for(var r in Requests){
				shift += scheduling[r][t][o] * visitTime[r.visit];
			}
		shifts[o][t] = shift;
		}
	}
	
	writeln("Total shifts per operator:");
	for(var o in Operators){
		writeln(shifts[o]);
	}
}


execute OP_COUNT {
	for (var r in Requests) {
		for (var t in TimeSlots) {
			for (var o in Operators) {
				if (scheduling[r][t][o] == 1) {
					operatorCount[r.patient][o] = 1;
				}
			}
		}
	}
	
	writeln("Number of operators that visited each patient:");
	for(var p in Patients){
		for(var o in Operators){
			visitedOperators[p] += operatorCount[p][o];
		}
	}
	writeln(visitedOperators);	
}

execute MOV_COUNT {
//    for (var o in Operators) {
//        writeln("Movements of Operator ", o, ":");
//        for (var t in TimeSlots) {
//        	writeln("Time slot ", t)
//            for (var p1 in Patients) {
//                for (var p2 in Patients) {
//                    if (operatorMovement[o][t][p1][p2] == 1) {
//                        writeln("Patient ", p1, " -> patient ", p2);
//                    }
//                }
//            }
//        }
//        writeln();
//    }
    
    for (var o in Operators) {
    	writeln("Operator ", o)
    	for (var t in TimeSlots) {
    	  	writeln("Time slot ", t);
    		for (var r in Requests) {
    			if (scheduling[r][t][o] == 1)
    				writeln("request from patient ", r.patient);
    		}
    	}
    	writeln();
    }
}


/****************************************************************
	END POSTPROCESSING
****************************************************************/
