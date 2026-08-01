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
                   ("Aula PED Pratica", ("Segunda", "10:00"), ("Segunda", "12:00"), minutesOfTheWeek(0, 10, 0),
              minutesOfTheWeek(0, 12, 0)),
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
    startDomain = cp_model.Domain.FromIntervals([[data["domainStart"], data["domainEnd"]]])
    start = model.new_int_var_from_domain(startDomain, f"{name}_Start")
    duration = model.new_int_var(data["durationMin"], data["durationMax"], f"{name}_Duration")
    endDomain =  cp_model.Domain.FromIntervals([[data["domainStart"] + data["durationMin"], data["domainEnd"] + data["durationMax"]]])
    end = model.new_int_var_from_domain(endDomain, f"{name}_End")
    model.add(start + duration == end)
    var = model.new_optional_interval_var(start, duration, end, bool_var, f"{name}_Interval")
    intervals.append(var)
    pesos.append(data["peso"])
    tasks[name] = {"bool": bool_var, "start": start, "duration": duration, "end": end}

def solveSchedule(model):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    showInformation(solver, status)

def showInformation(solver, status):
    for name in optionalTasks.keys():
        print(f"{name} starts at {solver.Value(tasks[name]['start'])}")
        print(f"{name} presence at {solver.value(tasks[name]['bool'])}")
        print(f"{name} duration at {solver.value(tasks[name]['duration'])}")
    print(solver.status_name(status))

def executeSchedule():
    model = cp_model.CpModel()
    fixedTasks(model)
    for name, data in optionalTasks.items():
        createNewOptionalTask(name, data, model)
    solveSchedule(model)

if __name__ == "__main__":
    executeSchedule()