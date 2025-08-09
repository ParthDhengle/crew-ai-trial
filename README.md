# AI Agent Demo

This project is a demonstration of an AI assistant built using [CrewAI](https://github.com/crewAIInc/crewAI), a framework for orchestrating AI agents. The assistant processes natural language user queries, analyzes them against a predefined set of operations and user preferences, creates an execution plan, and performs tasks such as file management, calculations, system operations, web interactions, and more. It leverages large language models (LLMs) like Google's Gemini (default) or Groq's models for reasoning and planning.

The core functionality includes:
- **Query Analysis**: An agent reads user preferences (e.g., name, location, interests) and available operations to map queries to executable steps.
- **Operation Execution**: Supports a wide range of operations (detailed below) via a centralized tool.
- **Interactive Mode**: Run in a command-line interface for ongoing queries, or pass single queries as arguments.
- **Personalization**: Incorporates user details from `knowledge/user_preference.txt` (e.g., default location as San Francisco).
- **Extensibility**: Custom tools for file management, operations, and system tasks.

This project is ideal for exploring AI agents in automation, task management, and natural language interfaces. It's structured as a Python package with a CrewAI crew, agents, tasks, and tools.

## Prerequisites

- Python 3.10 to 3.13 (as specified in `pyproject.toml`).
- A compatible LLM API key (e.g., from Google Gemini or Groq). Sign up at:
  - [Google AI Studio](https://aistudio.google.com/) for Gemini.
  - [Groq](https://groq.com/) for alternative models like Mixtral.

## Installation

This project uses [UV](https://github.com/astral-sh/uv), a fast Python package installer, resolver, and virtual environment manager (similar to Poetry or Pipenv but faster). UV handles dependencies, virtual environments, and scripts defined in `pyproject.toml`.

### Step 1: Install UV

UV can be installed via a simple script. Choose one of the methods below:

- **Via curl (recommended for Unix-like systems)**:
curl -LsSf https://astral.sh/uv/install.sh | sh
text- **Via Homebrew (macOS)**:
brew install uv
text- **Via pip (if you already have Python)**:
pip install uv
text- For Windows or other platforms, see the [official UV installation guide](https://docs.astral.sh/uv/getting-started/installation/).

After installation, verify UV:
uv --version

### Step 2: Set Up the Project

Clone or download the project repository, then navigate to the project directory:
cd parthdhengle-crew-ai-trial
textCreate and activate a virtual environment, then install dependencies:
uv venv  # Creates a virtual environment in .venv
source .venv/bin/activate  # Activate on Unix-like systems (use .venv\Scripts\activate on Windows)
uv sync  # Installs dependencies from pyproject.toml, including crewai[tools]
textThis will install all required packages, such as `crewai` and its tools extras.

### Step 3: Configure Environment Variables

Create a `.env` file in the project root to store your LLM API key. The project uses Gemini by default, but you can switch to Groq by updating `src/agent_demo/crew.py`.

Example `.env` content:
GEMINI_API_KEY=your-gemini-api-key-here
Alternatively, for Groq:
GROQ_API_KEY=your-groq-api-key-here
textThe code loads these via `os.getenv("GEMINI_API_KEY")` or similar. Ensure the `.env` is not committed to version control (add it to `.gitignore`).

### Step 4: Prepare Knowledge Files

The project relies on two knowledge files (already included but customizable):
- `knowledge/user_preference.txt`: User details (e.g., name: John Doe, location: San Francisco, interests: AI Agents).
- `knowledge/operations.txt`: List of supported operations (see below).

If these files are missing, the project will error out—ensure they exist.

## Running the Project

UV integrates with the scripts defined in `pyproject.toml` (e.g., `crewai run`, `train`, etc.). Activate your virtual environment first.

### Interactive Mode
Run the assistant in an interactive CLI loop:
uv run run_crew
text- You'll see a welcome message with examples.
- Type queries like "Get the weather for San Francisco" or "Calculate 10 + 15".
- Type `help` for examples, `quit` to exit.

### Single Query Mode
Pass a query as a command-line argument:
uv run run_crew "Create a file called notes.txt with content: Hello World"
text### Other Commands
- **Train**: Placeholder for future training (not implemented):
uv run train
text- **Replay**: Placeholder for replaying past executions:
uv run replay
text- **Test**: Runs predefined test queries:
uv run test
textThe execution flow:
1. Analyzes the query using the CrewAI agent.
2. Generates `execution_plan.json` if operations match.
3. Executes operations sequentially and reports results.

## Available Operations

The assistant can only perform operations listed in `knowledge/operations.txt`. If a query doesn't match, it responds with "Sorry, I can't do that yet. This feature will be available soon."

Here's the full list (grouped by category):

### Communication
- `send_email` (parameters: to, subject, body): Sends an email.
- `send_sms` (parameters: to, message): Sends an SMS.
- `make_call` (parameters: to, message): Places a call.
- `send_whatsapp_message` (parameters: to, message): Sends a WhatsApp message.

### File Management
- `create_file` (parameters: filename, content): Creates a file.
- `read_file` (parameters: filename): Reads file content.
- `update_file` (parameters: filename, new_content): Updates a file.
- `delete_file` (parameters: filename): Deletes a file.
- `list_files` (parameters: directory): Lists files in a directory.

### Web & Search
- `search_web` (parameters: query): Searches the internet.
- `download_file` (parameters: url, save_path): Downloads a file.
- `open_website` (parameters: url): Opens a website.
- `get_weather` (parameters: location): Fetches weather.
- `get_news` (parameters: topic): Retrieves news.

### Calendar & Time
- `create_event` (parameters: title, date, time, location): Creates an event.
- `list_events` (parameters: date_range): Lists events.
- `delete_event` (parameters: event_id): Deletes an event.
- `get_time` (parameters: location): Gets current time.
- `set_reminder` (parameters: message, datetime): Sets a reminder.

### Task Management
- `create_task` (parameters: title, due_date, priority): Creates a task.
- `update_task` (parameters: task_id, updates): Updates a task.
- `delete_task` (parameters: task_id): Deletes a task.
- `list_tasks` (parameters: filter): Lists tasks.

### Communication Platforms
- `send_slack_message` (parameters: channel, message): Sends to Slack.
- `send_discord_message` (parameters: channel, message): Sends to Discord.
- `post_twitter` (parameters: message): Posts a tweet.
- `post_linkedin` (parameters: message): Posts on LinkedIn.

### Data Handling
- `read_csv` (parameters: filepath): Reads CSV.
- `write_csv` (parameters: filepath, data): Writes CSV.
- `filter_csv` (parameters: filepath, condition): Filters CSV.
- `generate_report` (parameters: title, data): Generates PDF report.

### Media
- `play_music` (parameters: song_name): Plays music.
- `pause_music` (parameters: none): Pauses music.
- `stop_music` (parameters: none): Stops music.
- `play_video` (parameters: video_name): Plays video.
- `take_screenshot` (parameters: save_path): Takes screenshot.

### Utilities
- `calculate` (parameters: expression): Evaluates math.
- `translate` (parameters: text, target_language): Translates text.
- `unit_convert` (parameters: value, from_unit, to_unit): Converts units.
- `spell_check` (parameters: text): Checks spelling.
- `summarize_text` (parameters: text): Summarizes text.
- `generate_password` (parameters: length): Generates password.
- `scan_qr_code` (parameters: image_path): Scans QR code.

### AI & Content Generation
- `generate_text` (parameters: prompt): Generates text.
- `generate_image` (parameters: prompt, size): Generates image.
- `generate_code` (parameters: prompt, language): Generates code.
- `analyze_sentiment` (parameters: text): Analyzes sentiment.
- `chat_with_ai` (parameters: message): Chats with AI.

### System
- `shutdown_system` (parameters: none): Shuts down system.
- `restart_system` (parameters: none): Restarts system.
- `check_system_status` (parameters: none): Checks status.
- `list_running_processes` (parameters: none): Lists processes.
- `kill_process` (parameters: process_id): Kills a process.

Note: Not all operations are fully implemented in the code (e.g., some are demos or placeholders). Extend `operations_tool.py` for full functionality.

## Examples

- "Send an email to john@example.com about the meeting": Maps to `send_email`.
- "Calculate 15% tip on $85": Uses `calculate`.
- "Get the weather for San Francisco": Uses `get_weather` (personalized by user location).
- "Generate a strong password": Uses `generate_password`.

## Development

- Edit agents/tasks in `config/agents.yaml` and `config/tasks.yaml`.
- Add handlers in `tools/operations_tool.py` for new operations.
- Run tests with `uv run test`.

## Limitations

- Operations are simulated in some cases (e.g., email sending is a demo print).
- No real external integrations (e.g., actual email/SMS requires additional setup).
- LLM costs apply based on your API usage.

## Contributing

Fork the repo, make changes, and submit a PR. Ensure UV is used for dependency management.

## License

MIT (assumed; add a LICENSE file if needed).

