import json
import os
import datetime as dt

from ortools.sat.python import cp_model
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

Days_Int = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sabado": 5, "Domingo": 6}
Int_Days = {value: key for  key, value in Days_Int.items()}

#Empty Data Structures
tasks = {}
intervals = []
boolean_variables = []
pesos = []

def dateToMinutes(task, timeField, referenceTime):
    todayDay = referenceTime.weekday()
    targetDay = Days_Int[task["day"]]
    days = (targetDay - todayDay) % 7
    hour, minute = task[timeField].split(":")
    taskDate = (referenceTime + dt.timedelta(days=days)).replace(hour=int(hour), minute=int(minute))
    taskMinutes = int((taskDate - referenceTime).total_seconds() // 60)
    return taskMinutes

def minutesIntoSchedule(minutes, referenceTime):
    date = referenceTime + dt.timedelta(minutes=minutes)
    return {"date": date.isoformat(timespec="seconds"), "day_week": Int_Days[date.weekday()]}

def googleEventToMinutes(event, field, referenceTime):
    time = dt.datetime.fromisoformat(event[field]['dateTime']).replace(tzinfo=None)
    minutes = int((time - referenceTime).total_seconds() // 60)
    return minutes

def addGoogleEvents(events, model, referenceTime):
    for event in events:
        begin = googleEventToMinutes(event, "start", referenceTime)
        end = googleEventToMinutes(event, "end", referenceTime)
        addFixedEntry(event["summary"], begin, end, model)

def fixedTasks(data, model, referenceTime):
    for task in data:
        begin = dateToMinutes(task, "HoraInicio", referenceTime)
        end = dateToMinutes(task, "HoraFim", referenceTime)
        addFixedEntry(task["name"], begin, end, model)

def addFixedEntry(name, begin, end, model):
    begin_cons = model.new_constant(begin)
    end_cons = model.new_constant(end)
    duration = model.new_constant(end - begin)
    interval = model.new_interval_var(begin_cons, duration, end_cons, name)
    tasks[name] = {"bool": model.new_constant(1), "start": begin_cons,
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

def addOptionalTasks(optionals, model, referenceTime):
    for task in optionals:
        windows = []
        for domain in task["domains"]:
            Start = dateToMinutes(domain,"HoraInicio", referenceTime)
            End = dateToMinutes(domain, "HoraFim", referenceTime)
            windows.append([Start, End])
        task["intervals"] = windows
        createNewOptionalTask(task["name"], task, model)

def solveSchedule(model, referenceTime):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        generateOutput(solver, referenceTime)
    else:
        print("No solution found")

def generateOutput(solver, referenceTime):
    schedule = []
    for task in tasks:
        if solver.value(tasks[task]["bool"]) == 1:
            begin = minutesIntoSchedule(solver.value(tasks[task]["start"]), referenceTime)
            end = minutesIntoSchedule(solver.value(tasks[task]["end"]), referenceTime)
            schedule.append({"name": task, "start": begin, "end": end})
    with open("JSON file/output.json", mode="w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=3)

def GoogleConnection(referenceTime, model):
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds = None
    if os.path.exists("JSON file/token.json"):
        creds = Credentials.from_authorized_user_file("JSON file/token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("JSON file/credentials.json", SCOPES)
        creds = flow.run_local_server(port=8000)
        with open("JSON file/token.json", "w") as f:
            f.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    timeMin = dt.datetime.now()
    timeMax = (dt.timedelta(days=7) + timeMin)
    events_result = service.events().list(
        calendarId="primary",
        timeMin=timeMin.isoformat() + "Z",
        timeMax=timeMax.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    addGoogleEvents(events_result['items'], model, referenceTime)

def executeSchedule():
    with open("JSON file/Tasks.json", encoding="utf-8") as f:
        data = json.load(f)
    model = cp_model.CpModel()
    referenceTime = dt.datetime.now().replace(second=0)
    GoogleConnection(referenceTime, model)
    fixedTasks(data["fixedTasks"], model, referenceTime)
    addOptionalTasks(data["optionalTasks"], model, referenceTime)
    solveSchedule(model, referenceTime)

if __name__ == "__main__":
    executeSchedule()