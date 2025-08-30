# AI Agent Demo

This project is a demonstration of an AI assistant built using [CrewAI](https://github.com/crewAIInc/crewAI), a framework for orchestrating AI agents. The assistant processes natural language user queries, analyzes them against a predefined set of operations and user preferences, creates an execution plan, and performs tasks such as file management, calculations, system operations, web interactions, and more. It leverages large language models (LLMs) like Google's Gemini (default) or Groq's models for reasoning and planning.

The core functionality includes:

- **Query Analysis**: An agent reads user preferences (e.g., name, location, interests) and available operations to map queries to executable steps.
- **Operation Execution**: Supports a wide range of operations (detailed below) via a centralized tool.
- **UI Mode**: A desktop app built with Electron for interactive queries.
- **Personalization**: Incorporates user details from `knowledge/user_preference.txt` (e.g., default location as San Francisco).
- **Extensibility**: Custom tools for file management, operations, and system tasks.

This project is ideal for exploring AI agents in automation, task management, and natural language interfaces. It's structured as a Python package with a CrewAI crew, agents, tasks, and tools.

## Prerequisites

- Python 3.10 to 3.13 (as specified in `pyproject.toml`).
- Node.js (LTS, e.g., v20+) and npm for the Electron UI (download from https://nodejs.org/).
- A compatible LLM API key (e.g., from Google Gemini or Groq). Sign up at:
  - [Google AI Studio](https://aistudio.google.com/) for Gemini.
  - [Groq](https://groq.com/) for alternative models like Mixtral.

## Installation

This project uses [UV](https://github.com/astral-sh/uv), a fast Python package installer, resolver, and virtual environment manager (similar to Poetry or Pipenv but faster). UV handles dependencies, virtual environments, and scripts defined in `pyproject.toml`.

### Step 1: Install UV

UV can be installed via a simple script. Choose one of the methods below:

- **Via curl (recommended for Unix-like systems)**:
  curl -LsSf https://astral.sh/uv/install.sh | sh
- **Via Homebrew (macOS)**:
  brew install uv
- **Via pip (if you already have Python)**:
  pip install uv
- For Windows or other platforms, see the [official UV installation guide](https://docs.astral.sh/uv/getting-started/installation/).

After installation, verify UV:
uv --version

### Step 2: Set Up the Project

Clone or download the project repository, then navigate to the project directory:
cd parthdhengle-crew-ai-trial
Create and activate a virtual environment, then install dependencies:
uv venv # Creates a virtual environment in .venv
source .venv/bin/activate # Activate on Unix-like systems (use .venv\Scripts\activate on Windows)
uv sync # Installs dependencies from pyproject.toml, including crewai[tools]

### Step 3: Set Up Electron UI

cd src/agent_demo/electron_app
npm install

### Step 4: Configure Environment Variables

Create a `.env` file in the project root to store your LLM API key. The project uses Gemini by default, but you can switch to Groq by updating `src/agent_demo/crew.py`.

Example `.env` content:
GEMINI_API_KEY=your-gemini-api-key-here
Alternatively, for Groq:
GROQ_API_KEY=your-groq-api-key-here
The code loads these via `os.getenv("GEMINI_API_KEY")` or similar. Ensure the `.env` is not committed to version control (add it to `.gitignore`).

### Step 5: Prepare Knowledge Files

The project relies on two knowledge files (already included but customizable):

- `knowledge/user_preference.txt`: User details (e.g., name: John Doe, location: San Francisco, interests: AI Agents).
- `knowledge/operations.txt`: List of supported operations (see below).

If these files are missing, the project will error out—ensure they exist.

## Running the Project

UV integrates with the scripts defined in `pyproject.toml` (e.g., `crewai run`, `train`, etc.). Activate your virtual environment first.

### UI Mode (Default)

Launch the Electron desktop app (starts the backend server automatically):
uv run ui

- The app window will open.
- Enter queries in the input field and click "Send Query".
- Responses (execution plan and results) will display below.

### Single Query Mode (CLI, if needed)

Pass a query as a command-line argument:
uv run run_crew "Create a file called notes.txt with content: Hello World"

### Other Commands

- **Train**: Placeholder for future training (not implemented):
  uv run train
- **Replay**: Placeholder for replaying past executions:
  uv run replay
- **Test**: Runs predefined test queries:
  uv run test

The execution flow:

1. Analyzes the query using the CrewAI agent.
2. Generates `execution_plan.json` if operations match.
3. Executes operations sequentially and reports results.

## Available Operations

[Unchanged from original...]

## Examples

[Unchanged from original...]

## Development

- Edit agents/tasks in `config/agents.yaml` and `config/tasks.yaml`.
- Add handlers in `tools/operations_tool.py` for new operations.
- Run tests with `uv run test`.
- For UI development: Edit files in `src/agent_demo/electron_app/`. Test with `cd src/agent_demo/electron_app && npm start` (ensure backend is running).

## Limitations

[Unchanged from original...]

## Contributing

[Unchanged from original...]

## License

[Unchanged from original...]
