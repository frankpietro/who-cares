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
float visitPercThreshold = ...;

/****************************************************************
	END CONSTANTS
****************************************************************/


/****************************************************************
	SETS AND PROPERTIES
****************************************************************/

// operators
int numOperators = ...;
range Operators = 1..numOperators;
int operatorSkill[Operators] = ...;
float operatorWage[Operators] = ...;
int operatorTime[Operators] = ...;

// visits
int numVisits = ...;
range Visits = 1..numVisits;
int visitSkill[Visits] = ...;
int visitTime[Visits] = ...;

// patients
int numPatients = ...;
range Patients = 1..numPatients;

// time slots
int numTimeSlots = ...;
range TimeSlots = 1..numTimeSlots;
range Days = 1..(numTimeSlots div 2);

/****************************************************************
	END SETS AND PROPERTIES
****************************************************************/

/****************************************************************
	PARAMETERS
****************************************************************/

// requests
int requests[Patients][TimeSlots][Visits] = ...;

/****************************************************************
	END PARAMETERS
****************************************************************/


/****************************************************************
	PREPROCESSING PARAMETERS
****************************************************************/

int visitsPerPatient[Patients];
int visitsPerTimeSlot[TimeSlots];
int visitsPerVisitType[Visits];
int patientRequiredTime[Patients];
int patientReqTimePerSkill[Patients][Skills];
int minGlobalContinuity[Patients];

/****************************************************************
	END PREPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	PREPROCESSING
****************************************************************/

execute PATIENT_STATS {
	for(var p in Patients){
		minGlobalContinuity[p] = minSkill;
		for(var t in TimeSlots){
			for(var v in Visits){
				visitsPerPatient[p] += requests[p][t][v];
				patientRequiredTime[p] += requests[p][t][v] * visitTime[v];
				patientReqTimePerSkill[p][visitSkill[v]] += requests[p][t][v] * visitTime[v];
			}
		}
		
		// computing minimum global continuity
		for(var s in Skills){
			// if visits of a certain skill level
			// are above the percentage threshold,
			// continuity is enforced for all visits
			if(minGlobalContinuity[p] < s && (patientReqTimePerSkill[p][s] / patientRequiredTime[p]) > visitPercThreshold){
				minGlobalContinuity[p] = s;
			}
		} 
	}
	
	writeln("Visits per patient:", visitsPerPatient);
	writeln("Time required by patients:", patientRequiredTime);
	writeln("Time required by patients per skill:", patientReqTimePerSkill);
	writeln("Minimum global continuity:", minGlobalContinuity);
}	


execute VISIT_STATS {
	// Visits per time slot
	for(var t in TimeSlots){
		var vpts = 0;
		for(var p in Patients){
			for(var v in Visits){
				vpts += requests[p][t][v];
			}
		}
		visitsPerTimeSlot[t] = vpts;
	}
	writeln("Visits per time slot:", visitsPerTimeSlot);
	
	// Visits per visit type
	for(var v in Visits){
		var vpv = 0;
		for(var t in TimeSlots){
			for(var p in Patients){
				vpv += requests[p][t][v];
			}
		}
		visitsPerVisitType[v] = vpv;
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
		availableTime += operatorTime[o];
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
dvar boolean assignment[Patients][TimeSlots][Visits][Operators];

// objective function: cost
dexpr float totalWage = sum(p in Patients, t in TimeSlots, v in Visits, o in Operators) assignment[p][t][v][o] * visitTime[v] * operatorWage[o];

/****************************************************************
	END DECISION VARIABLES AND EXPRESSIONS
****************************************************************/


/****************************************************************
	COMPUTATION
****************************************************************/

minimize totalWage;

subject to {
	// each visit must be done
	forall (p in Patients, t in TimeSlots, v in Visits) {
        sum(o in Operators) assignment[p][t][v][o] == requests[p][t][v];
    }
    
    // the skill of the operator must be g.e. than the skill required for the visit
    forall (p in Patients, t in TimeSlots, v in Visits) {
        sum(o in Operators) assignment[p][t][v][o] * operatorSkill[o] >= requests[p][t][v] * visitSkill[v];
    }
    
    // sum of visit times for all patients, visits, and operators should be l.e. than the time slot duration
	forall (t in TimeSlots, o in Operators)	{
	    sum(p in Patients, v in Visits) assignment[p][t][v][o] * visitTime[v] <= timeSlotDuration;
	}
	
	// sum of visit times for all patients, time slots, and visits should be less than or equal to the available working time of the operator.
	forall (o in Operators)	{
	    sum(p in Patients, t in TimeSlots, v in Visits) assignment[p][t][v][o] * visitTime[v] <= operatorTime[o];
	}
	
	// no operator works more than its daily time
	forall (o in Operators, d in Days) {
		sum(p in Patients, v in Visits, t in (2*d-1)..(2*d))(assignment[p][t][v][o] * visitTime[v]) <= operatorTime[o] / 5;
	}
	
	// minimum global continuity
//	forall (p in Patients, t in TimeSlots, v in Visits, o in Operators){
//		assignment[p][t][v][o] * operatorSkill[o] >= assignment[p][t][v][o] * minGlobalContinuity[p];
//	}
	
	// care continuity constraint for same skill level visits
	forall (p in Patients){
		sum(
			v1 in Visits,
			v2 in Visits : visitSkill[v1] == visitSkill[v2] || (minGlobalContinuity[p] > visitSkill[v1] || minGlobalContinuity[p] > visitSkill[v2]),
			t1 in TimeSlots,
			t2 in TimeSlots : t1 != t2,
			o1 in Operators,
			o2 in Operators : o1 != o2)(assignment[p][t1][v1][o1] * assignment[p][t2][v2][o2]) <= 0;
	}
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

/****************************************************************
	END POSTPROCESSING PARAMETERS
****************************************************************/


/****************************************************************
	POSTPROCESSING
****************************************************************/

execute OP_STATS {
	for(var o in Operators){
		for(var t in TimeSlots){
			var shift = 0;
			for(var p in Patients){
				for(var v in Visits){
					shift += assignment[p][t][v][o] * visitTime[v];
				}
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
	for (var p in Patients) {
		for (var t in TimeSlots) {
			for (var v in Visits) {
				for (var o in Operators) {
					if (assignment[p][t][v][o] == 1) {
						operatorCount[p][o] = 1;
					}
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

/****************************************************************
	END POSTPROCESSING
****************************************************************/
