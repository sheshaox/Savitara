@echo off
cd /d d:\SAVI\Savitara\backend
set PYTHONPATH=%CD%
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
