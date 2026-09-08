import json
import os
import datetime as dt

from ortools.sat.python import cp_model
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI

DAYS_INT = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sabado": 5, "Domingo": 6}
INT_DAYS = {value: key for key, value in DAYS_INT.items()}

PROMPT = """Atua como um conversor de texto para JSON.
A tua tarefa é extrair as informações do "NOVO PEDIDO DO UTILIZADOR" e formatá-las na estrutura JSON especificada.

Regras estritas:
1. Responde APENAS com o objeto JSON final.
2. Não uses marcadores de código Markdown (como ```json ou ```). Não adiciones texto, explicações ou espaços antes ou depois do JSON.
3. Não incluas os dados dos exemplos na resposta. Processa apenas o NOVO PEDIDO.

Estrutura do JSON:
- TAREFA FIXA com nome como chave (fixed_task): "kind", "day", "HoraInicio", "HoraFim"
- TAREFA OPCIONAL com nome como chave (optional_task): "kind", "domains" (lista com "day", "HoraInicio", "HoraFim"), "durationMin", "durationMax", "peso"

Exemplo de formato esperado (NÃO incluir estes dados na resposta):
{
  "Aula_X": {
    "kind": "fixed_task"
    "day": "Terça",
    "HoraInicio": "14:00",
    "HoraFim": "16:00"
  },
    "Gym": {
    "kind": "optional_task",
    "domains": [
      {
        "day": "Segunda",
        "HoraInicio": "8:00",
        "HoraFim": "21:00"
      },
      {
        "day": "Terça",
        "HoraInicio": "8:00",
        "HoraFim": "21:00"
      }
    ],
    "durationMin": 60,
    "durationMax": 60,
    "peso": 3
  }
}

NOVO PEDIDO DO UTILIZADOR: [PEDIDO DO UTILIZADOR]"""

def initialize_global_variables():
    global tasks, intervals, boolean_variables, pesos, stability_bonus
    tasks = {}
    intervals = []
    boolean_variables = []
    pesos = []
    stability_bonus = []

def date_to_minutes(task, timeField, referenceTime):
    today_day = referenceTime.weekday()
    target_day = DAYS_INT[task["day"]]
    days = (target_day - today_day) % 7
    hour, minute = task[timeField].split(":")
    task_date = (referenceTime + dt.timedelta(days=days)).replace(hour=int(hour), minute=int(minute))
    task_minutes = int((task_date - referenceTime).total_seconds() // 60)
    return task_minutes

def minutes_into_schedule(minutes, reference_time):
    date = reference_time + dt.timedelta(minutes=minutes)
    return date.isoformat(timespec="seconds")

def date_time_field_to_minutes(event, field, reference_time):
    time = dt.datetime.fromisoformat(event[field]['date']).replace(tzinfo=None)
    minutes = int((time - reference_time).total_seconds() // 60)
    return minutes

def add_google_events(events, model, reference_time, previous_schedule):
    with open("../JSON_file/Library.json", encoding="utf-8") as f:
        data = json.load(f)
    for event in events:
        if event["summary"] in data and data[event["summary"]]["kind"] == "optional_task":
            task = data[event["summary"]]
            windows = []
            for domain in task["domains"]:
                start = date_to_minutes(domain, "HoraInicio", reference_time)
                start = 0 if start < 0 else start
                end = date_to_minutes(domain, "HoraFim", reference_time)
                if end >= 0:
                    windows.append([start, end])
            task["intervals"] = windows
            create_new_optional_task(event["summary"], task, model, previous_schedule)
        else:
            begin = date_time_field_to_minutes(event, "start", reference_time)
            end = date_time_field_to_minutes(event, "end", reference_time)
            add_fixed_entry(event["summary"], begin, end, model, True)

def add_llm_events(response, model, reference_time, previous_schedule):
    data = json.loads(response)
    for name, value in data.items():
        if value["kind"] == "fixed_task":
            begin = date_time_field_to_minutes(value, "HoraInicio", reference_time)
            end = date_time_field_to_minutes(value, "HoraFim", reference_time)
            add_fixed_entry(value, begin, end, model, False)
        else:
            windows = []
            for domain in value["domains"]:
                start = date_to_minutes(domain, "HoraInicio", reference_time)
                start = 0 if start < 0 else start
                end = date_to_minutes(domain, "HoraFim", reference_time)
                if end >= 0:
                    windows.append([start, end])
            value["intervals"] = windows
            create_new_optional_task(name, value, model, previous_schedule)


def fixed_tasks(data, model, reference_time):
    for task in data:
        begin = date_to_minutes(task, "HoraInicio", reference_time)
        end = date_to_minutes(task, "HoraFim", reference_time)
        add_fixed_entry(task["name"], begin, end, model, False)

def add_fixed_entry(name, begin, end, model, bool):
    begin_cons = model.new_constant(begin)
    end_cons = model.new_constant(end)
    duration = model.new_constant(end - begin)
    interval = model.new_interval_var(begin_cons, duration, end_cons, name)
    tasks[name] = {"bool": model.new_constant(1), "start": begin_cons,
                           "duration": duration, "end": end_cons, "from_google": bool}
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
        "end": end,
        "from_google": False
    }

def create_new_optional_task(name, data, model, previousSchedule):
    bool_var = model.new_bool_var(f"{name}_Present")
    boolean_variables.append(bool_var)
    start, duration = create_tasks_start_and_duration(model, name, data)
    create_tasks_stability(model, name, start, previousSchedule)
    end = create_task_end(model, name, data)
    register_optional_tasks_interval(model, name, data, start, duration, end, bool_var)

def add_optional_tasks(optionals, model, reference_time, previous_schedule):
    for task in optionals:
        windows = []
        for domain in task["domains"]:
            start = date_to_minutes(domain, "HoraInicio", reference_time)
            start = 0 if start < 0 else start
            end = date_to_minutes(domain, "HoraFim", reference_time)
            if end >= 0:
                windows.append([start, end])
        task["intervals"] = windows
        create_new_optional_task(task["name"], task, model, previous_schedule)

def solve_schedule(model, reference_time):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)) + sum(stability_bonus))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        generate_output(solver, reference_time)
    else:
        print("No solution found")

