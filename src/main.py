import datetime as dt
from pathlib import Path

from google_service import GoogleCalendarService
from llm_service import TaskExtractor
from scheduler import SchedulerSolver

JSON_DIR = Path(__file__).parent.parent / "JSON_file"

def execute_schedule(user_request: str) -> None:
    reference_time = dt.datetime.now().replace(second=0, microsecond=0)
    scheduler = SchedulerSolver(reference_time)
    google_service = GoogleCalendarService(JSON_DIR / "token.json", JSON_DIR / "credentials.json")
    google_events = google_service.fetch_upcoming_events()
    llm_service = TaskExtractor()
    llm_help = llm_service.extract_task(user_request)
    scheduler.add_google_events(google_events, JSON_DIR / "Library.json")
    scheduler.add_llm_events(llm_help)
    events = scheduler.solve_schedule()
    if not events:
        print("No solution")
    else:
        for task in events:
            print("New task:")
            print(f"Name: {task} \n Begin : {events[task]["start"]} \nEnd: {events[task]["end"]}\n")
        confirm = input("Confirm this are the correct options to add to your calendar:")
        if confirm.lower() == 'y':
            google_service.write_upcoming_events(events)

if __name__ == "__main__":
    print("Please entre the new task you want: ")
    prompt = input()
    if prompt == "a":
        prompt = "Quero ir ao ginasio na Segunda, podendo ir entre as 8h e as 21h e quero que dure 1h"
    execute_schedule(prompt)