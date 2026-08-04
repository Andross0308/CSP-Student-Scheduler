import json
from ortools.sat.python import cp_model

def minutesOfTheWeek(day, hour, minutes):
    """
    Calculates the minutes since the start of the week to the given time
    :param day: Day of the week
    :param hour: Hour of the given time
    :param minutes: Minutes of the given time
    :return: the time in minutes since the start of the week
    """
    return day * 1440 + hour * 60 + minutes

#Filed Data Structures
optionalTasks = {"Gym": { "domainStart": minutesOfTheWeek(0, 8, 0),
                 "domainEnd": minutesOfTheWeek(0, 21, 0), "durationMin": 60,
                 "durationMax": 60, "peso": 3},
                 "Chess": {"domainStart": minutesOfTheWeek(0, 8, 0),
                 "domainEnd": minutesOfTheWeek(0, 21, 0), "durationMin": 30,
                 "durationMax": 30, "peso": 2},
                 "Study": {"domainStart": minutesOfTheWeek(0, 10, 0),
                 "domainEnd": minutesOfTheWeek(0, 16, 0), "durationMin": 30,
                 "durationMax": 120, "peso": 5},
                 "Library": {"domainStart": minutesOfTheWeek(0, 10, 0),
                 "domainEnd": minutesOfTheWeek(0, 16, 0), "durationMin": 60,
                 "durationMax": 180, "peso": 5}
                 }

Days_Int = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sabado": 5, "Domingo": 6}

#Empty Data Structures
tasks = {}
intervals = []
boolean_variables = []
pesos = []

def fixedTasks(model):
    fixed_tasks = [("Aula BD Pratica", ("Terça", "16:00"), ("Terça", "18:00"), minutesOfTheWeek(1, 16, 0),
                    minutesOfTheWeek(1, 18, 0)),
                   ("Aula LAP Pratica", ("Terça", "14:00"), ("Terça", "16:00"), minutesOfTheWeek(1, 14, 0),
              minutesOfTheWeek(1, 16, 0)),
                   ("Aula PED Pratica", ("Segunda", "10:00"), ("Segunda", "12:00"), minutesOfTheWeek(1, 10, 0),
              minutesOfTheWeek(1, 12, 0)),
                   ("Aula TC Pratica", ("Segunda", "8:00"), ("Segunda", "10:00"), minutesOfTheWeek(0, 8, 0),
              minutesOfTheWeek(0, 10, 0)),
                   ("Aula BD Teorica", ("Quarta", "10:00"), ("Quarta", "11:30"), minutesOfTheWeek(2, 10, 0),
              minutesOfTheWeek(2, 11, 30)),
                   ("Aula LAP Teorica", ("Quinta", "11:30"), ("Quinta", "13:00"), minutesOfTheWeek(3, 11, 30),
              minutesOfTheWeek(3, 13, 0)),
                   ]
    for nome,_,_, begin, end in fixed_tasks:
        duration = end - begin
        interval = model.new_interval_var(begin, duration,end, nome)
        intervals.append(interval)

def createNewOptionalTask(name, data, model):
    bool_var = model.new_bool_var(f"{name}_Present")
    boolean_variables.append(bool_var)
    startDomain = cp_model.Domain.FromIntervals(data["intervals"])
    start = model.new_int_var_from_domain(startDomain, f"{name}_Start")
    duration = model.new_int_var(data["durationMin"], data["durationMax"], f"{name}_Duration")
    end_window = []
    for w_begin, w_end in data["intervals"]:
        end_window.append([w_begin + data["durationMin"], w_end + data["durationMax"]])
    endDomain =  cp_model.Domain.FromIntervals(end_window)
    end = model.new_int_var_from_domain(endDomain, f"{name}_End")
    model.add(start + duration == end)
    var = model.new_optional_interval_var(start, duration, end, bool_var, f"{name}_Interval")
    intervals.append(var)
    pesos.append(data["peso"])
    tasks[name] = {"bool": bool_var, "start": start, "duration": duration, "end": w_end}

def solveSchedule(model):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            showInformation(solver, status)
    else:
        print("No solution found")

def showInformation(solver, status):
    print(solver.status_name(status))
    for name in optionalTasks.keys():
        print(f"{name} starts at {solver.Value(tasks[name]['start'])}")
        print(f"{name} presence at {solver.value(tasks[name]['bool'])}")
        print(f"{name} duration at {solver.value(tasks[name]['duration'])}")


def executeSchedule():
    with open("Tasks.json", encoding="utf-8") as f:
        data = json.load(f)
    model = cp_model.CpModel()
    fixedTasks(model)
    Optional = data["optionalTasks"]
    for task in Optional:
        windows = []
        for domain in task["domains"]:
            day = Days_Int[domain["day"]]
            hourStart, minuteStart = domain["HoraInicio"].split(":")
            hourEnd, minuteEnd = domain["HoraFim"].split(":")
            Start = minutesOfTheWeek(day, int(hourStart), int(minuteStart))
            End = minutesOfTheWeek(day, int(hourEnd), int(minuteEnd))
            windows.append([Start, End])
        task["intervals"] = windows
        createNewOptionalTask(task["nome"], task, model)

    """
    for name, data in optionalTasks.items()
        createNewOptionalTask(name, data, model)"""
    solveSchedule(model)

if __name__ == "__main__":
    executeSchedule()