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
stability_bonus = []

def dateToMinutes(task, timeField, referenceTime):
    todayDay = referenceTime.weekday()
    targetDay = Days_Int[task["day"]]
    days = (targetDay - todayDay) % 7
    hour, minute = task[timeField].split(":")
    taskDate = (referenceTime + dt.timedelta(days=days)).replace(hour=int(hour), minute=int(minute))
    taskMinutes = int((taskDate - referenceTime).total_seconds() // 60)
    return taskMinutes

def minutesIntoSchedule(minutes, referenceTime):
    date = referenceTime + dt.timedelta(minutes=minutes)       #Problem Here!!!!!!!!
    return {"dateTime": date.isoformat(timespec="seconds"), "day_week": Int_Days[date.weekday()]}

def dateTimeFieldToMinutes(event, field, referenceTime):
    time = dt.datetime.fromisoformat(event[field]['dateTime']).replace(tzinfo=None)
    minutes = int((time - referenceTime).total_seconds() // 60)
    return minutes

def addGoogleEvents(events, model, referenceTime):
    for event in events:
        begin = dateTimeFieldToMinutes(event, "start", referenceTime)
        end = dateTimeFieldToMinutes(event, "end", referenceTime)
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


def create_task_stability(model, name, start, previous_schedule):

    keep_schedule = None
    if name in previous_schedule:
        previous_start = previous_schedule[name]["start"]
        keep_schedule = model.new_bool_var(f"{name}_Keep")
        model.add(start == previous_start).only_enforce_if(keep_schedule)
        model.add(start != previous_start).only_enforce_if(~keep_schedule)
        stability_bonus.append(keep_schedule)

def create_task_start_and_duration(model, name, data):
    start_domain = cp_model.Domain.FromIntervals(data["intervals"])
    start = model.new_int_var_from_domain(start_domain, f"{name}_Start")
    duration = model.new_int_var(data["durationMin"], data["durationMax"], f"{name}_Duration")
    return start, duration

def create_task_end(model, name, data):
    end_window = [
        [begin + data["durationMin"], end + data["durationMax"]]
        for begin, end in data["intervals"]
    ]
    end_domain = cp_model.Domain.FromIntervals(end_window)
    return model.new_int_var_from_domain(end_domain, f"{name}_End")


def register_optional_task_interval(model, name, data, start, duration, end, bool_var):
    model.add(start + duration == end)
    interval_var = model.new_optional_interval_var(start, duration, end, bool_var, f"{name}_Interval")

    intervals.append(interval_var)
    pesos.append(data["peso"])
    tasks[name] = {
        "bool": bool_var,
        "start": start,
        "duration": duration,
        "end": end
    }

def createNewOptionalTask(name, data, model, previousSchedule):
    bool_var = model.new_bool_var(f"{name}_Present")
    boolean_variables.append(bool_var)
    start, duration = create_task_start_and_duration(model, name, data)

    create_task_stability(model, name, start, previousSchedule)

    end = create_task_end(model, name, data)

    register_optional_task_interval(model, name, data, start, duration, end, bool_var)

def addOptionalTasks(optionals, model, referenceTime, previousSchedule):
    for task in optionals:
        windows = []
        for domain in task["domains"]:
            start = dateToMinutes(domain,"HoraInicio", referenceTime)
            start = 0 if start < 0 else start
            end = dateToMinutes(domain, "HoraFim", referenceTime)
            if end >= 0:
                windows.append([start, end])
        task["intervals"] = windows
        createNewOptionalTask(task["name"], task, model, previousSchedule)

def solveSchedule(model, referenceTime):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)) + sum(stability_bonus))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        generateOutput(solver, referenceTime)
    else:
        print("No solution found")

def generateOutput(solver, referenceTime):
    schedule = []
    for b in stability_bonus:
        print(solver.value(b))
    for task in tasks:
        if solver.value(tasks[task]["bool"]) == 1:
            begin = minutesIntoSchedule(solver.value(tasks[task]["start"]), referenceTime)
            end = minutesIntoSchedule(solver.value(tasks[task]["end"]), referenceTime)

            schedule.append({"name": task, "start": begin, "end": end})
    with open("JSON_file/output.json", mode="w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=3)

def loadPreviousSchedule(referenceTime):
    if not os.path.exists("JSON_file/output.json"):
        return {}
    with open("JSON_file/output.json", encoding="utf-8") as f:
        data = json.load(f)
    result={}
    for task in data:
        begin = dateTimeFieldToMinutes(task, "start", referenceTime)
        end = dateTimeFieldToMinutes(task, "end", referenceTime)
        result[task["name"]] = {"start": begin, "end": end}
    return result


def get_credentials(token, credentials):
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds = None
    if os.path.exists(token):
        creds = Credentials.from_authorized_user_file(token, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials, SCOPES)
        creds = flow.run_local_server(port=8000)
        with open("JSON_file/token.json", "w") as f:
            f.write(creds.to_json())

    return creds

def fetchUpcomingEvents(service, days=7):
    timeMin = dt.datetime.now()
    timeMax = (dt.timedelta(days) + timeMin)
    return service.events().list(
        calendarId="primary",
        timeMin=timeMin.isoformat() + "Z",
        timeMax=timeMax.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

def GoogleConnection(referenceTime, model):
    creds = get_credentials("JSON_file/token.json", "JSON_file/credentials.json")

    service = build("calendar", "v3", credentials=creds)
    events = fetchUpcomingEvents(service)
    addGoogleEvents(events['items'], model, referenceTime)

def executeSchedule():
    with open("JSON_file/Tasks.json", encoding="utf-8") as f:
        data = json.load(f)
    model = cp_model.CpModel()
    referenceTime = dt.datetime.now().replace(second=0)
    previousSchedule = loadPreviousSchedule(referenceTime)
    GoogleConnection(referenceTime, model)
    fixedTasks(data["fixedTasks"], model, referenceTime)
    addOptionalTasks(data["optionalTasks"], model, referenceTime, previousSchedule)
    solveSchedule(model, referenceTime)

if __name__ == "__main__":
    executeSchedule()