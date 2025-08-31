## Running the Project

UV integrates with the scripts defined in `pyproject.toml`. Activate your virtual environment first.

### Default Mode (UI + Listener)

Launch the full app (backend server, Electron UI, and text selection listener for MVP popup):
uv run

- The Electron window opens for queries.
- Select text anywhere (e.g., browser, PDF) to see "Ask AI" popup—click to pre-fill the UI input.

### Single Query Mode (CLI)

Pass a query as a command-line argument:
uv run "Create a file called notes.txt with content: Hello World"

### Other Commands

- **Train**: uv run train
- **Replay**: uv run replay
- **Test**: uv run test
