import json
from pathlib import Path

from google_service import GoogleCalendarService
from llm_service import TaskExtractor
from ortools.sat.python import cp_model
from date_utils import *

JSON_DIR = Path(__file__).parent.parent / "JSON_file"


def initialize_global_variables():
    global tasks, intervals, boolean_variables, pesos, stability_bonus
    tasks = {}
    intervals = []
    boolean_variables = []
    pesos = []
    stability_bonus = []

def add_google_events(events, model, reference_time):
    with open("../JSON_file/Library.json", encoding="utf-8") as f:
        data = json.load(f)
    for event in events:
        name = event["summary"]
        previous_start = date_time_field_to_minutes(event, 'start', reference_time)
        previous_start = previous_start if previous_start >= 0 else None
        if name in data and data[name]["kind"] == "optional_task":
            task = data[name]
            windows = []
            for domain in task["domains"]:
                start = date_to_minutes(domain, "HoraInicio", reference_time)
                start = 0 if start < 0 else start
                end = date_to_minutes(domain, "HoraFim", reference_time)
                if end >= 0:
                    windows.append([start, end])
            task["intervals"] = windows
            create_new_optional_task(name, task, model, previous_start)
        else:
            begin = date_time_field_to_minutes(event, "start", reference_time)
            end = date_time_field_to_minutes(event, "end", reference_time)
            add_fixed_entry(name, begin, end, model, True)

def add_llm_events(response, model, reference_time):
    data = json.loads(response)
    for name, value in data.items():
        if value["kind"] == "fixed_task":
            begin = date_to_minutes(value, "HoraInicio", reference_time)
            end = date_to_minutes(value, "HoraFim", reference_time)
            add_fixed_entry(name, begin, end, model, False)
        else:
            windows = []
            for domain in value["domains"]:
                start = date_to_minutes(domain, "HoraInicio", reference_time)
                start = 0 if start < 0 else start
                end = date_to_minutes(domain, "HoraFim", reference_time)
                if end >= 0:
                    windows.append([start, end])
            value["intervals"] = windows
            create_new_optional_task(name, value, model)


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


def create_tasks_stability(model, name, start, previous_start):
    if previous_start is not None:
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

def create_new_optional_task(name, data, model, previous_start=None):
    bool_var = model.new_bool_var(f"{name}_Present")
    boolean_variables.append(bool_var)
    start, duration = create_tasks_start_and_duration(model, name, data)
    create_tasks_stability(model, name, start, previous_start)
    end = create_task_end(model, name, data)
    register_optional_tasks_interval(model, name, data, start, duration, end, bool_var)

def solve_schedule(model, reference_time,google):
    model.maximize(sum(bool_var * peso for bool_var, peso in zip(boolean_variables, pesos)) + sum(stability_bonus))
    model.add_no_overlap(intervals)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        generate_output(solver, reference_time, google)
    else:
        print("No solution found")

def generate_output(solver, reference_time, google):
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
        google.write_upcoming_events(new_events)


def execute_schedule(llm_response):
    model = cp_model.CpModel()
    reference_time = dt.datetime.now().replace(second=0, microsecond=0)
    google_service = GoogleCalendarService(JSON_DIR / "token.json", JSON_DIR / "credentials.json")
    google_events = google_service.fetch_upcoming_events()
    add_llm_events(llm_response, model, reference_time)
    solve_schedule(model, reference_time, google_service)

if __name__ == "__main__":
    initialize_global_variables()
    llm_service = TaskExtractor()
    llm_help = llm_service.extract_task("Tenho uma aula de BD das 5h às 6h de Quarta-Feira")
    print(llm_help)
    execute_schedule(llm_help)