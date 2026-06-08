$env:HTTP_PROXY='http://127.0.0.1:7897'
$env:HTTPS_PROXY='http://127.0.0.1:7897'
& ".\.venv\Scripts\python.exe" -m uvicorn src.api:app --host 0.0.0.0 --port 8000