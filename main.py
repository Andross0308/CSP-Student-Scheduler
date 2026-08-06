import json

from ortools.sat.python import cp_model

Days_Int = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sabado": 5, "Domingo": 6}
Int_Days = {value: key for key, value in Days_Int.items()}

#Empty Data Structures
tasks = {}
intervals = []
boolean_variables = []
pesos = []

def minutesOfTheWeek(task, time):
    day = Days_Int[task["day"]]
    hour, minute = task[time].split(":")
    return day * 1440 + int(hour) * 60 + int(minute)

def minutesIntoSchedule(minutes):
    day = Int_Days[minutes // 1440]
    hour = (minutes % 1440) // 60
    minute = (minutes % 1440) % 60
    return {"day": day, "hour": hour, "minute": minute}

def fixedTasks(data, model):
    for task in data:
        begin = minutesOfTheWeek(task, "HoraInicio")
        end = minutesOfTheWeek(task, "HoraFim")
        begin_cons = model.new_constant(begin)
        end_cons = model.new_constant(end)
        duration = model.new_constant(end - begin)
        interval = model.new_interval_var(begin_cons, duration, end_cons, task["name"])
        tasks[task["name"]] = {"bool": model.new_constant(1), "start": begin_cons,
                               "duration": duration, "end": end_cons}
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
    tasks[name] = {"bool": bool_var, "start": start, "duration": duration, "end": end}

def addOptionalTasks(optionals, model):
    for task in optionals:
        windows = []
        for domain in task["domains"]:
            Start = minutesOfTheWeek(domain, "HoraInicio")
            End = minutesOfTheWeek(domain, "HoraFim")
            windows.append([Start, End])
        task["intervals"] = windows
        createNewOptionalTask(task["name"], task, model)

def solveSchedule(model):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        generateOutput(solver)
    else:
        print("No solution found")

def generateOutput(solver):
    schedule = []
    for task in tasks:
        if solver.value(tasks[task]["bool"]) == 1:
            begin = minutesIntoSchedule(solver.value(tasks[task]["start"]))
            end = minutesIntoSchedule(solver.value(tasks[task]["end"]))
            schedule.append({"name": task, "start": begin, "end": end})
    with open("output.json", mode="w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False)

def executeSchedule():
    with open("Tasks.json", encoding="utf-8") as f:
        data = json.load(f)
    model = cp_model.CpModel()
    fixedTasks(data["fixedTasks"], model)
    addOptionalTasks(data["optionalTasks"], model)
    solveSchedule(model)

if __name__ == "__main__":
    executeSchedule()