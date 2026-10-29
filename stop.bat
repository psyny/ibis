@echo off
rem Stops the ibis containers. Your data is kept (use reset-db.bat to wipe it).
setlocal
cd /d "%~dp0"
call scripts\win\ensure-docker.bat || goto fail
docker compose down || goto fail
echo [ibis] Stopped. Data is kept.
exit /b 0

:fail
echo [ibis] Stop failed. See the messages above.
pause
exit /b 1
