import os
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')


def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def get_upcoming_events(max_results=10):
    try:
        service = get_calendar_service()

        now = datetime.utcnow().isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found."

        formatted = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            location = event.get('location', '')

            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                start_formatted = dt.strftime('%A, %B %d at %I:%M %p')
            except:
                start_formatted = start

            entry = f"{summary} — {start_formatted}"
            if location:
                entry += f" at {location}"
            formatted.append(entry)

        return "\n".join(formatted)

    except Exception as e:
        return f"Error getting events: {str(e)}"


def create_event(summary, start_time, end_time, description="", location=""):
    print(f"\n⚠️  FRIDAY wants to create a calendar event:")
    print(f"   Title: {summary}")
    print(f"   Start: {start_time}")
    print(f"   End:   {end_time}")
    if location:
        print(f"   Location: {location}")

    confirm = input("Confirm? (yes/no): ").strip().lower()

    if confirm != "yes":
        return "Event creation cancelled."

    try:
        service = get_calendar_service()

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Kolkata'
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Kolkata'
            }
        }

        created = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        return f"Event created: {created.get('summary')} — {created.get('htmlLink')}"

    except Exception as e:
        return f"Error creating event: {str(e)}"