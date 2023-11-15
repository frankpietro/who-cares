# from typing import Any
from mesa import Agent, Model
from mesa.time import RandomActivation
from itertools import groupby
from mesa.datacollection import DataCollector
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

import src.constants as c
import src.utilities as u
import src.manipulation as m
import src.stats as s
import src.sim_util as su



class Patient(Agent):
    def __init__(self, unique_id : int, model : 'HCModel', municipality : int, premium=False, assigned_operator_id=None, newly_generated=False):
        self.unique_id = unique_id
        self.model = model

        self.municipality = municipality
        self.premium = premium

        self.assigned_operator_id = assigned_operator_id

        self.newly_generated = newly_generated

        # stats
        self.newly_generated_visits = 0
        self.is_removed = False

    
    def _initialize_premium(self) -> bool:
        own_visits = self.own_visits()
        for v in own_visits:
            if v.skill == 0:
                return False
        
        return True


    def __str__(self):
        ret_str = f"Patient {self.unique_id} (municipality {self.municipality})"
        if self.premium:
            ret_str += " - premium"

        return ret_str


    def __repr__(self):
        return self.__str__()

    
    def own_visits(self) -> list['Visit']:
        return [visit for visit in self.model.visits if visit.patient_id == self.unique_id]


    def preferred_operators(self) -> list[int]:
        visits = self.own_visits()
        fav_ops = {}
        for v in visits:
            sch_op_id = v.scheduled_operator_id
            if sch_op_id is not None:
                if sch_op_id in fav_ops:
                    fav_ops[sch_op_id] += 1
                else:
                    fav_ops[sch_op_id] = 1
            else:
                prop_op_id = v.proposed_operator_id
                if prop_op_id is not None:
                    if prop_op_id in fav_ops:
                        fav_ops[prop_op_id] += 1
                    else:
                        fav_ops[prop_op_id] = 1
        
        # sort by values (descending)
        fav_ops = {k: v for k, v in sorted(fav_ops.items(), key=lambda item: item[1], reverse=True)}
        
        return list(fav_ops.keys())


    def preferred_start_times(self) -> list[int]:
        visits = self.own_visits()
        fav_times = {}
        for v in visits:
            prop_start_time = v.proposed_start_time
            if prop_start_time is not None:
                if prop_start_time in fav_times:
                    fav_times[prop_start_time] += 1
                else:
                    fav_times[prop_start_time] = 1
        
        # sort by values (descending)
        fav_times = {k: v for k, v in sorted(fav_times.items(), key=lambda item: item[1], reverse=True)}
        
        return list(fav_times.keys())


    def has_visit(self, day) -> bool:
        return len([v for v in self.own_visits() if v.real_day == day and v.state != c.NOT_SCHEDULED]) > 0

    # ------------ VISIT GENERATION ------------
    
    def select_skill(self) -> int:
        if self.premium is True:
            return 1
        else:
            return np.random.rand() < self.model.high_skill_prob
        

    def select_duration(self) -> int:
        visit_duration_distr = self.model.get_visit_duration_distribution()
        durations = list(visit_duration_distr.keys())
        probs = list(visit_duration_distr.values())

        return np.random.choice(durations, p=probs)
    

    def select_start_time(self, duration : int, day : int) -> int:
        first_av_time = self.model.current_time if day == self.model.current_day and self.model.current_time > c.DEF_PAT_START_TIME else c.DEF_PAT_START_TIME
        
        preferred_start_times = self.preferred_start_times()
        for pst in preferred_start_times:
            if pst >= first_av_time:
                return pst
        
        first_av_slot = first_av_time // c.TIME_UNIT
        last_av_slot = (c.DEF_PAT_END_TIME - duration) // c.TIME_UNIT

        if self.model.debug:
            print(f"Patient {self.unique_id} has {last_av_slot - first_av_slot} available slots")

        if first_av_slot > last_av_slot:
            return None
        elif first_av_slot == last_av_slot:
            return first_av_slot * c.TIME_UNIT

        slot = np.random.randint(first_av_slot, last_av_slot)

        return slot * c.TIME_UNIT 
       
    
    def select_slot(self, duration : int) -> tuple[int, int]:
        possible_days = list(range(self.model.current_day, self.model.n_days))

        own_visits = self.own_visits()

        available_days = [d for d in possible_days if len([v for v in own_visits if v.proposed_day == d]) == 0]

        if self.model.debug:
            print(f"Patient {self.unique_id} has {len(available_days)} available days: {available_days}")

        if len(available_days) == 0:
            return None, None
        
        # shuffle days
        np.random.shuffle(available_days)

        for day in available_days:
            start_time = self.select_start_time(duration, day)
            if start_time is not None:
                return day, start_time
        
        return None, None


    def generate_new_visit(self) -> bool:
        skill = self.select_skill()
        duration = self.select_duration()
        day, start_time = self.select_slot(duration)

        if day is None or start_time is None:
            if self.model.verbose:
                print(f"Patient {self.unique_id} has no available slots")

            return False

        self.model.add_visit(self.unique_id, day, skill, start_time, start_time+duration, newly_generated=True)
        return True


    def cancellable_visits(self) -> list['Visit']:
        return [v for v in self.own_visits() if v.state == c.SCHEDULED and (v.real_day > self.model.current_day or (v.real_day == self.model.current_day and v.real_start_time > self.model.current_time + c.MIN_NOTICE_TIME))]


    def cancel_visit(self) -> bool:
        canc_visits = self.cancellable_visits()
        if len(canc_visits) == 0:
            return False
        
        np.random.shuffle(canc_visits)
        visit_to_remove = canc_visits[0]

        if self.model.verbose:
            print(f"Patient {self.unique_id} is cancelling visit {visit_to_remove.unique_id} to operator {visit_to_remove.real_operator_id} in municipality {self.model.get_operator(visit_to_remove.real_operator_id).municipality} on day {visit_to_remove.real_day} at time {u.print_time_in_minutes(visit_to_remove.real_start_time)}")
        
        self.model.remove_visit(visit_to_remove)
        
        return True


    def cancel_all_visits(self) -> bool:
        canc_visits =  self.cancellable_visits()
        if len(canc_visits) == 0:
            return False
        
        for v in canc_visits:
            self.model.remove_visit(v)
        
        self.is_removed = True

        return True

    # ------------ END VISIT GENERATION ------------

    
    def step(self):
        if not self.is_removed:
            if self.model.current_time > c.DEF_PAT_START_TIME and self.model.current_time < c.DEF_PAT_END_TIME:
                # new visit
                if np.random.rand() * su.day_adjustment(self.model.current_day) < self.model.p_new_visit:
                    if self.model.verbose:
                        print(f"Patient {self.unique_id} is generating a new visit")
                    
                    self.newly_generated_visits += self.generate_new_visit()

                # cancellation
                if np.random.rand() * su.day_adjustment(self.model.current_day) < self.model.p_single_canc:
                    self.cancel_visit()

                # all cancellations
                if np.random.rand() * su.day_adjustment(self.model.current_day) < self.model.p_all_canc:
                    if self.model.verbose:
                        print(f"Patient {self.unique_id} is cancelling all visits")
                    
                    self.cancel_all_visits()



