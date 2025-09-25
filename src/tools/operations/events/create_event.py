import os
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks'
]

class GoogleCalendarManager:
    def __init__(self):
        self.calendar_service = None
        self.tasks_service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate and build the Google Calendar service."""
        creds = None
        
        # Get the client secret path from environment variable
        client_secret_path = os.getenv('GOOGLE_CLIENT_SECRET_PATH', 'client_secret.json')
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(client_secret_path):
                    raise FileNotFoundError(f"Client secret file not found at: {client_secret_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.calendar_service = build('calendar', 'v3', credentials=creds)
            self.tasks_service = build('tasks', 'v1', credentials=creds)
            print("Successfully authenticated with Google Calendar and Tasks APIs")
        except HttpError as error:
            print(f"An error occurred while building the services: {error}")
            raise

    def create_event(self, summary, start_time, end_time, description=None, location=None, 
                    attendees=None, calendar_id='primary'):
        """
        Create a new event in Google Calendar.
        
        Args:
            summary (str): Event title
            start_time (datetime): Event start time
            end_time (datetime): Event end time
            description (str, optional): Event description
            location (str, optional): Event location
            attendees (list, optional): List of attendee emails
            calendar_id (str): Calendar ID (default: 'primary')
        
        Returns:
            dict: Created event details
        """
        try:
            event_body = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            # Add optional fields
            if description:
                event_body['description'] = description
            
            if location:
                event_body['location'] = location
            
            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]
            
            # Create the event
            event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            print(f"Event created successfully!")
            print(f"Event ID: {event['id']}")
            print(f"Event Link: {event.get('htmlLink')}")
            
            return event
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def create_task(self, title, notes=None, due_date=None, tasklist_id='@default'):
        """
        Create a new task in Google Tasks.
        
        Args:
            title (str): Task title
            notes (str, optional): Task description/notes
            due_date (datetime, optional): Task due date
            tasklist_id (str): Task list ID (default: '@default')
        
        Returns:
            dict: Created task details
        """
        try:
            task_body = {
                'title': title
            }
            
            # Add optional fields
            if notes:
                task_body['notes'] = notes
            
            if due_date:
                # Convert datetime to RFC 3339 format
                task_body['due'] = due_date.isoformat() + 'Z'
            
            # Create the task
            task = self.tasks_service.tasks().insert(
                tasklist=tasklist_id,
                body=task_body
            ).execute()
            
            print(f"Task created successfully!")
            print(f"Task ID: {task['id']}")
            print(f"Task Title: {task['title']}")
            
            return task
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def complete_task(self, task_id, tasklist_id='@default'):
        """
        Mark a task as completed.
        
        Args:
            task_id (str): Task ID to complete
            tasklist_id (str): Task list ID (default: '@default')
        
        Returns:
            dict: Updated task details
        """
        try:
            task = self.tasks_service.tasks().patch(
                tasklist=tasklist_id,
                task=task_id,
                body={'status': 'completed'}
            ).execute()
            
            print(f"Task '{task['title']}' marked as completed!")
            return task
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def list_tasks(self, tasklist_id='@default', show_completed=False):
        """
        List tasks from a task list.
        
        Args:
            tasklist_id (str): Task list ID (default: '@default')
            show_completed (bool): Whether to show completed tasks
        
        Returns:
            list: List of tasks
        """
        try:
            # Get tasks
            results = self.tasks_service.tasks().list(
                tasklist=tasklist_id,
                showCompleted=show_completed,
                showHidden=False
            ).execute()
            
            tasks = results.get('items', [])
            
            if not tasks:
                print("No tasks found.")
                return []
            
            print(f"\nTasks in list (showing completed: {show_completed}):")
            for task in tasks:
                status = "✓" if task.get('status') == 'completed' else "○"
                due = ""
                if task.get('due'):
                    due_date = datetime.fromisoformat(task['due'].replace('Z', '+00:00'))
                    due = f" (Due: {due_date.strftime('%Y-%m-%d')})"
                
                print(f"{status} {task['title']}{due}")
                if task.get('notes'):
                    print(f"   Notes: {task['notes']}")
            
            return tasks
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def list_task_lists(self):
        """List all available task lists."""
        try:
            results = self.tasks_service.tasklists().list().execute()
            task_lists = results.get('items', [])
            
            print("Available task lists:")
            for task_list in task_lists:
                print(f"- {task_list['title']} (ID: {task_list['id']})")
            
            return task_lists
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def create_task_list(self, title):
        """
        Create a new task list.
        
        Args:
            title (str): Task list title
        
        Returns:
            dict: Created task list details
        """
        try:
            task_list = self.tasks_service.tasklists().insert(
                body={'title': title}
            ).execute()
            
            print(f"Task list '{title}' created successfully!")
            print(f"Task list ID: {task_list['id']}")
            
            return task_list
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def create_all_day_event(self, summary, date, description=None, location=None, 
                            calendar_id='primary'):
        """
        Create an all-day event in Google Calendar.
        
        Args:
            summary (str): Event title
            date (datetime.date): Event date
            description (str, optional): Event description
            location (str, optional): Event location
            calendar_id (str): Calendar ID (default: 'primary')
        
        Returns:
            dict: Created event details
        """
        try:
            event_body = {
                'summary': summary,
                'start': {
                    'date': date.isoformat(),
                },
                'end': {
                    'date': (date + timedelta(days=1)).isoformat(),
                },
            }
            
            # Add optional fields
            if description:
                event_body['description'] = description
            
            if location:
                event_body['location'] = location
            
            # Create the event
            event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            print(f"All-day event created successfully!")
            print(f"Event ID: {event['id']}")
            print(f"Event Link: {event.get('htmlLink')}")
            
            return event
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def list_calendars(self):
        """List all available calendars."""
        try:
            calendars_result = self.calendar_service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            print("Available calendars:")
            for calendar in calendars:
                print(f"- {calendar['summary']} (ID: {calendar['id']})")
            
            return calendars
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None


def main():
    """Example usage of the GoogleCalendarManager."""
    try:
        # Initialize the calendar manager
        calendar_manager = GoogleCalendarManager()
        
        print("=== CALENDAR EVENTS ===")
        
        # Example 1: Create a timed event
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        event = calendar_manager.create_event(
            summary="Meeting with Team",
            start_time=start_time,
            end_time=end_time,
            description="Weekly team standup meeting",
            location="Conference Room A",
            attendees=["colleague@example.com"]  # Add real emails here
        )
        
        # Example 2: Create an all-day event
        from datetime import date
        tomorrow = date.today() + timedelta(days=1)
        
        all_day_event = calendar_manager.create_all_day_event(
            summary="Company Holiday",
            date=tomorrow,
            description="Office closed for holiday"
        )
        
        # Example 3: List available calendars
        calendar_manager.list_calendars()
        
        print("\n=== TASKS ===")
        
        # Example 4: Create a simple task
        task1 = calendar_manager.create_task(
            title="Complete project documentation",
            notes="Write comprehensive documentation for the new feature"
        )
        
        # Example 5: Create a task with due date
        due_date = datetime.now() + timedelta(days=3)
        task2 = calendar_manager.create_task(
            title="Review code changes",
            notes="Review pull requests from team members",
            due_date=due_date
        )
        
        # Example 6: Create a new task list
        task_list = calendar_manager.create_task_list("Work Projects")
        
        # Example 7: Create a task in the new task list
        if task_list:
            task3 = calendar_manager.create_task(
                title="Plan sprint meeting",
                notes="Prepare agenda for next sprint planning",
                tasklist_id=task_list['id']
            )
        
        # Example 8: List all task lists
        calendar_manager.list_task_lists()
        
        # Example 9: List tasks (incomplete only)
        calendar_manager.list_tasks()
        
        # Example 10: List all tasks including completed ones
        # calendar_manager.list_tasks(show_completed=True)
        
        # Example 11: Mark a task as completed (uncomment to use)
        # if task1:
        #     calendar_manager.complete_task(task1['id'])
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()