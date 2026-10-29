@echo off
rem Runs the production-like build (nginx frontend, production settings), close to what Railway runs.
rem Usage: prod-local.bat         start on http://localhost:8080 (stops the dev stack first: same API port)
rem        prod-local.bat stop    stop it (data kept)
setlocal
cd /d "%~dp0"
call scripts\win\ensure-docker.bat || goto fail
rem Answer Compose's one-time 'build with Bake?' prompt up front (it would hang a double-clicked window)
set COMPOSE_BAKE=true

if /i "%~1"=="stop" (
  docker compose -f docker-compose.prod-local.yml down || goto fail
  echo [ibis] Production-like stack stopped.
  exit /b 0
)

docker compose down >nul 2>nul
echo [ibis] Building and starting the production-like stack...
docker compose -f docker-compose.prod-local.yml up -d --build || goto fail

set /a TRIES=0
:wait_api
curl.exe -s -f -o nul http://localhost:8000/health && goto ready
set /a TRIES+=1
if %TRIES% geq 90 (
  docker compose -f docker-compose.prod-local.yml logs --tail 40 backend-api
  goto fail
)
ping -n 3 127.0.0.1 >nul
goto wait_api

:ready
echo [ibis] Production-like app: http://localhost:8080   (stop with: prod-local.bat stop)
start "" http://localhost:8080
exit /b 0

:fail
echo [ibis] Failed. See the messages above.
pause
exit /b 1
