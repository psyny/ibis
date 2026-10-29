@echo off
rem Builds and starts ibis (Postgres + backend API + frontend) in Docker, then opens the app.
rem Usage: start.bat [--no-browser]
setlocal
cd /d "%~dp0"
call scripts\win\ensure-docker.bat || goto fail
rem Answer Compose's one-time 'build with Bake?' prompt up front (it would hang a double-clicked window)
set COMPOSE_BAKE=true

echo [ibis] Building and starting containers (the first run takes a few minutes)...
rem --renew-anon-volumes refreshes the frontend's node_modules when packages change (database is kept)
docker compose up -d --build --renew-anon-volumes || goto fail

echo [ibis] Waiting for the API (database migrations run first)...
set /a TRIES=0
:wait_api
curl.exe -s -f -o nul http://localhost:8000/health && goto ready
set /a TRIES+=1
if %TRIES% geq 90 (
  echo [ibis] The API did not come up. Last backend logs:
  docker compose logs --tail 40 backend-api
  goto fail
)
ping -n 3 127.0.0.1 >nul
goto wait_api

:ready
echo.
echo [ibis] Running!
echo   App:      http://localhost:3000
echo   API docs: http://localhost:8000/docs
echo   The first sign-in creates the admin account.
echo   Stop with stop.bat. Logs with logs.bat.
if /i not "%~1"=="--no-browser" start "" http://localhost:3000
exit /b 0

:fail
echo.
echo [ibis] Start failed. See the messages above.
if /i not "%~1"=="--no-browser" pause
exit /b 1
