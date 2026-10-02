import json
import datetime as dt
from ortools.sat.python import cp_model
from date_utils import (date_time_field_to_minutes, date_to_minutes, minutes_into_schedule)

class SchedulerSolver:
    def __init__(self, reference_time: dt.datetime):
        self.model = cp_model.CpModel()
        self.reference_time = reference_time
        self.tasks = {}
        self.intervals = []
        self.boolean_variables = []
        self.weights = []
        self.stability_bonus = []

    def add_google_events(self, events: list, library: dict):
        with open(library, encoding="utf-8") as f:
            data = json.load(f)
        for event in events:
            name = event["summary"]
            previous_start = date_time_field_to_minutes(event, 'start', self.reference_time)
            previous_start = previous_start if previous_start >= 0 else None
            if name in data and data[name]["kind"] == "optional_task":
                task = data[name]
                self.create_new_optional_task(name, task, previous_start)
            else:
                begin = date_time_field_to_minutes(event, "start", self.reference_time)
                end = date_time_field_to_minutes(event, "end", self.reference_time)
                self.add_fixed_entry(name, begin, end, from_google=True)

    def add_llm_events(self, response: dict):
        for name, value in response.items():
            if value["kind"] == "fixed_task":
                begin = date_to_minutes(value, "start", self.reference_time)
                end = date_to_minutes(value, "end", self.reference_time)
                self.add_fixed_entry(name, begin, end, False)
            else:
                self.create_new_optional_task(name, value)

    def add_fixed_entry(self, name: str, begin: int, end: int, from_google: bool):
        duration = self.model.new_constant(end - begin)
        interval = self.model.new_fixed_size_interval_var(begin, duration, name)
        self.tasks[name] = {"bool": self.model.new_constant(1), "start": begin,
                       "duration": duration, "end": end, "from_google": from_google}
        self.intervals.append(interval)

    def create_task_window(self, task: dict) -> dict:
        windows = []
        for domain in task["domains"]:
            start = max(date_to_minutes(domain, "start", self.reference_time), 0)
            end = date_to_minutes(domain, "end", self.reference_time)
            if end >= 0:
                windows.append([start, end])
        task["intervals"] = windows
        return task


    def create_tasks_stability(self, name: str, start: cp_model.IntVar, previous_start: int | None) -> None:
        if previous_start is not None:
            keep_schedule = self.model.new_bool_var(f"{name}_Keep")
            self.model.add(start == previous_start).only_enforce_if(keep_schedule)
            self.stability_bonus.append(keep_schedule)

    def create_tasks_start_and_duration(self, name: str, data: dict) \
            -> tuple[cp_model.IntVar, cp_model.IntVar]:
        start_domain = cp_model.Domain.FromIntervals(data["intervals"])
        start = self.model.new_int_var_from_domain(start_domain, f"{name}_Start")
        duration = self.model.new_int_var(data["durationMin"], data["durationMax"], f"{name}_Duration")
        return start, duration

    def create_task_end(self, name: str, data: dict):
        end_window = [
            [begin + data["durationMin"], end + data["durationMax"]]
            for begin, end in data["intervals"]
        ]
        end_domain = cp_model.Domain.FromIntervals(end_window)
        return self.model.new_int_var_from_domain(end_domain, f"{name}_End")

    def register_optional_tasks_interval(self, name: str, data: dict, start: cp_model.IntVar, duration: cp_model.IntVar,
                                         end: cp_model.IntVar, bool_var: cp_model.BoolVarT) ->None:
        self.model.add(start + duration == end)
        interval_var = self.model.new_optional_interval_var(start, duration, end, bool_var, f"{name}_Interval")

        self.intervals.append(interval_var)
        self.weights.append(data["peso"])
        self.tasks[name] = {
            "bool": bool_var,
            "start": start,
            "duration": duration,
            "end": end,
            "from_google": False
        }

    def create_new_optional_task(self, name: str, data: dict, previous_start: int |None =None):
        bool_var = self.model.new_bool_var(f"{name}_Present")
        self.boolean_variables.append(bool_var)
        task = self.create_task_window(data)
        start, duration = self.create_tasks_start_and_duration(name, task)
        self.create_tasks_stability(name, start, previous_start)
        end = self.create_task_end(name, task)
        self.register_optional_tasks_interval(name, task, start, duration, end, bool_var)

    def solve_schedule(self) -> dict | None:
        self.model.maximize(sum(bool_var * peso for bool_var, peso in zip(self.boolean_variables, self.weights))
                            + sum(self.stability_bonus))
        self.model.add_no_overlap(self.intervals)
        solver = cp_model.CpSolver()
        status = solver.solve(self.model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self.generate_output(solver)
        return None

    def generate_output(self, solver: cp_model.CpSolver) -> dict:
        new_events = {}
        for name, task in self.tasks.items():
            is_present = (
                solver.value(task["bool"]) == 1
                if isinstance(task["bool"], cp_model.BoolVarT)
                else task["bool"] == 1
            )
            if is_present and not task["from_google"]:
                begin = minutes_into_schedule(solver.value(task["start"]), self.reference_time)
                end = minutes_into_schedule(solver.value(task["end"]), self.reference_time)
                new_events[name] = {"start": begin, "end": end}
        return new_events