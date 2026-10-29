@echo off
rem Usage:  run        start Redis + the product API + the frontend (http://localhost:3000/products)
rem         run test   start Redis + run the tests
cd /d "%~dp0"

rem --- make sure Docker Desktop is up ---
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready
echo Starting Docker Desktop...
start "" "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
:wait_docker
ping -n 4 127.0.0.1 >nul
docker info >nul 2>&1
if errorlevel 1 goto wait_docker
:docker_ready

rem --- start the redis container, creating it the first time ---
docker start redis >nul 2>&1 || docker run -d --name redis -p 6379:6379 redis >nul
echo Redis is running.

if /i "%~1"=="test" goto test

rem frontend gets its own window
start "frontend" /d "%~dp0my-app\my-app" cmd /k pnpm dev
echo Frontend starting at http://localhost:3000/products
.venv\Scripts\python -m uvicorn product_DB:app --reload
goto :eof

:test
.venv\Scripts\python -m pytest test_product_DB.py -q
