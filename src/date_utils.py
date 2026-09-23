import datetime as dt

DAYS_INT = {"Segunda": 0, "Terça": 1, "Quarta": 2, "Quinta": 3, "Sexta": 4, "Sabado": 5, "Domingo": 6}
INT_DAYS = {value: key for key, value in DAYS_INT.items()}

def date_to_minutes(task: dict, timeField: str, referenceTime: dt.datetime) -> int:
    today_day = referenceTime.weekday()
    target_day = DAYS_INT[task["day"]]
    days = (target_day - today_day) % 7
    hour, minute = task[timeField].split(":")
    task_date = (referenceTime + dt.timedelta(days=days)).replace(hour=int(hour), minute=int(minute))
    task_minutes = int((task_date - referenceTime).total_seconds() // 60)
    return task_minutes if task_minutes > 0 else (task_minutes + int(dt.timedelta(days=days+7).total_seconds()//60))

def minutes_into_schedule(minutes: int, reference_time: dt.datetime) -> dt.datetime:
    date = reference_time + dt.timedelta(minutes=minutes)
    return date.isoformat(timespec="seconds")

def date_time_field_to_minutes(event: dict, field: str, reference_time: dt.datetime) -> int:
    time = dt.datetime.fromisoformat(event[field]['dateTime']).replace(tzinfo=None)
    minutes = int((time - reference_time).total_seconds() // 60)
    return minutes