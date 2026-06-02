@echo off

echo Starting Email Listener...
start cmd /k "uv sync && uv run main.py"

echo Starting Server...
start cmd /k "uv sync && uv run uvicorn server:app --reload"