def generate_output(solver, reference_time):
    new_events = {}
    for task in tasks:
        if solver.value(tasks[task]["bool"]) == 1 and not tasks[task]["from_google"]:
            begin = minutes_into_schedule(solver.value(tasks[task]["start"]), reference_time)
            end = minutes_into_schedule(solver.value(tasks[task]["end"]), reference_time)
            new_events[task] = {"start": begin, "end": end}
    for task in new_events:
        print("New task:")
        print(f"Name: {task} \n Begin : {new_events[task]["start"]} \nEnd: {new_events[task]["end"]}\n")
    confirm = input("Confirm this are the correct options to add to your calendar:")
    if confirm == 'y':
        service = build("calendar", "v3", credentials=get_credentials())
        for task in new_events:
            service.events().insert(
                calendarId="primary",
                body= {
                    "summary": task,
                    "start": {"dateTime": new_events[task]["start"], "timeZone": "Europe/Lisbon"},
                    "end": {"dateTime": new_events[task]["end"], "timeZone": "Europe/Lisbon"}
                }
             ).execute()


def load_previous_schedule(reference_time):
    if not os.path.exists("../JSON_file/output.json"):
        return {}
    with open("../JSON_file/output.json", encoding="utf-8") as f:
        data = json.load(f)
    result={}
    for task in data:
        begin = date_time_field_to_minutes(task, "start", reference_time)
        end = date_time_field_to_minutes(task, "end", reference_time)
        if begin >= 0:
            result[task["name"]] = {"start": begin, "end": end}
    return result


def get_credentials(token = "../JSON_file/token.json", credentials = "../JSON_file/credentials.json"):
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = None
    if os.path.exists(token):
        creds = Credentials.from_authorized_user_file(token, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials, SCOPES)
        creds = flow.run_local_server(port=8000)
        with open("../JSON_file/token.json", "w") as f:
            f.write(creds.to_json())

    return creds

def fetch_upcoming_events(creds, days=7):
    service = build("calendar", "v3", credentials=creds)
    time_min = dt.datetime.now(dt.timezone.utc)
    time_max = (dt.timedelta(days) + time_min)
    return service.events().list(
        calendarId="primary",
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

def google_connection(referenceTime, model, previous_schedule):
    creds = get_credentials("../JSON_file/token.json", "../JSON_file/credentials.json")

    events = fetch_upcoming_events(creds)["items"]
    add_google_events(events, model, referenceTime, previous_schedule)

def execute_schedule(llm_response):
    model = cp_model.CpModel()
    reference_time = dt.datetime.now().replace(second=0, microsecond=0)
    previous_schedule = load_previous_schedule(reference_time)
    google_connection(reference_time, model, previous_schedule)
    add_llm_events(llm_response, model, reference_time, previous_schedule)
    solve_schedule(model, reference_time)

def ask_llm(user_request, client):
    prompt = PROMPT.replace("[PEDIDO DO UTILIZADOR]", user_request)
    response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content

if __name__ == "__main__":
    initialize_global_variables()
    client = OpenAI()
    llm_help = ask_llm("Quero jogar Terraria à tarde, peso 3, entre 8h e 21h de Segunda a Sexta, durante 1 hora", client)
    print(llm_help)
    execute_schedule(llm_help)