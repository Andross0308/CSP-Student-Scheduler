from pathlib import Path

from google_service import GoogleCalendarService
from llm_service import TaskExtractor
from scheduler import SchedulerSolver
from date_utils import *

JSON_DIR = Path(__file__).parent.parent / "JSON_file"

def execute_schedule():
    reference_time = dt.datetime.now().replace(second=0, microsecond=0)
    scheduler = SchedulerSolver(reference_time)
    google_service = GoogleCalendarService(JSON_DIR / "token.json", JSON_DIR / "credentials.json")
    google_events = google_service.fetch_upcoming_events()
    llm_service = TaskExtractor()
    llm_help = llm_service.extract_task("Tenho uma aula de BD das 7h às 8h de Quarta-Feira")
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
        if confirm == 'y':
            google_service.write_upcoming_events(events)

if __name__ == "__main__":
    execute_schedule()