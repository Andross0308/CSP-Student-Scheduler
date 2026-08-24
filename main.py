import json
import os
import datetime as dt

from ortools.sat.python import cp_model
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI

Days_Int = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sabado": 5, "Domingo": 6}
Int_Days = {value: key for  key, value in Days_Int.items()}

#Empty Data Structures
tasks = {}
intervals = []
boolean_variables = []
pesos = []
stability_bonus = []

def date_to_minutes(task, timeField, referenceTime):
    todayDay = referenceTime.weekday()
    targetDay = Days_Int[task["day"]]
    days = (targetDay - todayDay) % 7
    hour, minute = task[timeField].split(":")
    taskDate = (referenceTime + dt.timedelta(days=days)).replace(hour=int(hour), minute=int(minute))
    taskMinutes = int((taskDate - referenceTime).total_seconds() // 60)
    return taskMinutes

def minutes_into_schedule(minutes, referenceTime):
    date = referenceTime + dt.timedelta(minutes=minutes)       #Problem Here!!!!!!!!
    return {"dateTime": date.isoformat(timespec="seconds"), "day_week": Int_Days[date.weekday()]}

def date_time_field_to_minutes(event, field, referenceTime):
    time = dt.datetime.fromisoformat(event[field]['dateTime']).replace(tzinfo=None)
    minutes = int((time - referenceTime).total_seconds() // 60)
    return minutes

def add_google_events(events, model, referenceTime):
    for event in events:
        begin = date_time_field_to_minutes(event, "start", referenceTime)
        end = date_time_field_to_minutes(event, "end", referenceTime)
        add_fixed_entry(event["summary"], begin, end, model)

def fixed_tasks(data, model, referenceTime):
    for task in data:
        begin = date_to_minutes(task, "HoraInicio", referenceTime)
        end = date_to_minutes(task, "HoraFim", referenceTime)
        add_fixed_entry(task["name"], begin, end, model)

def add_fixed_entry(name, begin, end, model):
    begin_cons = model.new_constant(begin)
    end_cons = model.new_constant(end)
    duration = model.new_constant(end - begin)
    interval = model.new_interval_var(begin_cons, duration, end_cons, name)
    tasks[name] = {"bool": model.new_constant(1), "start": begin_cons,
                           "duration": duration, "end": end_cons}
    intervals.append(interval)


def create_tasks_stability(model, name, start, previous_schedule):
    if name in previous_schedule:
        previous_start = previous_schedule[name]["start"]
        keep_schedule = model.new_bool_var(f"{name}_Keep")
        model.add(start == previous_start).only_enforce_if(keep_schedule)
        model.add(start != previous_start).only_enforce_if(~keep_schedule)
        stability_bonus.append(keep_schedule)

def create_tasks_start_and_duration(model, name, data):
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

def register_optional_tasks_interval(model, name, data, start, duration, end, bool_var):
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

def create_new_optional_task(name, data, model, previousSchedule):
    bool_var = model.new_bool_var(f"{name}_Present")
    boolean_variables.append(bool_var)
    start, duration = create_tasks_start_and_duration(model, name, data)
    create_tasks_stability(model, name, start, previousSchedule)
    end = create_task_end(model, name, data)
    register_optional_tasks_interval(model, name, data, start, duration, end, bool_var)

def add_optional_tasks(optionals, model, referenceTime, previousSchedule):
    for task in optionals:
        windows = []
        for domain in task["domains"]:
            start = date_to_minutes(domain, "HoraInicio", referenceTime)
            start = 0 if start < 0 else start
            end = date_to_minutes(domain, "HoraFim", referenceTime)
            if end >= 0:
                windows.append([start, end])
        task["intervals"] = windows
        create_new_optional_task(task["name"], task, model, previousSchedule)

def solve_schedule(model, referenceTime):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)) + sum(stability_bonus))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        generate_output(solver, referenceTime)
    else:
        print("No solution found")

def generate_output(solver, referenceTime):
    schedule = []
    for b in stability_bonus:
        print(solver.value(b))
    for task in tasks:
        if solver.value(tasks[task]["bool"]) == 1:
            begin = minutes_into_schedule(solver.value(tasks[task]["start"]), referenceTime)
            end = minutes_into_schedule(solver.value(tasks[task]["end"]), referenceTime)

            schedule.append({"name": task, "start": begin, "end": end})
    with open("JSON_file/output.json", mode="w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=3)

def load_previous_schedule(referenceTime):
    if not os.path.exists("JSON_file/output.json"):
        return {}
    with open("JSON_file/output.json", encoding="utf-8") as f:
        data = json.load(f)
    result={}
    for task in data:
        begin = date_time_field_to_minutes(task, "start", referenceTime)
        end = date_time_field_to_minutes(task, "end", referenceTime)
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

def fetch_upcoming_events(service, days=7):
    timeMin = dt.datetime.now()
    timeMax = (dt.timedelta(days) + timeMin)
    return service.events().list(
        calendarId="primary",
        timeMin=timeMin.isoformat() + "Z",
        timeMax=timeMax.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

def google_connection(referenceTime, model):
    creds = get_credentials("JSON_file/token.json", "JSON_file/credentials.json")

    service = build("calendar", "v3", credentials=creds)
    events = fetch_upcoming_events(service)
    add_google_events(events['items'], model, referenceTime)

def execute_schedule():
    with open("JSON_file/Tasks.json", encoding="utf-8") as f:
        data = json.load(f)
    model = cp_model.CpModel()
    referenceTime = dt.datetime.now().replace(second=0)
    previousSchedule = load_previous_schedule(referenceTime)
    google_connection(referenceTime, model)
    fixed_tasks(data["fixedTasks"], model, referenceTime)
    add_optional_tasks(data["optionalTasks"], model, referenceTime, previousSchedule)
    solve_schedule(model, referenceTime)

def ask_llm(user_request, client):
    prompt = """Preciso que cries um documento com a informaçao necessario da tarefa do utilizador para puder utilizar no meu programa responde apenas com o JSON, sem texto antes ou depois, em que pode ser uma tarefa fixa, dividida em 'name', 'day', 'HoraInicio', 'HoraFim', ou pode ser opcional, dividida em 'name', 'domains' (que terá uma lista de elementos com os atributos 'day','HoraInicio','HoraFim'), 'durationMin', 'durationMax', 'peso' Exemplo:
{
    "fixedTasks": [{
    "name": "Aula BD Pratica", "day": "Terça", "HoraInicio": "16:00", "HoraFim": "18:00"}], "optionalTasks": [{
      "name":"Gym",
      "domains": [
        {"day": "Segunda",
          "HoraInicio": "8:00",
          "HoraFim": "21:00"},
        {"day": "Terça",
          "HoraInicio": "8:00",
          "HoraFim": "21:00"}],
      "durationMin": 60,
      "durationMax": 60,
      "peso": 3}
   ]
}

Pedido do Utilizador: [PEDIDO DO UTILIZADOR]""".replace("[PEDIDO DO UTILIZADOR]", user_request)
    response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
    print("shit")

if __name__ == "__main__":
    #execute_schedule()
    print(os.environ.get("OPENAI_API_KEY"))
    client = OpenAI()
    ask_llm("Tenho aula de BD à Terça das 16h às 18h, e quero ir ao Ginásio à tarde, peso 3, entre 8h e 21h de Segunda a Sexta, durante 1 hora", client)