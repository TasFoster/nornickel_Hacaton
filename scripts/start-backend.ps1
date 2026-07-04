# Запуск backend (Django + DRF) на http://localhost:8000
# Требуется: запущенный Neo4j (start-neo4j.ps1) и заполненный .env в корне репозитория.
Set-Location "$PSScriptRoot\..\backend"
$env:PYTHONIOENCODING = "utf-8"
& ".\.venv\Scripts\python.exe" manage.py runserver 8000
