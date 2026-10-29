@echo off
rem Shows which ibis containers are running.
setlocal
cd /d "%~dp0"
call scripts\win\ensure-docker.bat || exit /b 1
docker compose ps
