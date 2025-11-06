@echo off
cd /d D:\python\PROJETO2\Checklist_Energy
call .venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
