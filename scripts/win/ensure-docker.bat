@echo off
rem Shared helper for the ibis .bat files (call it, don't run it directly).
rem Makes sure the docker CLI is reachable and the Docker engine is running.
rem Exits with 1 (after printing why) if Docker can't be used.

where docker >nul 2>nul
if not errorlevel 1 goto have_cli
rem A fresh install isn't on PATH until a new terminal is opened: look in the usual places.
if exist "%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe" set "PATH=%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin;%PATH%"
if exist "%ProgramFiles%\Docker\Docker\resources\bin\docker.exe" set "PATH=%ProgramFiles%\Docker\Docker\resources\bin;%PATH%"
:have_cli
where docker >nul 2>nul
if errorlevel 1 (
  echo [ibis] Docker was not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/
  exit /b 1
)

docker info >nul 2>nul
if not errorlevel 1 exit /b 0

echo [ibis] Docker Desktop is not running. Starting it...
set "IBIS_DD="
if exist "%LOCALAPPDATA%\Programs\DockerDesktop\frontend\Docker Desktop.exe" set "IBIS_DD=%LOCALAPPDATA%\Programs\DockerDesktop\frontend\Docker Desktop.exe"
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" set "IBIS_DD=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not defined IBIS_DD (
  echo [ibis] Could not find Docker Desktop. Start it from the Start menu, then try again.
  exit /b 1
)
start "" "%IBIS_DD%"

set /a IBIS_TRIES=0
:wait_engine
ping -n 3 127.0.0.1 >nul
docker info >nul 2>nul
if not errorlevel 1 (
  echo [ibis] Docker is running.
  exit /b 0
)
set /a IBIS_TRIES+=1
if %IBIS_TRIES% lss 60 goto wait_engine
echo [ibis] Docker Desktop did not start within 3 minutes. Open it, wait for "Engine running", then try again.
exit /b 1
