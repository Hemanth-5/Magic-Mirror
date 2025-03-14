from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/tasks"]

def get_credentials():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    return creds

def get_tasks_service():
    creds = get_credentials()
    service = build("tasks", "v1", credentials=creds)
    return service

def add_task(task_title):
    service = get_tasks_service()
    task = {"title": task_title}
    result = service.tasks().insert(tasklist="@default", body=task).execute()
    return f"Task '{task_title}' added successfully!"

def show_tasks():
    service = get_tasks_service()
    tasks = service.tasks().list(tasklist="@default").execute().get("items", [])
    if not tasks:
        return "No tasks available!"
    
    result = "\n".join([f"{i+1}. {task['title']}" for i, task in enumerate(tasks)])
    return result

def delete_task(task_title):
    service = get_tasks_service()
    tasks = service.tasks().list(tasklist="@default").execute().get("items", [])
    
    for task in tasks:
        if task["title"].lower() == task_title.lower():
            service.tasks().delete(tasklist="@default", task=task["id"]).execute()
            return f"Task '{task_title}' deleted successfully!"
    
    return "Task not found!"