class Operator(Agent):
    def __init__(self,
        unique_id,
        model : 'HCModel',
        municipality,
        skill : int,
        time : int,
        max_time : int,
        availability : list[int],
        start_time : list[int],
        end_time : list[int],
        state=c.IDLE
    ):
        self.unique_id = unique_id
        self.model = model
        
        self.municipality = municipality
        self.skill = skill
        self.time = time
        self.max_time = max_time

        self.availability = availability
        self.start_time = start_time
        self.end_time = end_time

        self.state = state
        self.current_municipality = municipality

        # if idle state
        self.next_visit = None
        self.etd = None
        # useful for travelling
        self.current_edge = None
        self.eta = None

        self.executed_visits = 0
        self.workload = 0

        self.real_travel_time = 0
        self.real_inter_travel_time = 0

        self.is_reimbursed = False
        self.travel_to_reimburse = 0

        self.overskill_visits = 0
        self.overskill_time = 0


    def __str__(self):
        return f"Operator {self.unique_id} (municipality {self.municipality}, skill {self.skill}, contract time {self.time})"


    def __repr__(self):
        return self.__str__()


    def retrieve_schedule(self, only_scheduled=False, day=None) -> list['Visit']:
        schedule = []
        for visit in self.model.visits:
            if day is not None and visit.real_day != day:
                continue

            if visit.real_operator_id == self.unique_id and (visit.state == c.SCHEDULED or ((visit.state == c.EXECUTED or visit.state == c.EXECUTING) and not only_scheduled)):
                    schedule.append(visit)

        # sort by day and start time
        schedule = sorted(schedule, key=lambda visit: (visit.real_day, visit.real_start_time))    
        
        return schedule


    # ------------ WORKLOAD COMPUTATION ------------

    def compute_done_workload(self, schedule=None):
        dw = 0

        if schedule is None:
            schedule = self.retrieve_schedule()

        for visit in schedule:
            if visit.state == c.EXECUTED:
                dw += visit.real_end_time - visit.real_start_time

        return dw


    def compute_real_workload(self, schedule=None):
        rw = 0

        if schedule is None:
           schedule = self.retrieve_schedule()

        for visit in schedule:
            if visit.state == c.SCHEDULED or visit.state == c.EXECUTING or visit.state == c.EXECUTED:
                rw += visit.real_end_time - visit.real_start_time

        return rw
    

    def compute_scheduled_workload(self, schedule=None):
        sw = 0

        if schedule is None:
            schedule = self.retrieve_schedule()

        for visit in schedule:
            if visit.state == c.SCHEDULED:
                sw += visit.scheduled_end_time - visit.scheduled_start_time

        return sw


    def n_executed_visits(self, schedule=None):
        ev = 0

        if schedule is None:
            schedule = self.retrieve_schedule()

        for visit in schedule:
            if visit.state == c.EXECUTED:
                ev += 1
        
        return ev


    def n_not_executed_visits(self):
        nev = 0

        for p in self.model.patients:
            if p.assigned_operator_id == self.unique_id:
                nev += len([v for v in p.own_visits() if v.state == c.NOT_SCHEDULED])

        return nev


    def remaining_contract_time(self):
        return np.max([0,self.time - self.compute_done_workload()])


    def remaining_max_time(self):
        return np.max([0,self.max_time - self.compute_done_workload()])


    def n_assigned_patients(self):
        return sum([p.assigned_operator_id == self.unique_id for p in self.model.patients])


    def patients_to_visit(self):
        schedule = self.retrieve_schedule()
        pats = [v.patient_id for v in schedule if v.state == c.SCHEDULED]

        return list(set(pats))


    def compute_total_wage(self):
        base_workload = np.min([self.time, self.workload])
        overtime_workload = np.max([0, self.workload - self.time])

        wage_per_minute = self.model.sigma0 + self.skill * self.model.sigma1

        total_wage = wage_per_minute * (base_workload + overtime_workload * (1 + self.model.omega))

        return total_wage

    # ------------ END WORKLOAD COMPUTATION ------------


    # ------------ SCHEDULE UTILS ------------

    def estimated_return_home_time(self, day, schedule=None):
        if schedule is None:
            schedule = self.retrieve_schedule(day=day)

        if len(schedule) == 0:
            return self.end_time[day]
        
        return np.max([schedule[-1].real_end_time + self.model.graph[schedule[-1].get_mun()][self.municipality]['weight'], self.end_time[day]])


    def cumulable_delay(self, day, start_time=None, end_time=None, schedule=None):
        if schedule is None:
            schedule = self.retrieve_schedule(day=day)
        
        if len(schedule) == 0:
            return -1

        cumul_delay = 0

        from_time = start_time if start_time is not None else self.start_time[day]
        to_time = end_time if end_time is not None else self.end_time[day]

        # compute time between start of day and first visit - travel time
        first_visit = schedule[0]

        time_distance = self.model.graph[self.municipality][first_visit.get_mun()]['weight']
        
        cumul_delay += np.max([0, np.min([to_time, first_visit.real_start_time]) - from_time - time_distance])

        if self.model.debug:
            print(f"From time: {from_time}; first visit end time: {first_visit.real_end_time}")

        if from_time < first_visit.real_end_time:
            shortening_time = first_visit.shortening_time()
            cumul_delay += np.min([shortening_time, first_visit.real_end_time - from_time])

        if self.model.debug:
            print(f"Cumul delay after first visit: {cumul_delay}")
        
        # compute time between one visit and the other - travel time
        for i in range(len(schedule) - 1):
            current_visit = schedule[i]
            next_visit = schedule[i + 1]

            time_distance = self.model.graph[current_visit.get_mun()][next_visit.get_mun()]['weight']

            cumul_delay += np.max([0, np.min([next_visit.real_start_time, to_time]) - np.max([from_time, current_visit.real_end_time]) - time_distance])

            if from_time < next_visit.real_end_time and next_visit.real_start_time < to_time:
                shortening_time = next_visit.shortening_time()
                cumul_delay += np.min([shortening_time, next_visit.real_end_time - from_time, to_time - next_visit.real_start_time])

            if self.model.debug:
                print(f"Cumul delay after visit {i}: {cumul_delay}")

        # compute time between last visit and end of day - travel time
        last_visit = schedule[-1]
        
        time_distance = self.model.graph[last_visit.get_mun()][self.municipality]['weight']

        cumul_delay += np.max([0, to_time - np.max([from_time, last_visit.real_end_time]) - time_distance])

        if self.model.debug:
            print(f"Cumul delay after last visit: {cumul_delay}")

        if end_time is None:
            cumul_delay += (self.end_time[day] - self.estimated_return_home_time(day, schedule=schedule))
            if self.model.debug:
                print(f"Cumul delay after return home: {cumul_delay}")

        return cumul_delay


    def available_for_municipality(self, municipality=None, day=None, schedule=None):
        if municipality is not None:
            if schedule is None:
                schedule = self.retrieve_schedule()

            availabilities = []

            for d in range(self.model.n_days):
                if (day is not None and day == d) or day is None:
                    daily_availabilities = []
                    # if operator is not available, skip
                    if self.availability[d] == 0:
                        if day is None:
                            availabilities.append(daily_availabilities)
                            continue
                        else:
                            return daily_availabilities
                    
                    subschedule = [visit for visit in schedule if visit.real_day == d]

                    # case 1: if no visits, always available
                    if len(subschedule) == 0:
                        # compute distance between operator municipality and municipality
                        time_distance = self.model.graph[self.municipality][municipality]['weight']

                        av_window = (self.start_time[d] + time_distance, self.end_time[d] - time_distance)

                        daily_availabilities.append(av_window)
    
                    else:
                        # compute availability from start of d to first visit
                        first_visit = subschedule[0]

                        start_time_distance = self.model.graph[self.municipality][municipality]['weight']
                        end_time_distance = self.model.graph[first_visit.get_mun()][municipality]['weight']

                        first_av_window = (self.start_time[d] + start_time_distance, first_visit.real_start_time - end_time_distance)
                        
                        if first_av_window[0] < first_av_window[1]:
                            daily_availabilities.append(first_av_window)

                        # compute availability between visits
                        for i in range(len(subschedule) - 1):
                            current_visit = subschedule[i]
                            next_visit = subschedule[i + 1]

                            start_time_distance = self.model.graph[current_visit.get_mun()][municipality]['weight']
                            end_time_distance = self.model.graph[next_visit.get_mun()][municipality]['weight']

                            av_window = (current_visit.real_end_time + start_time_distance, next_visit.real_start_time - end_time_distance)
                            
                            if av_window[0] < av_window[1]:
                                daily_availabilities.append(av_window)
                        
                        # compute availability from last visit to end of d
                        last_visit = subschedule[-1]
                        
                        start_time_distance = self.model.graph[last_visit.get_mun()][municipality]['weight']
                        end_time_distance = self.model.graph[self.municipality][municipality]['weight']

                        last_av_window = (last_visit.real_end_time + start_time_distance, self.end_time[d] - end_time_distance)
                        
                        if last_av_window[0] < last_av_window[1]:
                            daily_availabilities.append(last_av_window)
                    
                    if day is None:
                        availabilities.append(daily_availabilities)
                    else:
                        return daily_availabilities
            
            return availabilities
    
        else:
            schedule = self.retrieve_schedule()

            # if no municipality is specified, return availability for all municipalities
            all_availabilities = []
            
            for municipality in range(self.model.n_municipalities):
                availabilities = self.available_for_municipality(municipality=municipality, day=day, schedule=schedule)
                all_availabilities.append(availabilities)

            return all_availabilities


    def available_for_time_period(self, start_time, end_time, municipality=None, day=None, schedule=None):
        if schedule is None:
            schedule = self.retrieve_schedule()

        availabilities = self.available_for_municipality(municipality=municipality, day=day, schedule=schedule)

        if municipality is not None and day is not None:
            for av_window in availabilities:
                if av_window[0] <= start_time and av_window[1] >= end_time:
                    return True
            
            return False
        
        elif (municipality is not None and day is None) or (municipality is None and day is not None):
            ret_av = []

            for single_av in availabilities:
                available = False
                for av_window in single_av:
                    if av_window[0] <= start_time and av_window[1] >= end_time:
                        available = True
                
                ret_av.append(available)
        
            return ret_av

        else:
            ret_av = []

            for mun_av in availabilities:
                m_av = []
                for daily_av in mun_av:
                    available = False
                    for av_window in daily_av:
                        if av_window[0] <= start_time and av_window[1] >= end_time:
                            available = True
                            
                    m_av.append(available)
                    
                ret_av.append(m_av)
        
            return ret_av


    def available_for_visit(self, visit : 'Visit', schedule=None):
        if visit.skill > self.skill:
            return False

        if schedule is None:
            schedule = self.retrieve_schedule()

        return self.available_for_time_period(start_time=visit.proposed_start_time, end_time=visit.proposed_end_time, municipality=visit.get_mun(), day=visit.proposed_day, schedule=schedule)
    

    def possible_visits(self, duration, day, municipality=None, start_time=c.DEF_PAT_START_TIME, end_time=c.DEF_PAT_END_TIME):
        if municipality is not None:
            # compute how many visits the operator can execute in the municipality from start time to end time
            availabilities = self.available_for_municipality(municipality=municipality, day=day)
            actual_availabilities = su.get_actual_availabilities(availabilities, start_time, end_time)
            possible_visits = su.calculate_possible_visits(actual_availabilities, duration)
        
        else:
            # if no municipality is specified, return availability for all municipalities
            all_availabilities = self.available_for_municipality(day=day)

            all_possible_visits = []
            for mun_av in all_availabilities:
                actual_availabilities = su.get_actual_availabilities(mun_av, start_time, end_time)
                possible_visits = su.calculate_possible_visits(actual_availabilities, duration)
                all_possible_visits.append(possible_visits)

            return all_possible_visits


    def possible_times_to_start_visit(self, duration, day, municipality):
        availabilities = self.available_for_municipality(municipality=municipality, day=day)
        possible_start_times = []
        for pst in range(c.DEF_PAT_START_TIME, c.DEF_PAT_END_TIME - duration):
            if su.is_possible_start_time(availabilities, pst, duration):
                possible_start_times.append(pst)

        return possible_start_times


    def added_travel_costs(self, day, time, municipality, schedule=None):
        # print(f"Operator {self.unique_id} is in municipality {self.municipality} at time {time} on day {day}")
        # retrieve previous municipality and next municipality with respect to time
        if schedule is None:
            schedule = self.retrieve_schedule(day=day)

        if len(schedule) == 0:
            if self.municipality == municipality:
                return 0
            else:
                return 2 * self.model.graph[self.municipality][municipality]['weight']

        prev_mun = None
        next_mun = None
        
        if time < schedule[0].real_start_time:
            prev_mun = self.municipality
            next_mun = schedule[0].get_mun()

        elif time > schedule[-1].real_end_time:
            prev_mun = schedule[-1].get_mun()
            next_mun = self.municipality

        else:
            for i in range(len(schedule) - 1):
                if time >= schedule[i].real_end_time and time <= schedule[i + 1].real_start_time:
                    prev_mun = schedule[i].get_mun()
                    next_mun = schedule[i + 1].get_mun()
                    break
        
        if prev_mun is None or next_mun is None:
            print("Error in input data")
            return 0

        # print(f"Operator {self.unique_id} is travelling from municipality {prev_mun} to municipality {next_mun}")

        first_new = self.model.graph[municipality][prev_mun]['weight'] if municipality != prev_mun else 0
        second_new = self.model.graph[next_mun][municipality]['weight'] if municipality != next_mun else 0
        old = self.model.graph[prev_mun][next_mun]['weight'] if prev_mun != next_mun else 0
        
        return first_new + second_new - old


    def wage_increment(self, visit_duration):
        # formula: (sigma0 + operatorSkill[o] * sigma1) * (operatorWorkload[o] + omega * operatorOvertime[o])
        overtime = np.max([0, self.workload - self.time + visit_duration])
        return (self.model.sigma0 + self.skill * self.model.sigma1) * (self.workload + overtime * (1 + self.model.omega))

    # ------------ END SCHEDULE UTILS ------------


    # ------------ SCHEDULE CHANGES ------------

    def try_shrink_visit(self, visit : 'Visit', postponing_time):
        if self.model.handle_delay:
            # if late, shrink visits up to 15%
            short_time = visit.shortening_time()
            if short_time > 0 and postponing_time > 0:
                shrink_time = np.min([short_time, postponing_time])
                visit.shrink(shrink_time, start=True)
                if self.model.verbose:
                    print("Shrinking visit " + str(visit.unique_id) + " to patient " + str(visit.patient_id) + " in municipality " + str(self.model.get_patient(visit.patient_id).municipality) + " from " + u.print_time_in_minutes(visit.real_start_time) + " to " + u.print_time_in_minutes(visit.real_end_time) + " by " + str(shrink_time) + " minutes")
                
                postponing_time -= shrink_time

        return postponing_time        


    def try_stretch_visit(self, visit : 'Visit', stretch_time, recovered_time, schedule):
        if self.model.handle_delay and stretch_time > 0:
            total_delay = self.cumulable_delay(visit.real_day, start_time=visit.real_end_time, schedule=schedule)
            stretch_time = np.min([stretch_time, np.max([0, total_delay])])

            if stretch_time > 0:
                visit.stretch(stretch_time, start=False)
                if self.model.verbose:
                    print("Stretching visit " + str(visit.unique_id) + " to patient " + str(visit.patient_id) + " in municipality " + str(visit.get_mun()) + " from " + u.print_time_in_minutes(visit.real_start_time) + " to " + u.print_time_in_minutes(visit.real_end_time) + " by " + str(stretch_time) + " minutes")

                recovered_time -= stretch_time

        return recovered_time


    def extend_visit(self, visit : 'Visit', stretch_time, schedule=None):
        if visit.real_operator_id != self.unique_id:
            return False
        
        if schedule is None:
            schedule = self.retrieve_schedule(day=visit.real_day)

        # if visit is the last one of the day, stretch without limits
        if visit == schedule[-1]:
            if self.model.verbose:
                print("Stretching visit " + str(visit.unique_id) + " to patient " + str(visit.patient_id) + " in municipality " + str(self.model.get_patient(visit.patient_id).municipality) + " from " + u.print_time_in_minutes(visit.real_start_time) + " to " + u.print_time_in_minutes(visit.real_end_time) + " by " + str(stretch_time) + " minutes")
    
            visit.stretch(stretch_time, start=False)
            return True

        cumulable_delay = self.cumulable_delay(visit.real_day, start_time=visit.real_end_time, schedule=schedule)
        
        if cumulable_delay + c.MAX_ALLOWED_DELAY > stretch_time:
            # if the visit is the last one and is delayable, delay and stop
            if visit.unique_id == schedule[-1].unique_id:
                visit.stretch(stretch_time, start=False)
                return True

            visits_to_postpone = []

            for i in range(len(schedule) - 1):
                if schedule[i].unique_id == visit.unique_id:
                    delay = stretch_time
                    visit_index = i
                    while delay > 0 and visit_index < len(schedule) - 1:
                        this_visit = schedule[visit_index]

                        # delay next visits
                        next_visit = schedule[visit_index + 1]

                        time_distance = self.model.graph[this_visit.get_mun()][next_visit.get_mun()]['weight']

                        postponing_time = np.max([0, this_visit.real_end_time + time_distance + delay - next_visit.real_start_time])

                        postponing_time = self.try_shrink_visit(next_visit, postponing_time)
                            
                        if postponing_time > 0:
                            visits_to_postpone.append((visit_index+1, postponing_time))

                        delay = postponing_time
                        visit_index += 1
                    
            for visit_to_postpone in visits_to_postpone:
                if self.model.verbose:
                    print("Postponing visit " + str(schedule[visit_to_postpone[0]].unique_id) + " to patient " + str(schedule[visit_to_postpone[0]].patient_id) + " in municipality " + str(self.model.get_patient(schedule[visit_to_postpone[0]].patient_id).municipality) + " from " + u.print_time_in_minutes(schedule[visit_to_postpone[0]].real_start_time) + " to " + u.print_time_in_minutes(schedule[visit_to_postpone[0]].real_end_time) + " by " + str(visit_to_postpone[1]) + " minutes")
    
                schedule[visit_to_postpone[0]].postpone(visit_to_postpone[1])

            if self.model.verbose:
                print("Stretching visit " + str(visit.unique_id) + " to patient " + str(visit.patient_id) + " in municipality " + str(self.model.get_patient(visit.patient_id).municipality) + " from " + u.print_time_in_minutes(visit.real_start_time) + " to " + u.print_time_in_minutes(visit.real_end_time) + " by " + str(stretch_time) + " minutes")
            visit.stretch(stretch_time, start=False)
        
        else:
            # reschedule one of the visits
            if self.model.verbose:
                print("Can't do it")
            
            # deschedule last visit
            visit_to_reschedule = schedule[-1]
            visit_to_reschedule.deschedule()
            self.model.overly_delayed_visits += 1

            self.extend_visit(visit, stretch_time)


    def shorten_visit(self, visit : 'Visit', shrink_time, schedule=None):
        if visit.real_operator_id != self.unique_id:
            return False
        
        if schedule is None:
            schedule = self.retrieve_schedule(day=visit.real_day)

        if self.model.verbose:
            print("Shortening visit " + str(visit.unique_id) + " to patient " + str(visit.patient_id) + " in municipality " + str(self.model.get_patient(visit.patient_id).municipality) + " from " + u.print_time_in_minutes(visit.real_start_time) + " to " + u.print_time_in_minutes(visit.real_end_time) + " by " + str(shrink_time) + " minutes")
        
        visit.shrink(shrink_time, start=False)

        subseq_visits = [v for v in schedule if v.real_start_time >= visit.real_start_time]

        recovered_time = shrink_time

        for i in range(len(subseq_visits) - 1):
            this_visit = subseq_visits[i]
            next_visit = subseq_visits[i + 1]

            lag_time = self.cumulable_delay(visit.real_day, start_time=this_visit.real_end_time, end_time=next_visit.real_start_time, schedule=schedule)
            if self.model.debug:
                print(f"Lag time between visit {this_visit.unique_id} and visit {next_visit.unique_id}: {lag_time}")

            shortened_time = this_visit.shortened_time() if i != 0 else 0
            if self.model.debug:
                print(f"Shortened time for visit {this_visit.unique_id}: {shortened_time}")
            
            delay = next_visit.get_delay()
            if self.model.debug:
                print(f"Delay for visit {next_visit.unique_id}: {delay}")

            anticipate_time = np.min([lag_time, delay])
            if anticipate_time > 0:
                next_visit.anticipate(anticipate_time)
                if self.model.verbose:
                    print("Anticipating visit " + str(next_visit.unique_id) + " to patient " + str(next_visit.patient_id) + " in municipality " + str(next_visit.get_mun()) + " from " + u.print_time_in_minutes(next_visit.real_start_time) + " to " + u.print_time_in_minutes(next_visit.real_end_time) + " by " + str(anticipate_time) + " minutes")

                lag_time -= anticipate_time

            stretch_time = np.min([shortened_time, lag_time, recovered_time])

            recovered_time = self.try_stretch_visit(this_visit, stretch_time, recovered_time, schedule)

        last_visit = subseq_visits[-1]
        last_shortened_time = last_visit.shortened_time()

        lag_time = np.max([0, self.end_time[visit.real_day] - last_visit.real_end_time - self.model.graph[last_visit.get_mun()][self.municipality]['weight']])

        if self.model.debug:
            print(f"Lag time between last visit {last_visit.unique_id} and return home: {lag_time}")

        stretch_time = np.min([last_shortened_time, recovered_time, lag_time])

        if stretch_time > 0:
            last_visit.stretch(stretch_time, start=False)
            if self.model.verbose:
                print("Stretching visit " + str(last_visit.unique_id) + " to patient " + str(last_visit.patient_id) + " in municipality " + str(last_visit.get_mun()) + " from " + u.print_time_in_minutes(last_visit.real_start_time) + " to " + u.print_time_in_minutes(last_visit.real_end_time) + " by " + str(np.min([last_shortened_time, recovered_time])) + " minutes")

            recovered_time -= stretch_time

        return True
              

    # happens only when travelling
    def extend_travel(self, extend_time):
        # 1: delay eta
        self.eta += extend_time

        # 2a: if no subsequent visit, operator was returning home, so be it
        if self.next_visit is None:
            if self.model.verbose:
                print(f"Operator {self.unique_id} is returning home with a delay of {extend_time} minutes; ETA: {u.print_time_in_minutes(self.eta)}")
            return

        # 2b: if there is a subsequent visit, delay its start time and call extend_visit
        if self.model.verbose:
            print(f"Operator {self.unique_id} is delaying travel {self.next_visit.unique_id} to patient {self.next_visit.patient_id} in municipality {self.next_mun()} by {extend_time} minutes; ETA: {u.print_time_in_minutes(self.eta)}")

        time_to_extend = np.max([0, self.eta - self.next_visit.real_start_time])

        if self.model.handle_delay:
            # check if visit can be shortened
            st = self.next_visit.shortening_time()
            shorten_time = np.min([st, time_to_extend])
            if shorten_time > 0:
                self.next_visit.shrink(shorten_time, start=True)
                time_to_extend -= shorten_time
            
        if time_to_extend > 0:
            # shrink and then extend
            self.extend_visit(self.next_visit, time_to_extend)
            self.next_visit.shrink(time_to_extend)


    def shorten_travel(self, shorten_time):
        self.eta -= shorten_time

        if self.next_visit is None:
            if self.model.verbose:
                print(f"Operator {self.unique_id} is returning home {shorten_time} minutes earlier; ETA: {u.print_time_in_minutes(self.eta)}")
            return
        
        time_to_shorten = shorten_time

        visit_delay = self.next_visit.get_delay()

        if visit_delay > 0:
            tts = np.min([time_to_shorten, visit_delay])
            self.shorten_visit(self.next_visit, tts)
            self.next_visit.stretch(tts)

            time_to_shorten -= tts

        if self.next_visit.real_start_time == self.next_visit.scheduled_start_time:
            self.next_visit.stretch(self.next_visit.shortened_time(), start=False)        

    # ------------ END SCHEDULE CHANGES ------------


    # ------------ BEHAVIOR UTILS ------------

    def next_mun(self):
        return self.model.get_patient(self.next_visit.patient_id).municipality


    def update_movement(self):
        if self.next_visit is None:
            self.etd = None
            self.eta = None
            if self.model.debug:
                print("No next visit for operator " + str(self.unique_id) + "; etd and eta set to None")
        else:
            self.etd = np.min([self.next_visit.real_start_time - self.current_edge['weight'], np.max([c.DEF_OP_START_TIME, self.start_time[self.model.current_day], self.model.current_time + 1, self.next_visit.real_start_time - c.MIN_NOTICE_TIME])])
            self.eta = self.current_edge['weight'] + self.etd
            if self.model.debug:
                print(f"Operator {self.unique_id} is travelling from municipality {self.current_municipality} to municipality {self.next_mun()} for visit {self.next_visit.unique_id} to patient {self.next_visit.patient_id} from {u.print_time_in_minutes(self.next_visit.real_start_time)} to {u.print_time_in_minutes(self.next_visit.real_end_time)}; etd: {u.print_time_in_minutes(self.etd)}; eta: {u.print_time_in_minutes(self.eta)}")


    def retrieve_next_visit(self, day):
        if self.model.debug:
            print(f"Operator {self.unique_id} is retrieving next visit on day {day}")

        schedule = self.retrieve_schedule(only_scheduled=True, day=day)

        if len(schedule) == 0:
            self.next_visit = None
            self.current_edge = None        
        else:
            self.next_visit = schedule[0]
            self.current_edge = self.model.graph[self.current_municipality][self.next_mun()]

        self.update_movement()

    # ------------ END BEHAVIOR UTILS ------------


    # ------------ UNEXPECTED EVENTS ------------

    def quit_day(self):
        if self.model.verbose:
            print(f"Operator {self.unique_id} is quitting the day")

        self.end_time[self.model.current_day] = self.model.current_time + self.model.graph[self.current_municipality][self.municipality]['weight'] + 1
        self.next_visit = None
        self.current_edge = None
        self.etd = None
        self.eta = None

        # all visits need to be rescheduled for the day
        visits_to_reschedule = self.retrieve_schedule(only_scheduled=True, day=self.model.current_day)
        for v in visits_to_reschedule:
            v.deschedule()


    def late_entry(self, day, time):
        if self.model.verbose:
            print(f"Operator {self.unique_id} is entering late on {u.print_day(day)} at {u.print_time_in_minutes(time)}")

        self.start_time[day] = time

        schedule = self.retrieve_schedule(only_scheduled=True, day=day)
        visits_to_reschedule = [v for v in schedule if v.real_start_time - self.model.graph[self.municipality][v.get_mun()]['weight'] < time]
        for v in visits_to_reschedule:
            v.deschedule()


    def early_exit(self, day, time):
        if self.model.verbose:
            print(f"Operator {self.unique_id} is exiting early on {u.print_day(day)} at {u.print_time_in_minutes(time)}")
            
        self.end_time[day] = time

        schedule = self.retrieve_schedule(only_scheduled=True, day=day)
        visits_to_reschedule = [v for v in schedule if v.real_end_time + self.model.graph[v.get_mun()][self.municipality]['weight'] > time]
        for v in visits_to_reschedule:
            v.deschedule()

    # ------------ END UNEXPECTED EVENTS ------------


    # ------------ BEHAVIOR ------------

    def start_day(self):
        # start from home municipality
        self.current_municipality = self.municipality
        self.is_reimbursed = False

        if self.availability[self.model.current_day] == 0:
            self.state = c.UNAVAILABLE
            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " is unavailable on " + u.print_day(self.model.current_day))
            return
        
        self.retrieve_next_visit(self.model.current_day)

        if self.next_visit is None:
            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " has no visits scheduled on " + u.print_day(self.model.current_day))
            return

        if self.model.verbose:
            print("Operator " + str(self.unique_id) + " ready to start " + u.print_day(self.model.current_day) + " with visit " + str(self.next_visit.unique_id) + " to patient " + str(self.next_visit.patient_id) + " in municipality " + str(self.next_mun()) + " from " + u.print_time_in_minutes(self.next_visit.real_start_time) + " to " + u.print_time_in_minutes(self.next_visit.real_end_time))
            print("ETD: " + u.print_time_in_minutes(self.etd) + "; ETA: " + u.print_time_in_minutes(self.eta))

        if self.start_time[self.model.current_day] > c.DEF_OP_START_TIME:
            self.state = c.UNAVAILABLE
            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " is unavailable until " + u.print_time_in_minutes(self.start_time[self.model.current_day]))

        else:
            self.state = c.IDLE


    # if operator is unavailable, check if they are now available
    def unavailable_step(self):
        if self.availability[self.model.current_day] == 1 and self.model.current_time >= self.start_time[self.model.current_day] and self.model.current_time <= self.end_time[self.model.current_day]:
            self.state = c.IDLE
            self.retrieve_next_visit(self.model.current_day)
            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " is now available")


    # if operator is idle, check if it is time to go to the next municipality
    def idle_step(self):
        # if it is time to go home, go home
        if self.next_visit is None and self.end_time[self.model.current_day] <= np.max([self.model.current_time + self.model.graph[self.current_municipality][self.municipality]['weight'], self.model.current_time + c.MIN_NOTICE_TIME]):
            self.state = c.TRAVELLING
            self.current_edge = self.model.graph[self.current_municipality][self.municipality]
            self.etd = self.model.current_time
            self.eta = self.model.graph[self.current_municipality][self.municipality]['weight'] + self.model.current_time

            if np.random.rand() * su.rush_hours_coefficient(self.model.current_time) < self.model.p_extended_travel:
                extend_time = su.sample_extend_time(self.model.extend_min, self.model.extend_mode, self.model.extend_max)
                self.extend_travel(extend_time)

            else:
                noise_time = su.sample_noise_time(self.model.noise_time)
                if noise_time > 0:
                    self.extend_travel(noise_time)
                elif noise_time < 0:
                    self.shorten_travel(-noise_time)

            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " is returning home to municipality " + str(self.municipality) + "; ETA: " + u.print_time_in_minutes(self.eta))
            
            return

        # if it is time to go to the next visit
        if self.model.current_time == self.etd:
            self.state = c.TRAVELLING

            if np.random.rand() < self.model.p_extended_travel:
                extend_time = su.sample_extend_time(self.model.extend_min, self.model.extend_mode, self.model.extend_max)
                self.extend_travel(extend_time)

            else:
                noise_time = su.sample_noise_time(self.model.noise_time)
                if noise_time > 0:
                    self.extend_travel(noise_time)
                elif noise_time < 0:
                    self.shorten_travel(-noise_time)

            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " is travelling to municipality " + str(self.next_mun()) + " to visit patient " + str(self.next_visit.patient_id) + "; ETA: " + u.print_time_in_minutes(self.eta))
            
            return

        # random events
        if self.model.current_time > c.DEF_OP_START_TIME and self.model.current_time < c.DEF_OP_END_TIME and self.model.current_day != 4:
            # quit day
            if np.random.rand() * su.day_adjustment(self.model.current_day) < self.model.p_quit_day:
                self.quit_day()
                return

            # late entry
            if np.random.rand() * su.day_adjustment(self.model.current_day) < self.model.p_late_entry and self.model.current_day < self.model.n_days - 1:
                day = np.random.randint(self.model.current_day + 1, self.model.n_days)
                time = (np.random.randint(c.DEF_OP_START_TIME, c.DEF_OP_END_TIME / 2) // c.TIME_UNIT) * c.TIME_UNIT

                if time > self.start_time[day]:
                    self.late_entry(day, time)
                return
            
            # early exit
            if np.random.rand() * su.day_adjustment(self.model.current_day) < self.model.p_early_exit and self.model.current_day < self.model.n_days - 1:
                day = np.random.randint(self.model.current_day + 1, self.model.n_days)
                time = (np.random.randint(c.DEF_OP_START_TIME + c.DEF_OP_END_TIME / 2, c.DEF_OP_END_TIME) // c.TIME_UNIT) * c.TIME_UNIT
                
                if time < self.end_time[day]:
                    self.early_exit(day, time)
                return


    # if operator is travelling, check if they have arrived
    def travelling_step(self):
        if self.model.current_time == self.eta:
            self.current_edge['n_travels'] += 1
            self.real_travel_time += self.eta - self.etd

            if self.current_edge['muns'][0] != self.current_edge['muns'][1]:
                self.real_inter_travel_time += self.eta - self.etd 

            # if next visit, ready to perform it
            if self.next_visit is not None:
                if self.is_reimbursed and self.current_edge['muns'][0] != self.current_edge['muns'][1]:
                    self.travel_to_reimburse += self.eta - self.etd
                
                self.is_reimbursed = True
                self.state = c.READY
                self.current_municipality = self.next_mun()
                
                if self.model.verbose:
                    print("Operator " + str(self.unique_id) + " has arrived to municipality " + str(self.current_municipality) + " to visit patient " + str(self.next_visit.patient_id) + "; visit estimated at: " + u.print_time_in_minutes(self.next_visit.real_start_time))
            
            # if no next visit, operator is back home
            else:
                self.is_reimbursed = False
                self.state = c.UNAVAILABLE
                self.current_municipality = self.municipality
                self.end_time[self.model.current_day] = self.model.current_time
                
                if self.model.verbose:
                    print("Operator " + str(self.unique_id) + " is back home and unavailable for the rest of " + u.print_day(self.model.current_day))


    # if operator is ready, check if it is time to start the visit
    def ready_step(self):
        if self.model.current_time == self.next_visit.real_start_time:
            self.state = c.WORKING
            self.next_visit.start(self.model.current_day, self.model.current_time, self.unique_id)

            if np.random.rand() < self.model.p_extended_visit:
                extend_time = su.sample_extend_time(self.model.extend_min, self.model.extend_mode, self.model.extend_max)
                self.extend_visit(self.next_visit, extend_time)

            else:
                noise_time = su.sample_noise_time(self.model.noise_time)
                if noise_time > 0:
                    self.extend_visit(self.next_visit, noise_time)
                elif noise_time < 0:
                    self.shorten_visit(self.next_visit, -noise_time)

            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " is visiting patient " + str(self.next_visit.patient_id) + " in municipality " + str(self.next_mun()) + " from " + u.print_time_in_minutes(self.next_visit.real_start_time) + " to " + u.print_time_in_minutes(self.next_visit.real_end_time))


    # if operator is working, check if they have completed their visit
    def working_step(self):
        if self.model.current_time == self.next_visit.real_end_time:
            if self.model.verbose:
                print("Operator " + str(self.unique_id) + " has completed visit " + str(self.next_visit.unique_id) + " to patient " + str(self.next_visit.patient_id) + " in municipality " + str(self.next_mun()) + " from " + u.print_time_in_minutes(self.next_visit.real_start_time) + " to " + u.print_time_in_minutes(self.next_visit.real_end_time))
            
            self.next_visit.complete(self.model.current_time)

            self.executed_visits += 1
            self.workload += self.next_visit.real_end_time - self.next_visit.real_start_time

            if self.next_visit.skill < self.skill:
                self.overskill_visits += 1
                self.overskill_time += self.next_visit.real_end_time - self.next_visit.real_start_time
            
            # after completion, retrieve next visit
            self.state = c.IDLE

            self.retrieve_next_visit(day=self.model.current_day)
            if self.model.verbose:
                if self.next_visit is not None:
                    print("Operator " + str(self.unique_id) + " is idle in municipality " + str(self.current_municipality) + " until " + u.print_time_in_minutes(self.etd))
                else:
                    print("Operator " + str(self.unique_id) + " is idle in municipality " + str(self.current_municipality) + " and has no more visits scheduled on " + u.print_day(self.model.current_day))

            self.idle_step()


    def step(self):
        if self.state == c.UNAVAILABLE:
            self.unavailable_step()

        if self.state == c.IDLE:
            self.idle_step()

        if self.state == c.TRAVELLING:
            self.travelling_step()

        if self.state == c.READY:
            self.ready_step()

        if self.state == c.WORKING:
            self.working_step()

    # ------------ END BEHAVIOR ------------



class Visit:
    def __init__(self,
        unique_id,
        model : 'HCModel',
        patient_id,
        skill,
        proposed_day,
        proposed_start_time,
        proposed_end_time,
        proposed_operator_id=None,
        state=c.NOT_SCHEDULED,
        newly_generated=False,
        original_day=None
    ):
        # untouchable data
        self.unique_id = unique_id
        self.model = model
        self.patient_id = patient_id
        self.skill = skill

        # proposed data
        self.proposed_day = proposed_day
        self.proposed_start_time = proposed_start_time
        self.proposed_end_time = proposed_end_time
        self.proposed_operator_id = proposed_operator_id
        
        self.state = state

        # scheduled data - equal to real data when scheduled
        if self.state != c.NOT_SCHEDULED:
            self.scheduled_day = proposed_day
            self.scheduled_start_time = proposed_start_time
            self.scheduled_end_time = proposed_end_time
            self.scheduled_operator_id = proposed_operator_id
            self.real_day = proposed_day
            self.real_start_time = proposed_start_time
            self.real_end_time = proposed_end_time
            self.real_operator_id = proposed_operator_id
        else:
            self.scheduled_day = None
            self.scheduled_start_time = None
            self.scheduled_end_time = None
            self.scheduled_operator_id = None
            self.real_day = None
            self.real_start_time = None
            self.real_end_time = None
            self.real_operator_id = None

        self.newly_generated = newly_generated
        self.scheduled_by_manager = False

        self.original_day = original_day if original_day is not None else proposed_day

    
    def __str__(self):
        ret_str = "Visit " + str(self.unique_id) + " (patient " + str(self.patient_id) + ", municipality " + str(self.get_mun()) + ", skill " + str(self.skill) + ") "

        if self.state == c.NOT_SCHEDULED:
            ret_str += "not scheduled; proposed day: " + u.print_day(self.proposed_day) + ", from " + u.print_time_in_minutes(self.proposed_start_time) + " to " + u.print_time_in_minutes(self.proposed_end_time)
            if self.proposed_operator_id is not None:
                ret_str += "; proposed operator: " + str(self.proposed_operator_id)
            else:
                ret_str += "; no proposed operator"

        else:
            if self.state == c.SCHEDULED:
                ret_str += "scheduled; estimated day: "

            elif self.state == c.EXECUTED:
                ret_str += "executed; actual day: "

            ret_str += u.print_day(self.real_day) + ", from " + u.print_time_in_minutes(self.real_start_time) + " to " + u.print_time_in_minutes(self.real_end_time) + "; operator: " + str(self.real_operator_id)

        return ret_str


    def __repr__(self):
        return self.__str__()


    def get_real_operator(self) -> Operator:
        return self.model.get_operator(self.real_operator_id)


    def get_patient(self) -> Patient:
        return self.model.get_patient(self.patient_id)


    def get_mun(self):
        return self.model.get_patient(self.patient_id).municipality


    def preferred_operators(self):
        return self.model.get_patient(self.patient_id).preferred_operators()

    
    def get_operator_skill(self):
        if self.real_operator_id is None:
            return None
        return self.model.get_operator(self.real_operator_id).skill


    def shortening_time(self):
        scheduled_duration = self.scheduled_end_time - self.scheduled_start_time
        real_duration = self.real_end_time - self.real_start_time

        return int(np.max([0, real_duration - scheduled_duration * (1 - c.SHORTENING_PERC)]))


    def shortened_time(self):
        return (self.scheduled_end_time - self.scheduled_start_time) - (self.real_end_time - self.real_start_time)

    
    def get_delay(self):
        return self.real_start_time - self.scheduled_start_time
    

    def schedule(self, day, start_time, end_time, op_id):
        self.scheduled_day = day
        self.scheduled_start_time = start_time
        self.scheduled_end_time = end_time
        self.scheduled_operator_id = op_id
        self.real_day = day
        self.real_start_time = start_time
        self.real_end_time = end_time
        self.real_operator_id = op_id

        self.state = c.SCHEDULED
        self.scheduled_by_manager = True

    
    def deschedule(self):
        self.scheduled_day = None
        self.scheduled_start_time = None
        self.scheduled_end_time = None
        self.scheduled_operator_id = None
        self.real_day = None
        self.real_start_time = None
        self.real_end_time = None
        self.real_operator_id = None

        self.state = c.NOT_SCHEDULED

    
    def start(self, day, start_time, op_id):
        self.real_day = day
        self.real_start_time = start_time
        self.real_operator_id = op_id

        self.state = c.EXECUTING


    def complete(self, end_time):
        self.real_end_time = end_time
        
        self.state = c.EXECUTED


    def stretch(self, stretch_time, start=True):
        if start:
            self.real_start_time -= stretch_time
        else:
            self.real_end_time += stretch_time


    def shrink(self, shrink_time, start=True):
        if start:
            self.real_start_time += shrink_time
        else:
            self.real_end_time -= shrink_time

    
    def postpone(self, pp_time):
        self.real_start_time += pp_time
        self.real_end_time += pp_time


    def anticipate(self, ant_time):
        self.real_start_time -= ant_time
        self.real_end_time -= ant_time



class Manager(Agent):
    def __init__(self, unique_id, model : 'HCModel', level=c.DUMMY):
        self.unique_id = unique_id
        self.model = model
        self.level = level


    def check_possible_visits(self, duration, day, municipality=None, skill=0):
        if municipality is None:
            n_municipalities = m.get_num_municipalities()

            all_possible_visits = np.zeros(n_municipalities)
            for op in self.model.operators:
                if op.skill >= skill:
                    all_possible_visits += op.possible_visits(duration, day)

            return all_possible_visits
        
        else:
            possible_visits = 0
            for op in self.model.operators:
                if op.skill >= skill:
                    possible_visits += op.possible_visits(duration, day, municipality=municipality)

            return possible_visits

    
    def check_all_possible_visits(self, day):
        all_possible_visits = []
        all_possible_durations = list(self.model.get_visit_duration_distribution().keys())
        
        for skill in [0,1]:
            skill_possible_visits = []
            for duration in all_possible_durations:
                possible_visits = self.check_possible_visits(duration, day, skill=skill)
                skill_possible_visits.append(possible_visits)

            all_possible_visits.append(skill_possible_visits)

        return all_possible_visits


    def compute_objective_delta(self, visit : Visit, operator : Operator, start_time, end_time):
        travel_cost_increment = operator.added_travel_costs(visit.proposed_day, start_time, visit.get_mun())
        wage_increment = operator.wage_increment(end_time - start_time)
        is_overskill = visit.skill < operator.skill

        return self.model.c_movement * travel_cost_increment + self.model.c_wage * wage_increment + self.model.c_overskill * is_overskill


    def compute_criticity(self, visit : Visit, operator : Operator, start_time, end_time, prev_possible_visits):
        obj_delta = self.compute_objective_delta(visit, operator, start_time, end_time)
        obj_factor = su.compute_objective_factor(obj_delta)

        if self.level == c.OPTIMIZER:
            return obj_factor

        if self.level == c.ROBUST:
            # schedule, evaluate, deschedule
            visit.schedule(visit.proposed_day, start_time, end_time, operator.unique_id)

            new_possible_visits = self.check_all_possible_visits(visit.proposed_day)
            
            robustness_factor = su.compute_robustness_factor(
                visit.get_operator_skill(),
                self.model.get_visit_duration_distribution(visit.skill),
                prev_possible_visits,
                new_possible_visits,
                self.model.get_patient_municipality_distribution(),
                self.model.n_municipalities
            )

            time_offset_factor = su.compute_time_offset_factor(visit)

            visit.deschedule()
            
            criticity = robustness_factor * time_offset_factor * obj_factor

            return criticity

    # ------------ SCHEDULING ------------

    def ping_operator(self, operator : Operator, visit : Visit):
        if operator.state == c.IDLE and visit.proposed_day == self.model.current_day:
            if self.model.debug:
                print(f"Pinging operator {operator.unique_id} for visit {visit.unique_id}")
            
            operator.retrieve_next_visit(visit.proposed_day)


    def try_schedule_with_operators(self, visit : Visit, operator_set : list[Operator], prev_possible_visits=None) -> tuple[float, int, Operator]:
        if self.level == c.RANDOM:
            # A: PROPOSED TIME
            if not (visit.proposed_day == self.model.current_day and visit.proposed_start_time <= self.model.current_time + c.MIN_NOTICE_TIME):
                available_ops = [op for op in operator_set if op.available_for_visit(visit)]
                if len(available_ops) != 0:
                    chosen_operator = np.random.choice(available_ops)
                    return None, visit.proposed_start_time, chosen_operator
                
            # B: RANDOM TIME
            visit_duration = visit.proposed_end_time - visit.proposed_start_time
            visit_municipality = visit.get_mun()

            possible_start_times = {}

            for op in operator_set:
                possible_start_times[op] = op.possible_times_to_start_visit(visit_duration, visit.proposed_day, visit_municipality)
                if visit.proposed_day == self.model.current_day:
                    possible_start_times[op] = [pst for pst in possible_start_times[op] if pst >= self.model.current_time + c.MIN_NOTICE_TIME]

            possible_start_times = {k: v for k, v in possible_start_times.items() if len(v) != 0}

            if len(possible_start_times) != 0:
                chosen_operator = np.random.choice(list(possible_start_times.keys()))
                chosen_start_time = np.random.choice(possible_start_times[chosen_operator])
                return None, chosen_start_time, chosen_operator

            return None, None, None

        if self.level in [c.OPTIMIZER, c.ROBUST]:
            best_criticity = None
            best_operator = None

            # A: PROPOSED TIME
            if not (visit.proposed_day == self.model.current_day and visit.proposed_start_time <= self.model.current_time + c.MIN_NOTICE_TIME):
                for op in operator_set:
                    if op.available_for_visit(visit):
                        criticity = self.compute_criticity(visit, op, visit.proposed_start_time, visit.proposed_end_time, prev_possible_visits)

                        if best_criticity is None or criticity < best_criticity:
                            if self.model.debug:
                                print(f"New best criticity: {criticity}, for original time {u.print_time_in_minutes(visit.proposed_start_time)} and operator {op.unique_id}")
                            best_criticity = criticity
                            best_operator = op

                if best_criticity is not None:
                    if self.model.debug:
                        print(f"Best criticity for visit {visit.unique_id}: {best_criticity}, for original time {u.print_time_in_minutes(visit.proposed_start_time)} and operator {best_operator.unique_id}")
                    return best_criticity, visit.proposed_start_time, best_operator
        
            # B: BEST TIME    
            best_start_time = None
            visit_duration = visit.proposed_end_time - visit.proposed_start_time
            visit_municipality = visit.get_mun()

            for op in operator_set:
                possible_start_times = op.possible_times_to_start_visit(visit_duration, visit.proposed_day, visit_municipality)

                if len(possible_start_times) != 0:
                    if visit.proposed_day == self.model.current_day:
                        possible_start_times = [pst for pst in possible_start_times if pst >= self.model.current_time + c.MIN_NOTICE_TIME]

                    for pst in possible_start_times:
                        criticity = self.compute_criticity(visit, op, pst, pst + visit_duration, prev_possible_visits)

                        if best_criticity is None or criticity < best_criticity:
                            if self.model.debug:
                                print(f"New best criticity: {criticity}, for time {u.print_time_in_minutes(pst)} and operator {op.unique_id}")
                            best_criticity = criticity
                            best_start_time = pst
                            best_operator = op

            if self.model.debug:
                if best_criticity is not None:
                    print(f"Best criticity for visit {visit.unique_id}: {best_criticity}, for time {u.print_time_in_minutes(best_start_time)} and operator {best_operator.unique_id}")
                else:
                    print(f"Couldn't schedule visit {visit.unique_id} with any operator")
            
            return best_criticity, best_start_time, best_operator
        

    def find_best_scheduling(self, visit : Visit):
        preferred_operators = visit.preferred_operators()
        prev_possible_visits = self.check_all_possible_visits(visit.proposed_day)

        # 1: PREFERRED OPERATORS
        for preferred_operator_id in preferred_operators:
            preferred_operator = self.model.get_operator(preferred_operator_id)

            best_criticity, best_start_time, best_operator = self.try_schedule_with_operators(visit, [preferred_operator], prev_possible_visits)
            if best_criticity is not None:
                return best_criticity, best_start_time, best_operator

        if self.model.debug:
            if len(preferred_operators) != 0:
                print(f"Couldn't schedule visit {visit.unique_id} with preferred operators")
            else:
                print(f"No preferred operators for visit {visit.unique_id}")

        # 2: OTHER OPERATORS
        other_operators = [o for o in self.model.operators if o.unique_id not in preferred_operators]

        best_criticity, best_start_time, best_operator = self.try_schedule_with_operators(visit, other_operators, prev_possible_visits)
        if best_criticity is not None:
            return best_criticity, best_start_time, best_operator
        else:
            if self.model.debug:
                print(f"Couldn't schedule visit {visit.unique_id} with any operator")

        # if self.level == c.ROBUST:
        #     not_ot_same_skill_operators, ot_same_skill_operators, not_ot_overskilled_operators, ot_overskilled_operators = su.divide_operators_by_fit(other_operators, visit.skill, visit_duration)

        #     # 2: OTHER SAME SKILL OPERATORS NOT IN OVERTIME
        #     best_criticity, best_start_time, best_operator = self.try_schedule_with_operators(visit, not_ot_same_skill_operators, prev_possible_visits)
        #     if best_criticity is not None:
        #         return best_criticity, best_start_time, best_operator
        #     else:
        #         if self.model.debug:
        #             print(f"Couldn't schedule visit {visit.unique_id} with other same skill operators not in overtime")

        #     # 3: OTHER SAME SKILL OPERATORS IN OVERTIME
        #     best_criticity, best_start_time, best_operator = self.try_schedule_with_operators(visit, ot_same_skill_operators, prev_possible_visits)
        #     if best_criticity is not None:        
        #         return best_criticity, best_start_time, best_operator
        #     else:
        #         if self.model.debug:
        #             print(f"Couldn't schedule visit {visit.unique_id} with other same skill operators in overtime")
            
        #     # 4: OTHER OVERSKILLED OPERATORS NOT IN OVERTIME
        #     best_criticity, best_start_time, best_operator = self.try_schedule_with_operators(visit, not_ot_overskilled_operators, prev_possible_visits)
        #     if best_criticity is not None:
        #         return best_criticity, best_start_time, best_operator
        #     else:
        #         if self.model.debug:
        #             print(f"Couldn't schedule visit {visit.unique_id} with other overskilled operators not in overtime")
            
        #     # 5: OTHER OVERSKILLED OPERATORS IN OVERTIME
        #     best_criticity, best_start_time, best_operator = self.try_schedule_with_operators(visit, ot_overskilled_operators, prev_possible_visits)
        #     if best_criticity is not None:
        #         return best_criticity, best_start_time, best_operator
        #     else:
        #         if self.model.debug:
        #             print(f"Couldn't schedule visit {visit.unique_id} with other overskilled operators in overtime")

        #     if self.model.debug:
        #         print(f"Couldn't schedule visit {visit.unique_id} with any operator")
        
        return None, None, None


    def schedule_single_visit(self, visit : Visit):
        if self.level == c.DUMMY:
            pref_ops_id = visit.preferred_operators()
            
            if len(pref_ops_id) != 0 and not (visit.proposed_day == self.model.current_day and visit.proposed_start_time <= self.model.current_time + c.MIN_NOTICE_TIME):
                for op_id in pref_ops_id:
                    op = self.model.get_operator(op_id)
                    if op.available_for_visit(visit):
                        visit.schedule(visit.proposed_day, visit.proposed_start_time, visit.proposed_end_time, op_id)
                        self.ping_operator(op, visit)

                        if self.model.verbose:
                            print(f"Scheduled visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} from {u.print_time_in_minutes(visit.real_start_time)} to {u.print_time_in_minutes(visit.real_end_time)} with operator {visit.real_operator_id}")
                        
                        return True

        elif self.level == c.RANDOM:
            pref_ops_id = visit.preferred_operators()
            other_ops = [o for o in self.model.operators if o.unique_id not in pref_ops_id]

            pref_ops = []
            for pref_op_id in pref_ops_id:
                pref_ops.append(self.model.get_operator(pref_op_id)) 

            _, time, operator = self.try_schedule_with_operators(visit, pref_ops)
            if operator:
                visit.schedule(visit.proposed_day, time, time + visit.proposed_end_time - visit.proposed_start_time, operator.unique_id)
                self.ping_operator(operator, visit)

                if self.model.verbose:
                    print(f"Scheduled visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} from {u.print_time_in_minutes(visit.real_start_time)} to {u.print_time_in_minutes(visit.real_end_time)} with operator {visit.real_operator_id}")
                
                return True
            
            _, time, operator = self.try_schedule_with_operators(visit, other_ops)
            if operator:
                visit.schedule(visit.proposed_day, time, time + visit.proposed_end_time - visit.proposed_start_time, operator.unique_id)
                self.ping_operator(operator, visit)

                if self.model.verbose:
                    print(f"Scheduled visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} from {u.print_time_in_minutes(visit.real_start_time)} to {u.print_time_in_minutes(visit.real_end_time)} with operator {visit.real_operator_id}")
                
                return True

        elif self.level in [c.OPTIMIZER, c.ROBUST]:
            best_criticity, best_start_time, best_operator = self.find_best_scheduling(visit)

            if best_criticity is not None:
                visit.schedule(visit.proposed_day, best_start_time, best_start_time + visit.proposed_end_time - visit.proposed_start_time, best_operator.unique_id)
                self.ping_operator(best_operator, visit)
                
                if self.model.verbose:
                    print(f"Scheduled visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} from {u.print_time_in_minutes(visit.real_start_time)} to {u.print_time_in_minutes(visit.real_end_time)} with operator {visit.real_operator_id}")
                
                return True

        if self.level in [c.DUMMY, c.RANDOM]:
            self.model.not_schedulable_visit(visit)
            if self.model.verbose:
                print(f"Couldn't schedule visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} at any time")

        return False


    # level 3 functions

    def schedule_single_visit_multiple_days(self, visit : Visit):
        if self.model.verbose:
            print(f"Trying to schedule visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} on {u.print_day(visit.proposed_day)}")
        if not self.schedule_single_visit(visit):
            visit.original_day = visit.proposed_day
            # eligible days: past current one, not original one, patient must not have visits in that day
            eligible_days = [d for d in range(self.model.current_day + 1, self.model.n_days) if d != visit.original_day and not visit.get_patient().has_visit(d)]

            for day in eligible_days:
                visit.proposed_day = day
                if self.model.verbose:
                    print(f"Trying to schedule visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} on {u.print_day(visit.proposed_day)}")
                if self.schedule_single_visit(visit):
                    return True

            visit.proposed_day = visit.original_day
            visit.original_day = None

            if self.model.verbose:
                print(f"Couldn't schedule visit {visit.unique_id} to patient {visit.patient_id} in municipality {visit.get_mun()} on any day")
            
            self.model.not_schedulable_visit(visit)

            return False

        return True


    def try_multiple_schedules(self, visits : list[Visit], operators : list[Operator], prev_visits):
        best_avg_crit = None
        best_start_times = None
        best_operator = None

        for op in operators:
            if self.model.debug:
                print(f"Trying to schedule visits with operator {op.unique_id}")
            crits = []
            start_times = []
            
            for i in range(len(visits)):
                crit, start_time, _ = self.try_schedule_with_operators(visits[i], [op], prev_visits[i])
                crits.append(crit)
                start_times.append(start_time)
            
            if None in crits:
                continue

            avg_crit = np.mean(crits)
            if self.model.debug:
                print(f"Average criticity of all schedulings: {avg_crit}")
            if best_avg_crit is None or avg_crit < best_avg_crit:
                    if self.model.debug:
                        print(f"New best average criticity: {avg_crit} for operator {op.unique_id}")
                    best_avg_crit = avg_crit
                    best_start_times = start_times
                    best_operator = op

        return best_avg_crit, best_start_times, best_operator


    def find_best_multiple_schedulings(self, visits : list[Visit]):
        # visits are all from the same patient without any preferred operator, and are more than one

        prev_visits = [self.check_all_possible_visits(v.proposed_day) for v in visits]

        n_availabilities = {}

        for o in self.model.operators:
            tot_avail = 0
            for v in visits:
                tot_avail += o.available_for_visit(v)
            
            if tot_avail not in n_availabilities:
                n_availabilities[tot_avail] = [o]
            else:
                n_availabilities[tot_avail].append(o)

        n_availabilities = {k: v for k, v in sorted(n_availabilities.items(), key=lambda item: item[0], reverse=True)}
        for key in list(n_availabilities.keys()):
            available_operators = n_availabilities[key]

            best_avg_crit, best_start_times, best_operator = self.try_multiple_schedules(visits, available_operators, prev_visits)
            if best_avg_crit is not None:
                return best_avg_crit, best_start_times, best_operator
        
        # arriving here means no operator can perform the visits
        if self.model.debug:
            print(f"Couldn't schedule visits with any operator")
        
        return None, None, None


    def schedule_multiple_visits(self, visits : list[Visit]):
        if self.model.verbose:
            print(f"Trying to schedule visits {[v.unique_id for v in visits]}")

        best_criticity, best_start_times, best_operator = self.find_best_multiple_schedulings(visits)

        if best_criticity is not None:
            for i in range(len(visits)):
                visits[i].schedule(visits[i].proposed_day, best_start_times[i], best_start_times[i] + visits[i].proposed_end_time - visits[i].proposed_start_time, best_operator.unique_id)
                if best_operator.state == c.IDLE and visits[i].proposed_day == self.model.current_day:
                    best_operator.retrieve_next_visit(visits[i].proposed_day)
                if self.model.verbose:
                    print(f"Scheduled visit {visits[i].unique_id} to patient {visits[i].patient_id} in municipality {visits[i].get_mun()} from {u.print_time_in_minutes(visits[i].real_start_time)} to {u.print_time_in_minutes(visits[i].real_end_time)} with operator {visits[i].real_operator_id}")

            return True
        
        if self.model.verbose:
            print(f"Couldn't schedule visits {[v.unique_id for v in visits]} with any operator. Scheduling them singularly")

        for v in visits:
            self.schedule_single_visit_multiple_days(v)

        return False


    def schedule_all_unscheduled_visits(self):
        not_scheduled_visits = [visit for visit in self.model.visits if visit.state == c.NOT_SCHEDULED]

        if self.level in [c.DUMMY, c.RANDOM]:
            for v in not_scheduled_visits:
                self.schedule_single_visit(v)
        
        if self.level in [c.OPTIMIZER, c.ROBUST]:
            # group by patient
            not_scheduled_visits = sorted(not_scheduled_visits, key=lambda visit: visit.patient_id)
            not_scheduled_visits = [list(group) for _, group in groupby(not_scheduled_visits, lambda visit: visit.patient_id)]

            for patient_visits in not_scheduled_visits:
                if len(patient_visits) == 1:
                    self.schedule_single_visit_multiple_days(patient_visits[0])
                else:
                    self.schedule_multiple_visits(patient_visits)


    def reschedule_visits(self, visits : list[Visit]):
        for v in visits:
            v.deschedule()
            self.schedule_single_visit_multiple_days(v)

    # ------------ END SCHEDULING ------------

    def start_week(self):
        self.schedule_all_unscheduled_visits()


    def step(self):
        self.schedule_all_unscheduled_visits()



class HCModel(Model):
    
    # ------------ MODEL INITIALIZATION ------------
    
    def __init__(self,
            verbose=False,
            debug=False,
            noise_time=c.NOISE_TIME,
            extend_min=c.PROLONG_MIN,
            extend_mode=c.PROLONG_MODE,
            extend_max=c.PROLONG_MAX,
            new_visit_frequency=c.NEW_VISIT_FREQUENCY,
            single_cancellation_frequency=c.SINGLE_CANCELLATION_FREQUENCY,
            all_cancellations_frequency=c.ALL_CANCELLATIONS_FREQUENCY,
            new_patient_frequency=c.NEW_PATIENT_FREQUENCY,
            quit_day_frequency=c.QUIT_DAY_FREQUENCY,
            late_entry_frequency=c.LATE_ENTRY_FREQUENCY,
            early_exit_frequency=c.EARLY_EXIT_FREQUENCY,
            extended_visit_probability=c.PROLONGED_VISIT_PROBABILITY,
            extended_travel_probability=c.PROLONGED_TRAVEL_PROBABILITY,
            is_manager_working=True,
            manager_level=c.ROBUST,
            handle_delay=True,
            high_skill_prob=c.HIGH_SKILL_PROB
        ):
        self.verbose = verbose
        self.debug = debug
        self.running = True
        self.is_broken = False

        self.next_patient_id = 0
        self.next_operator_id = 0
        self.next_visit_id = 0

        # random activation class: activates the agents one by one
        self.schedule = RandomActivation(self)

        self.n_days = m.get_num_days()
        self.n_municipalities = m.get_num_municipalities()

        self.current_day = 0
        self.current_time = -1

        self.c_wage, self.c_movement, self.c_overskill, self.c_execution, self.sigma0, self.sigma1, self.omega = self._initialize_hyperparameters()

        self.graph = self._initialize_municipalities()
        self.patients = self._initialize_patients()
        self.operators = self._initialize_operators()
        self.visits = self._initialize_visits()

        for pat in self.patients:
            pat._initialize_premium()

        self.manager = self._initialize_manager(manager_level)

        self.removed_visits = []
        self.not_schedulable_visits = []
        
        self.noise_time = noise_time
        self.extend_min = extend_min
        self.extend_mode = extend_mode
        self.extend_max = extend_max

        self.high_skill_prob = high_skill_prob

        # probabilities of unexpected events
        self.p_new_visit = new_visit_frequency / (c.DEF_PAT_DAY_DURATION * len(self.patients))
        self.p_single_canc = single_cancellation_frequency / (c.DEF_PAT_DAY_DURATION * len(self.patients))
        self.p_all_canc = all_cancellations_frequency / (c.DEF_PAT_DAY_DURATION * len(self.patients))
        self.p_new_patient = new_patient_frequency / c.DEF_PAT_DAY_DURATION
        self.p_quit_day = quit_day_frequency / c.DEF_OP_END_TIME
        self.p_late_entry = late_entry_frequency / c.DEF_OP_END_TIME
        self.p_early_exit = early_exit_frequency / c.DEF_OP_END_TIME
        self.p_extended_visit = extended_visit_probability
        self.p_extended_travel = extended_travel_probability

        self.is_manager_working = is_manager_working
        self.handle_delay = handle_delay
        self.overly_delayed_visits = 0

        self.datacollector = DataCollector(
            agent_reporters={
                "skill": lambda a: a.skill if isinstance(a, Operator) else None,
                "time": lambda a: a.time if isinstance(a, Operator) else None,
                "n_ass_pat": lambda a: a.n_assigned_patients() if isinstance(a, Operator) else None,
                "exec_visits": lambda a: a.executed_visits if isinstance(a, Operator) else None,
                "not_exec_visits": lambda a: a.n_not_executed_visits() if isinstance(a, Operator) else None,
                "workload": lambda a: a.workload if isinstance(a, Operator) else None,
                "overtime": lambda a: np.max([0, a.workload - a.time]) if isinstance(a, Operator) else None, 
                "travel_time": lambda a: a.real_travel_time if isinstance(a, Operator) else None,
                "inter_travel_time": lambda a: a.real_inter_travel_time if isinstance(a, Operator) else None,
                "overskill_v": lambda a: a.overskill_visits if isinstance(a, Operator) else None,
                "overskill_t": lambda a: a.overskill_time if isinstance(a, Operator) else None
            }
        )
        
        if self.verbose:
            print("Model loaded.\n")


    def _initialize_hyperparameters(self):
        # retrieve from model parameters
        hp = u.retrieve_JSON(c.HYPERPARAMS_JSON)

        # return C_WAGE, C_MOVEMENT, C_OVERSKILL, C_EXECUTION, SIGMA0, SIGMA1, OMEGA
        return hp[c.C_WAGE], hp[c.C_MOVEMENT], hp[c.C_OVERSKILL], hp[c.C_EXECUTION], hp[c.SIGMA0], hp[c.SIGMA1], hp[c.OMEGA] 


    def _initialize_municipalities(self) -> nx.Graph:
        # MUNICIPALITIES
        if self.verbose:
            print("Loading municipalities...")

        graph = nx.Graph()
        mun_distances = m.get_commuting_times()
        mun_latitudes = m.get_municipality_param(c.MUN_LATITUDE)
        mun_longitudes = m.get_municipality_param(c.MUN_LONGITUDE)
        
        for mun in range(self.n_municipalities):
            graph.add_node(mun, pos=(mun_latitudes[mun], mun_longitudes[mun]))
        
        for i in range(self.n_municipalities):
            for j in range(self.n_municipalities):
                if i <= j:
                    graph.add_edge(
                        i,
                        j,
                        weight=mun_distances[i][j],
                        n_travels=0,
                        muns = [i,j]
                    )
        
        if self.verbose:
            print("Municipalities loaded.\n")

        return graph


    def _initialize_patients(self) -> list[Patient]:
        # PATIENTS
        if self.verbose:
            print("Loading patients...")

        n_patients = m.get_num_patients()
        patient_municipalities = m.get_patient_param(c.PAT_MUNICIPALITY)
        assignments = [a.index(1) for a in m.get_assignment()]

        patients = []

        for i in range(n_patients):
            patient = Patient(c.PAT_BASE_ID + i, self, municipality=patient_municipalities[i]-1, assigned_operator_id=c.OP_BASE_ID + assignments[i])
            patients.append(patient)
            self.schedule.add(patient)

        self.next_patient_id = n_patients

        if self.verbose:
            print("Patients loaded.\n")
        
        return patients

    
    def _initialize_operators(self) -> list[Operator]:
        # OPERATORS
        if self.verbose:
            print("Loading operators...")

        operators = []
        
        n_operators = m.get_num_operators()
        
        op_municipalities = m.get_operator_param(c.OP_MUNICIPALITY)
        op_skills = m.get_operator_param(c.OP_SKILL)
        op_times = m.get_operator_param(c.OP_TIME)
        op_max_times = m.get_operator_param(c.OP_MAX_TIME)

        op_availabilities = m.get_operator_daily_param(c.OP_AVAILABILITY)
        op_start_times = m.get_operator_daily_param(c.OP_START_TIME)
        op_end_times = m.get_operator_daily_param(c.OP_END_TIME)

        for i in range(n_operators):
            op_id = c.OP_BASE_ID + i

            operator = Operator(
                op_id,
                self,
                municipality=op_municipalities[i]-1,
                skill=op_skills[i],
                time=op_times[i],
                max_time=op_max_times[i],
                availability=op_availabilities[i],
                start_time=op_start_times[i],
                end_time=op_end_times[i]
            )

            self.schedule.add(operator)
            operators.append(operator)

        self.next_operator_id = n_operators
        
        if self.verbose:
            print("Operators loaded.\n")

        return operators


    def _initialize_visits(self) -> list[Visit]:
        if self.verbose:
            print("Loading visits...")

        n_operators = m.get_num_operators()
        op_schedules = s.operator_schedule()
        tot_not_executed_visits = s.operator_not_executed_schedule()
        
        visits = []
        
        for i in range(n_operators):
            op_id = c.OP_BASE_ID + i
            op_schedule = op_schedules[i]
            
            patients_to_be_visited = []
            for sch_visit in op_schedule:
                # retrieve instance of patient with id sch_visit[0]
                pat_id = int(sch_visit[c.SCH_PATIENT]) + c.PAT_BASE_ID
                if pat_id not in patients_to_be_visited:
                    patients_to_be_visited.append(pat_id)
                
                visit_day = sch_visit[c.SCH_DAY]
                visit_skill = sch_visit[c.SCH_SKILL]
                visit_start_time = sch_visit[c.SCH_START_TIME]
                visit_end_time = sch_visit[c.SCH_END_TIME]

                visit = Visit(
                    unique_id=c.VISIT_BASE_ID + len(visits),
                    model=self,
                    patient_id=pat_id,
                    skill=visit_skill,
                    proposed_day=visit_day,
                    proposed_start_time=visit_start_time,
                    proposed_end_time=visit_end_time,
                    proposed_operator_id=op_id,
                    state=c.SCHEDULED
                )

                visits.append(visit)

            op_not_executed_visits = tot_not_executed_visits[i]
            for not_exec_visit in op_not_executed_visits:
                pat_id = int(not_exec_visit[c.SCH_PATIENT]) + c.PAT_BASE_ID
                
                proposed_day = not_exec_visit[c.SCH_DAY]
                skill = not_exec_visit[c.SCH_SKILL]
                proposed_start_time = not_exec_visit[c.SCH_START_TIME]
                proposed_end_time = not_exec_visit[c.SCH_END_TIME]

                if pat_id not in patients_to_be_visited:
                    visit = Visit(
                        unique_id=c.VISIT_BASE_ID + len(visits),
                        model=self,
                        patient_id=pat_id,
                        skill=skill,
                        proposed_day=proposed_day,
                        proposed_start_time=proposed_start_time,
                        proposed_end_time=proposed_end_time,
                    )

                else:
                    visit = Visit(
                        unique_id=c.VISIT_BASE_ID + len(visits),
                        model=self,
                        patient_id=pat_id,
                        skill=skill,
                        proposed_day=proposed_day,
                        proposed_start_time=proposed_start_time,
                        proposed_end_time=proposed_end_time,
                        proposed_operator_id=op_id
                    )

                visits.append(visit)
        
        self.next_visit_id = len(visits)

        if self.verbose:
            print("Visits loaded.\n")
        
        return visits


    def _initialize_manager(self, level) -> Manager:
        if self.verbose:
            print("Loading manager...")

        manager = Manager(c.MANAGER_ID, self, level)

        if self.verbose:
            print("Manager loaded.\n")
        
        return manager

    # ------------ END MODEL INITIALIZATION ------------


    # ------------ RETRIEVAL ------------

    def get_agent(self, agent_id):
        for agent in self.schedule.agents:
            if agent.unique_id == agent_id:
                return agent
        
        return None
    

    def get_patient(self, patient_id) -> Patient:
        if patient_id >= c.PAT_BASE_ID:
            return self.get_agent(patient_id)
        return self.get_agent(patient_id + c.PAT_BASE_ID)


    def get_operator(self, operator_id) -> Operator:
        if operator_id >= c.OP_BASE_ID:
            return self.get_agent(operator_id)
        return self.get_agent(operator_id + c.OP_BASE_ID)


    def get_visit(self, visit_id) -> Visit:
        if visit_id < c.VISIT_BASE_ID:
            visit_id += c.VISIT_BASE_ID

        for visit in self.visits:
            if visit.unique_id == visit_id:
                return visit
        
        return None


    def get_visit_duration_distribution(self, skill=0):
        durations = {}
        for visit in self.visits:
            if visit.skill == skill:
                duration = visit.proposed_end_time - visit.proposed_start_time
                if duration not in durations:
                    durations[duration] = 1
                else:
                    durations[duration] += 1

        # sort by key
        durations = dict(sorted(durations.items()))

        # normalize values
        tot_visits = sum(durations.values())
        for duration in durations:
            durations[duration] /= tot_visits

        return durations


    def get_patient_municipality_distribution(self):
        municipalities = np.zeros(self.n_municipalities)
        for patient in self.patients:
            municipalities[patient.municipality] += 1

        # normalize values
        tot_patients = sum(municipalities)
        for mun in range(self.n_municipalities):
            municipalities[mun] /= tot_patients

        return municipalities


    def get_patient_premium_distribution(self):
        premium = 0
        for patient in self.patients:
            premium += patient.premium

        perc = premium / len(self.patients)
        return [1-perc, perc]

    # ------------ END RETRIEVAL ------------


    # ------------ ADD ------------

    def add_patient(self, municipality, premium=False, newly_generated=True) -> Patient:
        patient = Patient(c.PAT_BASE_ID + self.next_patient_id, self, municipality=municipality, premium=premium, newly_generated=newly_generated)
        
        self.next_patient_id += 1

        self.schedule.add(patient)
        self.patients.append(patient)

        if self.verbose:
            print("Patient " + str(patient.unique_id) + " added to municipality " + str(municipality))

        return patient

    
    def add_operator(self, municipality, skill, time, max_time, availability, start_time, end_time) -> Operator:
        operator = Operator(
            c.OP_BASE_ID + self.next_operator_id,
            self,
            municipality=municipality,
            skill=skill,
            time=time,
            max_time=max_time,
            availability=availability,
            start_time=start_time,
            end_time=end_time
        )

        self.next_operator_id += 1

        self.schedule.add(operator)
        self.operators.append(operator)
        
        if self.verbose:
            print("Operator " + str(operator.unique_id) + " added to municipality " + str(municipality) + " with skill " + str(skill) + ", time " + str(time) + ", max time " + str(max_time) + ", availability " + str(availability) + ", start time " + str(start_time) + ", end time " + str(end_time))

        return operator


    def add_visit(self, patient_id, day, skill, start_time, end_time, operator_id=None, state=c.NOT_SCHEDULED, newly_generated=True) -> Visit:
        visit = Visit(
            unique_id=c.VISIT_BASE_ID + self.next_visit_id,
            model=self,
            patient_id=patient_id,
            skill=skill,
            proposed_day=day,
            proposed_start_time=start_time,
            proposed_end_time=end_time,
            proposed_operator_id=operator_id,
            state=state,
            newly_generated=newly_generated
        )

        self.next_visit_id += 1

        self.visits.append(visit)

        if self.verbose:
            print_row = "Proposed visit " + str(visit.unique_id) + " added to patient " + str(patient_id) + " on " + u.print_day(day) + ", from " + u.print_time_in_minutes(start_time) + " to " + u.print_time_in_minutes(end_time) + ";"
            if operator_id is not None:
                print_row += " proposed operator: " + str(operator_id)
            else:
                print_row += " no proposed operator"
            print(print_row)

        return visit             


    def remove_visit(self, visit : Visit):
        if self.verbose:
            print("Removing visit " + str(visit.unique_id) + " from patient " + str(visit.patient_id) + " on " + u.print_day(visit.real_day) + ", from " + u.print_time_in_minutes(visit.real_start_time) + " to " + u.print_time_in_minutes(visit.real_end_time) + "; operator: " + str(visit.real_operator_id))
        
        operator = visit.get_real_operator()
        day = visit.real_day

        # remove visit from self.visits and move to self.removed_visits
        self.visits.remove(visit)
        self.removed_visits.append(visit)

        # retrieve next visit for operator
        if day == self.current_day and (operator.state == c.IDLE or operator.state == c.UNAVAILABLE):
            operator.retrieve_next_visit(day)


    def not_schedulable_visit(self, visit : Visit):
        self.visits.remove(visit)
        self.not_schedulable_visits.append(visit)

    # ------------ END ADD ------------


    # ------------ UNEXPECTED EVENTS ------------

    def generate_new_patient(self) -> Patient:
        if self.verbose:
            print("Generating new patient...")
        
        municipality = np.random.choice(self.n_municipalities, p=self.get_patient_municipality_distribution())
        premium = np.random.choice([False, True], p=self.get_patient_premium_distribution())
        
        return self.add_patient(municipality, premium=premium, newly_generated=True)


    def model_unexpected_events(self):
        # new patient
        if self.current_time > c.DEF_PAT_START_TIME and self.current_time < c.DEF_PAT_END_TIME and np.random.uniform() < self.p_new_patient:
            new_patient = self.generate_new_patient()
            new_patient.generate_new_visit()

    # ------------ END UNEXPECTED EVENTS ------------


    # ------------ BEHAVIOR ------------

    def start_day(self):
        if self.verbose:
            print("Starting " + u.print_day(self.current_day))

        for op in self.operators:
            op.start_day()


    def step(self):
        if self.running:
            # if first step
            if self.schedule.steps == 0:
                if self.verbose:
                    print("Starting simulation")
                if self.is_manager_working:
                    self.manager.start_week()

            if self.current_time == -1:
                self.start_day()

            self.current_time += 1
            if self.verbose:
                print(f"{u.print_day(self.current_day)}, {u.print_time_in_minutes(self.current_time)}")

            self.model_unexpected_events()

            self.schedule.step()

            if self.is_manager_working:
                self.manager.step()

            if self.current_time == c.DEF_OP_END_TIME:
                states = self.retrieve_operator_states()
                for s in states:
                    if s[1] != c.UNAVAILABLE:
                        if self.verbose:
                            print(f"Operator {s[0]} is {c.OP_STATES[s[1]]}")

            if self.current_time >= c.DEF_OP_END_TIME and self.all_unavailable_operators():
                if self.verbose:
                    print(f"{u.print_day(self.current_day)} is over\n")

                if self.current_day == self.n_days - 1:
                    if self.verbose:
                        print("Simulation is over")

                    self.datacollector.collect(self)
                    self.running = False
                else:    
                    self.current_time = -1
                    self.current_day += 1

            # if the time is over 24:00, the simulation is broken
            if self.current_time >= c.BROKEN_TIME:
                self.running = False
                self.is_broken = True
                if self.verbose:
                    print("Model has broken")
    
    # ------------ END BEHAVIOR ------------


    # ------------ STATS ------------
        
    def retrieve_operator_states(self):
        states = []
        for op in self.operators:
            states.append((op.unique_id, op.state))
        
        return states


    def all_unavailable_operators(self):
        for op in self.operators:
            if op.state != c.UNAVAILABLE:
                return False
        
        return True


    def num_newly_generated_visits(self):
        return len([v for v in self.visits if v.newly_generated])
    
    
    def compute_objective(self):
        # 1: wage component
        wage = 0
        for op in self.operators:
            wage += op.compute_total_wage()

        # 2: movement component
        im_movement = 0
        for op in self.operators:
            im_movement += op.travel_to_reimburse * self.c_movement

        # 3: overskill component
        overskill = 0
        for op in self.operators:
            overskill += op.overskill_visits * self.c_overskill

        # 4: execution component
        not_executed = 0
        for op in self.operators:
            not_executed += op.n_not_executed_visits() * self.c_execution

        if self.verbose:
            print(f"Wage component: {wage}")
            print(f"Movement component: {im_movement}")
            print(f"Overskill component: {overskill}")
            print(f"Not executed component: {not_executed}")

        return wage + im_movement + overskill + not_executed


    def average_visit_delay(self):
        executed_visits = [v for v in self.visits if v.state == c.EXECUTED]
        tot_delay = 0

        for v in executed_visits:
            # if v.state == c.EXECUTED and not v.scheduled_by_manager:
            if v.state == c.EXECUTED:
                tot_delay += v.real_start_time - v.scheduled_start_time

        return round(tot_delay / len(executed_visits), 2)


    def not_executed_visits(self):
        return [v for v in self.visits if v.state == c.NOT_SCHEDULED]


    def visits_delayed_by(self, time):
        return [v for v in self.visits if v.state == c.EXECUTED and v.real_start_time - v.scheduled_start_time > time]


    def num_op_per_patient(self):
        n_ops = [0]*6
        
        for p in self.patients:
            if not p.is_removed:
                own_visits = p.own_visits()
                # count number of scheduled operators
                ops = len(set([v.real_operator_id for v in own_visits if v.state == c.EXECUTED]))
                n_ops[ops] += 1

        return n_ops        


    def average_time_offset(self):
        tot = []
        for v in self.visits:
            if v.state in [c.EXECUTED, c.SCHEDULED] and v.scheduled_by_manager == True:
                tot.append(np.abs(v.scheduled_start_time - v.proposed_start_time))

        return round(np.mean(tot), 2) if len(tot) > 0 else 0
        

    def not_schedulable_days(self):
        days = [0]*self.n_days

        for v in self.not_schedulable_visits:
            days[v.proposed_day] += 1

        return days

    # ------------ END STATS ------------


    # ------------ PLOTS AND PRINTS ------------

    def plot_municipalities(self):
        plt.figure(figsize=(15, 10))

        pos = nx.get_node_attributes(self.graph, "pos")
        nx.draw(self.graph, pos, with_labels=True)
        
        edge_labels = nx.get_edge_attributes(self.graph, 'weight')
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)
        
        plt.title("Municipalities")
        plt.show()


    def print_patients(self):
        print("Patients:")
        for pat in self.patients:
            print(pat)
        print()

    
    def print_operators(self):
        print("Operators:")
        for op in self.operators:
            print(op)
        print()


    def print_visits(self):
        print("Visits:")
        for visit in self.visits:
            print(visit)
        print()

    # ------------ END PLOTS AND PRINTS ------------


    # ------------ SWAP ------------

    def perform_swap(self, pat1_id, pat2_id):
        if self.verbose:
            print(f"Performing swap between patient {pat1_id} and patient {pat2_id}")

        pat1 = self.get_patient(pat1_id)
        pat2 = self.get_patient(pat2_id)

        op1_id = pat1.assigned_operator_id
        op2_id = pat2.assigned_operator_id

        if op1_id == op2_id:
            return False

        op1 = self.get_operator(op1_id)
        op2 = self.get_operator(op2_id)

        if self.verbose:
            print(f"Assigned operators: {op1_id}, {op2_id}")

        pat1.assigned_operator_id = op2_id
        pat2.assigned_operator_id = op1_id

        # retrieve all visits of pat1 and pat2
        pat1_visits = [v for v in self.visits if v.patient_id == pat1_id]
        pat2_visits = [v for v in self.visits if v.patient_id == pat2_id]

        # for each visit, remove it and try to reschedule with the other operator
        for v in pat1_visits:
            v.deschedule()
            v.proposed_operator_id = op2_id

        for v in pat2_visits:
            v.deschedule()
            v.proposed_operator_id = op1_id

        for v in pat1_visits:            
            if op2.available_for_visit(v):
                v.schedule(v.proposed_day, v.proposed_start_time, v.proposed_end_time, v.proposed_operator_id)
                
        for v in pat2_visits:
            if op1.available_for_visit(v):
                v.schedule(v.proposed_day, v.proposed_start_time, v.proposed_end_time, v.proposed_operator_id)

        # retrieve patients with no assigned operator
        no_op_patients = [p for p in self.patients if p.assigned_operator_id is None]

        # for each patient, try to assign either op1 or op2
        for p in no_op_patients:
            availabilities = [0,0]
            for v in p.own_visits():
                if op1.available_for_visit(v):
                    availabilities[0] += 1
                if op2.available_for_visit(v):
                    availabilities[1] += 1

            if availabilities[0] > availabilities[1]:
                p.assigned_operator_id = op1_id
                for v in p.own_visits():
                    v.proposed_operator_id = p.assigned_operator_id
                    v.schedule(v.proposed_day, v.proposed_start_time, v.proposed_end_time, v.proposed_operator_id)

            elif availabilities[1] > availabilities[0]:
                p.assigned_operator_id = op2_id
                for v in p.own_visits():
                    v.proposed_operator_id = p.assigned_operator_id
                    v.schedule(v.proposed_day, v.proposed_start_time, v.proposed_end_time, v.proposed_operator_id)

            else:
                if availabilities[0] != 0:
                    p.assigned_operator_id = op1_id
                    for v in p.own_visits():
                        v.proposed_operator_id = p.assigned_operator_id
                        v.schedule(v.proposed_day, v.proposed_start_time, v.proposed_end_time, v.proposed_operator_id)

        # if patients assigned to either op1 or op2 with some unscheduled visits, try to schedule them
        for p in self.patients:
            if p.assigned_operator_id == op1_id:
                for v in p.own_visits():
                    if v.state == c.NOT_SCHEDULED:
                        v.proposed_operator_id = p.assigned_operator_id
                        if op1.available_for_visit(v):
                            v.schedule(v.proposed_day, v.proposed_start_time, v.proposed_end_time, v.proposed_operator_id)

            elif p.assigned_operator_id == op2_id:
                for v in p.own_visits():
                    if v.state == c.NOT_SCHEDULED:
                        v.proposed_operator_id = p.assigned_operator_id
                        if op2.available_for_visit(v):
                            v.schedule(v.proposed_day, v.proposed_start_time, v.proposed_end_time, v.proposed_operator_id)
        
        return True
