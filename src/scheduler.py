import json
from ortools.sat.python import cp_model
from date_utils import *

class SchedulerSolver:
    def __init__(self, reference_time: dt.datetime):
        self.model = cp_model.CpModel()
        self.reference_time = reference_time
        self.tasks = {}
        self.intervals = []
        self.boolean_variables = []
        self.pesos = []
        self.stability_bonus = []

    def add_google_events(self, events, library):
        with open(library, encoding="utf-8") as f:
            data = json.load(f)
        for event in events:
            name = event["summary"]
            previous_start = date_time_field_to_minutes(event, 'start', self.reference_time)
            previous_start = previous_start if previous_start >= 0 else None
            if name in data and data[name]["kind"] == "optional_task":
                task = data[name]
                windows = []
                for domain in task["domains"]:
                    start = date_to_minutes(domain, "start", self.reference_time)
                    start = 0 if start < 0 else start
                    end = date_to_minutes(domain, "end", self.reference_time)
                    if end >= 0:
                        windows.append([start, end])
                task["intervals"] = windows
                self.create_new_optional_task(name, task, previous_start)
            else:
                begin = date_time_field_to_minutes(event, "start", self.reference_time)
                end = date_time_field_to_minutes(event, "end", self.reference_time)
                self.add_fixed_entry(name, begin, end, True)

    def create_tasks_stability(self, name, start, previous_start):
        if previous_start is not None:
            keep_schedule = self.model.new_bool_var(f"{name}_Keep")
            self.model.add(start == previous_start).only_enforce_if(keep_schedule)
            self.model.add(start != previous_start).only_enforce_if(~keep_schedule)
            self.stability_bonus.append(keep_schedule)

    def create_tasks_start_and_duration(self, name, data):
        start_domain = cp_model.Domain.FromIntervals(data["intervals"])
        start = self.model.new_int_var_from_domain(start_domain, f"{name}_Start")
        duration = self.model.new_int_var(data["durationMin"], data["durationMax"], f"{name}_Duration")
        return start, duration

    def create_task_end(self, name, data):
        end_window = [
            [begin + data["durationMin"], end + data["durationMax"]]
            for begin, end in data["intervals"]
        ]
        end_domain = cp_model.Domain.FromIntervals(end_window)
        return self.model.new_int_var_from_domain(end_domain, f"{name}_End")

    def register_optional_tasks_interval(self, name, data, start, duration, end, bool_var):
        self.model.add(start + duration == end)
        interval_var = self.model.new_optional_interval_var(start, duration, end, bool_var, f"{name}_Interval")

        self.intervals.append(interval_var)
        self.pesos.append(data["peso"])
        self.tasks[name] = {
            "bool": bool_var,
            "start": start,
            "duration": duration,
            "end": end,
            "from_google": False
        }

    def create_new_optional_task(self, name, data, previous_start=None):
        bool_var = self.model.new_bool_var(f"{name}_Present")
        self.boolean_variables.append(bool_var)
        start, duration = self.create_tasks_start_and_duration(name, data)
        self.create_tasks_stability(name, start, previous_start)
        end = self.create_task_end(name, data)
        self.register_optional_tasks_interval(name, data, start, duration, end, bool_var)

    def add_fixed_entry(self, name, begin, end, bool):
        begin_cons = self.model.new_constant(begin)
        end_cons = self.model.new_constant(end)
        duration = self.model.new_constant(end - begin)
        interval = self.model.new_interval_var(begin_cons, duration, end_cons, name)
        self.tasks[name] = {"bool": self.model.new_constant(1), "start": begin_cons,
                       "duration": duration, "end": end_cons, "from_google": bool}
        self.intervals.append(interval)

    def add_llm_events(self, response: dict):
        for name, value in response.items():
            if value["kind"] == "fixed_task":
                begin = date_to_minutes(value, "start", self.reference_time)
                end = date_to_minutes(value, "end", self.reference_time)
                self.add_fixed_entry(name, begin, end, False)
            else:
                windows = []
                for domain in value["domains"]:
                    start = date_to_minutes(domain, "start", self.reference_time)
                    start = 0 if start < 0 else start
                    end = date_to_minutes(domain, "end", self.reference_time)
                    if end >= 0:
                        windows.append([start, end])
                value["intervals"] = windows
                self.create_new_optional_task(name, value)

    def solve_schedule(self):
        self.model.maximize(sum(bool_var * peso for bool_var, peso in zip(self.boolean_variables, self.pesos))
                            + sum(self.stability_bonus))
        self.model.add_no_overlap(self.intervals)
        solver = cp_model.CpSolver()
        status = solver.solve(self.model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self.generate_output(solver)
        else:
            return None

    def generate_output(self, solver):
        new_events = {}
        for task in self.tasks:
            if solver.value(self.tasks[task]["bool"]) == 1 and not self.tasks[task]["from_google"]:
                begin = minutes_into_schedule(solver.value(self.tasks[task]["start"]), self.reference_time)
                end = minutes_into_schedule(solver.value(self.tasks[task]["end"]), self.reference_time)
                new_events[task] = {"start": begin, "end": end}
        return new_events