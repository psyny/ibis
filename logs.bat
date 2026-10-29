@echo off
rem Follows the logs (Ctrl+C to quit).
rem Usage: logs.bat               all services
rem        logs.bat backend-api   one service (backend-api, frontend, postgres)
setlocal
cd /d "%~dp0"
call scripts\win\ensure-docker.bat || exit /b 1
docker compose logs -f --tail 100 %*
