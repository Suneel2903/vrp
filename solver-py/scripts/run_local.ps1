w$env:PYTHONPATH = ".."
..\.venv\Scripts\python -m uvicorn routeopt.api:app --reload --port 8001
