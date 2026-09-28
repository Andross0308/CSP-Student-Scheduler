import os
import datetime as dt
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarService:
    def __init__(self, token_path: Path, credentials_path: Path):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = self.get_credentials()

    def get_credentials(self,):
        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
            creds = flow.run_local_server(port=8000)
            with open("../JSON_file/token.json", "w") as f:
                f.write(creds.to_json())
        return creds

    def fetch_upcoming_events(self, days=7):
        service = build("calendar", "v3", credentials=self.creds)
        time_min = dt.datetime.now(dt.timezone.utc)
        time_max = (dt.timedelta(days) + time_min)
        events = service.events().list(
            calendarId="primary",
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return events.get("items", [])

    def write_upcoming_events(self, new_events: dict):
        service = build("calendar", "v3", credentials=self.creds)
        for task in new_events:
            service.events().insert(
                calendarId="primary",
                body={
                    "summary": task,
                    "start": {"dateTime": new_events[task]["start"], "timeZone": "Europe/Lisbon"},
                    "end": {"dateTime": new_events[task]["end"], "timeZone": "Europe/Lisbon"}
                }
            ).execute()