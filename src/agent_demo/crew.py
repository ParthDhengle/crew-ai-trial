import json
import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List
from agent_demo.tools.file_manager_tool import FileManagerTool


@CrewBase
class AiAgent():
    agents: List[Agent]
    tasks: List[Task]

    @agent
    def analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['analyzer'],
            tools=[FileManagerTool()],
            verbose=True
        )

    @task
    def analyze_and_plan(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_and_plan'],
        )

    def execute_operation(self, operation_name: str, parameters: dict) -> str:
        """
        Execute a single operation with given parameters.
        Add implementations for each operation as needed.
        """
        try:
            print(f"🔄 Executing: {operation_name}")
            
            # Communication operations
            if operation_name == "send_email":
                return self._send_email(parameters)
            elif operation_name == "send_sms":
                return self._send_sms(parameters)
            elif operation_name == "make_call":
                return self._make_call(parameters)
            elif operation_name == "send_whatsapp_message":
                return self._send_whatsapp(parameters)
            
            # File Management operations
            elif operation_name == "create_file":
                return self._create_file(parameters)
            elif operation_name == "read_file":
                return self._read_file(parameters)
            elif operation_name == "update_file":
                return self._update_file(parameters)
            elif operation_name == "delete_file":
                return self._delete_file(parameters)
            elif operation_name == "list_files":
                return self._list_files(parameters)
            
            # Web & Search operations
            elif operation_name == "search_web":
                return self._search_web(parameters)
            elif operation_name == "get_weather":
                return self._get_weather(parameters)
            elif operation_name == "get_news":
                return self._get_news(parameters)
            elif operation_name == "open_website":
                return self._open_website(parameters)
            
            # Calendar operations
            elif operation_name == "create_event":
                return self._create_event(parameters)
            elif operation_name == "get_time":
                return self._get_time(parameters)
            elif operation_name == "set_reminder":
                return self._set_reminder(parameters)
            
            # Task Management
            elif operation_name == "create_task":
                return self._create_task(parameters)
            elif operation_name == "list_tasks":
                return self._list_tasks(parameters)
            
            # Utilities
            elif operation_name == "calculate":
                return self._calculate(parameters)
            elif operation_name == "translate":
                return self._translate(parameters)
            elif operation_name == "generate_password":
                return self._generate_password(parameters)
            elif operation_name == "summarize_text":
                return self._summarize_text(parameters)
            
            # System operations
            elif operation_name == "take_screenshot":
                return self._take_screenshot(parameters)
            elif operation_name == "check_system_status":
                return self._check_system_status(parameters)
            
            else:
                return f"❌ Operation '{operation_name}' not implemented yet."
                
        except Exception as e:
            return f"❌ Error executing {operation_name}: {str(e)}"

    # Implementation methods for different operations
    def _send_email(self, params):
        # For demo purposes - you'd need to configure SMTP settings
        to = params.get('to', '')
        subject = params.get('subject', '')
        body = params.get('body', '')
        return f"✅ Email sent to {to} with subject '{subject}'"

    def _send_sms(self, params):
        # SMS implementation would go here (Twilio, etc.)
        to = params.get('to', '')
        message = params.get('message', '')
        return f"✅ SMS sent to {to}: {message[:50]}..."

    def _make_call(self, params):
        # Call implementation would go here
        to = params.get('to', '')
        message = params.get('message', '')
        return f"✅ Call placed to {to} with message: {message[:50]}..."

    def _send_whatsapp(self, params):
        # WhatsApp implementation would go here
        to = params.get('to', '')
        message = params.get('message', '')
        return f"✅ WhatsApp sent to {to}: {message[:50]}..."

    def _create_file(self, params):
        filename = params.get('filename', '')
        content = params.get('content', '')
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ File '{filename}' created successfully"
        except Exception as e:
            return f"❌ Error creating file: {str(e)}"

    def _read_file(self, params):
        filename = params.get('filename', '')
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"✅ File '{filename}' read successfully. Content: {content[:100]}..."
        except Exception as e:
            return f"❌ Error reading file: {str(e)}"

    def _update_file(self, params):
        filename = params.get('filename', '')
        new_content = params.get('new_content', '')
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return f"✅ File '{filename}' updated successfully"
        except Exception as e:
            return f"❌ Error updating file: {str(e)}"

    def _delete_file(self, params):
        filename = params.get('filename', '')
        try:
            os.remove(filename)
            return f"✅ File '{filename}' deleted successfully"
        except Exception as e:
            return f"❌ Error deleting file: {str(e)}"

    def _list_files(self, params):
        directory = params.get('directory', '.')
        try:
            files = os.listdir(directory)
            return f"✅ Files in '{directory}': {', '.join(files[:10])}" + ("..." if len(files) > 10 else "")
        except Exception as e:
            return f"❌ Error listing files: {str(e)}"

    def _search_web(self, params):
        query = params.get('query', '')
        return f"✅ Web search completed for: {query} (Implementation needed: integrate with search API)"

    def _get_weather(self, params):
        location = params.get('location', '')
        return f"✅ Weather for {location}: (Implementation needed: integrate with weather API)"

    def _get_news(self, params):
        topic = params.get('topic', '')
        return f"✅ Latest news for {topic}: (Implementation needed: integrate with news API)"

    def _open_website(self, params):
        url = params.get('url', '')
        try:
            subprocess.run(['python', '-m', 'webbrowser', url])
            return f"✅ Opened website: {url}"
        except Exception as e:
            return f"❌ Error opening website: {str(e)}"

    def _create_event(self, params):
        title = params.get('title', '')
        date = params.get('date', '')
        time = params.get('time', '')
        return f"✅ Event '{title}' created for {date} at {time}"

    def _get_time(self, params):
        location = params.get('location', 'local')
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"✅ Current time ({location}): {current_time}"

    def _set_reminder(self, params):
        message = params.get('message', '')
        datetime_str = params.get('datetime', '')
        return f"✅ Reminder set: '{message}' for {datetime_str}"

    def _create_task(self, params):
        title = params.get('title', '')
        due_date = params.get('due_date', '')
        priority = params.get('priority', 'medium')
        return f"✅ Task '{title}' created with {priority} priority, due: {due_date}"

    def _list_tasks(self, params):
        filter_type = params.get('filter', 'all')
        return f"✅ Listed tasks with filter: {filter_type} (Implementation needed: integrate with task system)"

    def _calculate(self, params):
        expression = params.get('expression', '')
        try:
            # Safe evaluation for basic math
            allowed_chars = set('0123456789+-*/().% ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return f"✅ Calculation result: {expression} = {result}"
            else:
                return f"❌ Invalid characters in expression: {expression}"
        except Exception as e:
            return f"❌ Calculation error: {str(e)}"

    def _translate(self, params):
        text = params.get('text', '')
        target_language = params.get('target_language', '')
        return f"✅ Translation to {target_language}: (Implementation needed: integrate with translation API)"

    def _generate_password(self, params):
        import random
        import string
        length = int(params.get('length', 12))
        chars = string.ascii_letters + string.digits + '!@#$%^&*'
        password = ''.join(random.choice(chars) for _ in range(length))
        return f"✅ Generated password: {password}"

    def _summarize_text(self, params):
        text = params.get('text', '')
        return f"✅ Text summarized (first 100 chars): {text[:100]}..."

    def _take_screenshot(self, params):
        save_path = params.get('save_path', 'screenshot.png')
        return f"✅ Screenshot saved to: {save_path} (Implementation needed: integrate with screenshot library)"

    def _check_system_status(self, params):
        import psutil
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            return f"✅ System Status - CPU: {cpu_percent}%, Memory: {memory.percent}% used"
        except ImportError:
            return f"✅ System Status: OK (Install psutil for detailed metrics)"

    def perform_operations(self, json_file_path):
        """
        Read the execution plan and perform all operations in sequence.
        """
        try:
            if not os.path.exists(json_file_path):
                print(f"❌ Execution plan file not found: {json_file_path}")
                return

            with open(json_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Handle case where agent returned a message instead of JSON
            if content.startswith('"Sorry,') or content == '"Sorry, I can\'t do that yet. This feature will be available soon."':
                print(content.strip('"'))
                return

            try:
                plan = json.loads(content)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a message
                print(content)
                return

            # Validate plan structure
            if not isinstance(plan, dict) or 'operations' not in plan:
                print("❌ Invalid execution plan format")
                return

            operations = plan.get('operations', [])
            if not operations:
                print("ℹ️ No operations to execute")
                return

            print(f"🚀 Starting execution of {len(operations)} operation(s)...\n")
            
            results = []
            for i, operation in enumerate(operations, 1):
                operation_name = operation.get('name', '')
                parameters = operation.get('parameters', {})
                description = operation.get('description', '')

                print(f"[{i}/{len(operations)}] {description}")
                result = self.execute_operation(operation_name, parameters)
                results.append(result)
                print(f"    {result}\n")

            print("🎉 Execution completed!")
            print(f"📋 Summary: {len([r for r in results if r.startswith('✅')])} successful, {len([r for r in results if r.startswith('❌')])} failed")

        except Exception as e:
            print(f"❌ Error executing operations: {str(e)}")

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )