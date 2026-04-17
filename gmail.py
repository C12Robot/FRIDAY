import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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


def get_gmail_service():
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

    return build('gmail', 'v1', credentials=creds)


def read_emails(max_results=5):
    try:
        service = get_gmail_service()

        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=['INBOX'],
            q='is:unread'
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return "No unread emails found."

        email_summaries = []

        for msg in messages:
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = message['payload']['headers']

            subject = next(
                (h['value'] for h in headers if h['name'] == 'Subject'),
                'No subject'
            )
            sender = next(
                (h['value'] for h in headers if h['name'] == 'From'),
                'Unknown sender'
            )
            date = next(
                (h['value'] for h in headers if h['name'] == 'Date'),
                'Unknown date'
            )

            body = ""
            payload = message['payload']

            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(
                                data).decode('utf-8')[:300]
                            break
            elif 'body' in payload:
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(
                        data).decode('utf-8')[:300]

            email_summaries.append(
                f"From: {sender}\nDate: {date}\nSubject: {subject}\nPreview: {body.strip()[:200]}"
            )

        return "\n\n---\n\n".join(email_summaries)

    except Exception as e:
        return f"Error reading emails: {str(e)}"


def send_email(to, subject, body):
    try:
        service = get_gmail_service()

        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        raw = base64.urlsafe_b64encode(
            message.as_bytes()).decode('utf-8')

        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()

        return f"Email sent to {to} successfully."

    except Exception as e:
        return f"Error sending email: {str(e)}"


def search_emails(query, max_results=3):
    try:
        service = get_gmail_service()

        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return f"No emails found for: {query}"

        email_summaries = []

        for msg in messages:
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = message['payload']['headers']

            subject = next(
                (h['value'] for h in headers if h['name'] == 'Subject'),
                'No subject'
            )
            sender = next(
                (h['value'] for h in headers if h['name'] == 'From'),
                'Unknown sender'
            )

            email_summaries.append(f"From: {sender} | Subject: {subject}")

        return "\n".join(email_summaries)

    except Exception as e:
        return f"Error searching emails: {str(e)}"