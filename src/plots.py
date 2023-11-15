import src.constants as c
import src.utilities as u

import src.manipulation as m
import src.stats as s

import matplotlib.pyplot as plt


# --------------- PLOTS --------------- #

def pat_op_space():
    mun_data = u.retrieve_JSON(c.MUNICIPALITY_JSON)
    mun_lat = mun_data[c.MUN_LATITUDE]
    mun_lon = mun_data[c.MUN_LONGITUDE]

    # get number of operators and patients living in each municipality
    mun_operators = s.municipality_operators(verbose=False)
    mun_patients = s.municipality_patients(verbose=False)

    print(mun_operators)

    print(mun_patients)

    # plot
    plt.figure(figsize=(10, 10))
    plt.title("Operators and patients per municipality")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # plot the number of operators and the number of patients using plt.text inside a for loop
    for lat, lon, pat in zip(mun_lat, mun_lon, mun_patients):
        plt.scatter(lon, lat, s=0)
        plt.text(lon, lat, pat, fontsize=20, horizontalalignment='left', verticalalignment='center', color='red')

    for lat, lon, op in zip(mun_lat, mun_lon, mun_operators):
        plt.scatter(lon, lat, s=0)
        plt.text(lon, lat, op, fontsize=20, horizontalalignment='right', verticalalignment='center', color='blue')

    # add a legend
    # plt.legend(["Operators", "Patients"])

    plt.show()    


def mun_space():
    mun_data = u.retrieve_JSON(c.MUNICIPALITY_JSON)
    mun_lat = mun_data[c.MUN_LATITUDE]
    mun_lon = mun_data[c.MUN_LONGITUDE]

    # plot each municipality as a green dot
    plt.figure(figsize=(5, 5))
    plt.title("Municipalities")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.scatter(mun_lon, mun_lat, s=100, marker="*")
    plt.show()


def operator_gantt(operator=None, day=None):
    days = m.get_num_days()
    operators = m.get_num_operators()

    # if both operator and day are None, return False
    if operator is None and day is None:
        return False
    
    elif operator is not None:
        schedule = s.operator_schedule(operator, False)
        
        if day is not None:
            schedule = [x for x in schedule if x[c.DAY] == day]
            if schedule == []:
                return False

        # plot
        plt.figure(figsize=(10, 5))
        plt.title(f"Operator {operator} schedule")
        plt.xlabel("Time (minutes)")
        plt.xlim(c.DEF_OP_START_TIME, c.DEF_OP_END_TIME)
        
        if day is not None:
            # y range: only one row, with day as label
            plt.yticks([0], [f"Day {day}"])
        else:
            # y range: one row for each day
            plt.yticks(range(days), [f"Day {x}" for x in range(days)])
            for i in range(days):
                # empty barh
                plt.barh(i, 0, left=0, height=0.9, color='blue', alpha=0.1)

        # for each scheduled visit, plot a rectangle from start to end time
        for visit in schedule:
            start_time = visit[c.START_TIME]
            end_time = visit[c.END_TIME]
            duration = end_time - start_time

            alpha = (visit[c.DAY]+days)/(days*2)
            plt.barh(visit[c.DAY], duration, left=start_time, height=0.9, color='blue', alpha=alpha)
    
    # day is not None, operator is None
    else:
        plt.figure(figsize=(10, 5))
        plt.title(f"Day {day} schedule")
        plt.xlabel("Time (minutes)")
        plt.xlim(c.DEF_OP_START_TIME, c.DEF_OP_END_TIME)

        # y range: one row for each operator
        plt.yticks(range(operators), [f"Operator {x}" for x in range(operators)])

        # for each scheduled visit, plot a rectangle from start to end time
        for operator in range(operators):
            subschedule = s.operator_subschedule(operator, day, verbose=False)
            
            # if there are no visits, leave the row empty but still add it
            if subschedule == []:
                plt.barh(operator, 0, left=0, height=0.9, color='green', alpha=0)
            
            for visit in subschedule:
                start_time = visit[c.START_TIME]
                end_time = visit[c.END_TIME]
                duration = end_time - start_time

                alpha = (operator+operators)/(operators*2)
                plt.barh(operator, duration, left=start_time, height=0.9, color='green', alpha=alpha)

# --------------- END PLOTS --------------- #
