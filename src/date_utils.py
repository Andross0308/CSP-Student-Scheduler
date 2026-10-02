import datetime as dt

DAYS_INT = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sabado": 5, "Domingo": 6}

def date_to_minutes(task: dict, time_field: str, reference_time: dt.datetime) -> int:
    today_day = reference_time.weekday()
    target_day = DAYS_INT[task["day"]]
    days = (target_day - today_day) % 7
    hour, minute = task[time_field].split(":")
    task_date = (reference_time + dt.timedelta(days=days)).replace(hour=int(hour), minute=int(minute))
    task_minutes = int((task_date - reference_time).total_seconds() // 60)
    return task_minutes if task_minutes > 0 else (task_minutes + int(dt.timedelta(days=days+7).total_seconds()//60))

def minutes_into_schedule(minutes: int, reference_time: dt.datetime) -> str:
    date = reference_time + dt.timedelta(minutes=minutes)
    return date.isoformat(timespec="seconds")

def date_time_field_to_minutes(event: dict, field: str, reference_time: dt.datetime) -> int:
    time = dt.datetime.fromisoformat(event[field]['dateTime']).replace(tzinfo=None)
    minutes = int((time - reference_time).total_seconds() // 60)
    return minutes