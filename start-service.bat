@echo off

echo Starting Email Listener...
start cmd /k "uv sync && uv run main.py"

echo Starting Server...
start cmd /k "uv sync && uv run uvicorn server:app --reload"

echo Starting Frontend...
start cmd /k "cd frontend && npm install && npm run dev"