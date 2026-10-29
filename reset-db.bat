@echo off
rem Deletes ALL local ibis data (households, people, costs) and stops the containers.
rem The next start.bat begins with an empty database: the first sign-in creates a new admin.
setlocal
cd /d "%~dp0"
call scripts\win\ensure-docker.bat || goto fail

echo This deletes ALL local ibis data: households, people and costs.
set "CONFIRM="
set /p CONFIRM=Type RESET to continue:
if /i not "%CONFIRM%"=="RESET" (
  echo [ibis] Cancelled. Nothing was deleted.
  pause
  exit /b 0
)
docker compose down -v || goto fail
echo [ibis] Local data deleted. Run start.bat to start again with an empty database.
pause
exit /b 0

:fail
echo [ibis] Reset failed. See the messages above.
pause
exit /b 1
