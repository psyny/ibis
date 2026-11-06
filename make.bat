@echo off
rem Windows counterpart of the Makefile. Usage: make.bat <target> [argument]
setlocal
cd /d "%~dp0"

set "VENV=backend\venv"
set "PYBIN=%VENV%\Scripts\python.exe"
rem Answer Compose's one-time 'build with Bake?' prompt up front (it would hang the window)
set COMPOSE_BAKE=true

set "TARGET=%~1"
set "ARG=%~2"
if "%TARGET%"=="" set "TARGET=help"

if /i "%TARGET%"=="help"              goto :help
if /i "%TARGET%"=="up"                goto :up
if /i "%TARGET%"=="down"              goto :down
if /i "%TARGET%"=="status"            goto :status
if /i "%TARGET%"=="logs"              goto :logs
if /i "%TARGET%"=="reset-db"          goto :reset_db
if /i "%TARGET%"=="prod-local"        goto :prod_local
if /i "%TARGET%"=="prod-local-down"   goto :prod_local_down
if /i "%TARGET%"=="be-install"        goto :be_install
if /i "%TARGET%"=="be-tests"          goto :be_tests
if /i "%TARGET%"=="be-tests-postgres" goto :be_tests_postgres
if /i "%TARGET%"=="be-migration"      goto :be_migration
if /i "%TARGET%"=="fe-install"        goto :fe_install
if /i "%TARGET%"=="fe-build"          goto :fe_build
if /i "%TARGET%"=="fe-tests"          goto :fe_tests

echo Unknown target: %TARGET%
echo.
call :help
exit /b 1

:help
echo Docker (local app: Postgres + API + frontend)
echo   make.bat up [--no-browser]    -^> build and start, wait until ready, open http://localhost:3000
echo   make.bat down                 -^> stop (data is kept)
echo   make.bat status               -^> show running containers
echo   make.bat logs [service]       -^> follow logs (backend-api, frontend, postgres)
echo   make.bat reset-db             -^> delete ALL local data (asks to type RESET)
echo   make.bat prod-local           -^> production-like build on http://localhost:8080
echo   make.bat prod-local-down      -^> stop the production-like build
echo Backend
echo   make.bat be-install           -^> create backend\venv and install dependencies
echo   make.bat be-tests [path]      -^> unit + API tests on SQLite, no Docker (e.g. unit/test_settlement.py)
echo   make.bat be-tests-postgres    -^> tests against the Docker Postgres test DB
echo   make.bat be-migration "msg"   -^> autogenerate a migration (Docker Postgres must be up)
echo Frontend
echo   make.bat fe-install           -^> npm install
echo   make.bat fe-build             -^> typecheck and build
echo   make.bat fe-tests             -^> unit tests
echo.
echo The first sign-in on an empty database creates the admin account.
exit /b 0

rem ---- Docker ----

:up
call :ensure_docker || goto :fail
echo [ibis] Building and starting containers (the first run takes a few minutes)...
rem --renew-anon-volumes refreshes the frontend's node_modules when packages change (database is kept)
docker compose up -d --build --renew-anon-volumes || goto :fail
echo [ibis] Waiting for the API (database migrations run first)...
call :wait_api docker-compose.yml || goto :fail
echo.
echo [ibis] Running!
echo   App:      http://localhost:3000
echo   API docs: http://localhost:8000/docs
echo   The first sign-in creates the admin account.
echo   Stop with "make.bat down". Logs with "make.bat logs".
if /i not "%ARG%"=="--no-browser" start "" http://localhost:3000
exit /b 0

:down
call :ensure_docker || goto :fail
docker compose down || goto :fail
echo [ibis] Stopped. Data is kept.
exit /b 0

:status
call :ensure_docker || goto :fail
docker compose ps
exit /b %ERRORLEVEL%

:logs
call :ensure_docker || goto :fail
docker compose logs -f --tail 100 %ARG%
exit /b %ERRORLEVEL%

:reset_db
call :ensure_docker || goto :fail
echo This deletes ALL local ibis data: households, people and costs.
set "CONFIRM="
set /p CONFIRM=Type RESET to continue:
if /i not "%CONFIRM%"=="RESET" (
  echo [ibis] Cancelled. Nothing was deleted.
  exit /b 0
)
docker compose down -v || goto :fail
echo [ibis] Local data deleted. Run "make.bat up" to start again with an empty database.
exit /b 0

:prod_local
call :ensure_docker || goto :fail
rem Same API port as the dev stack: stop that first
docker compose down >nul 2>nul
echo [ibis] Building and starting the production-like stack...
docker compose -f docker-compose.prod-local.yml up -d --build || goto :fail
call :wait_api docker-compose.prod-local.yml || goto :fail
echo [ibis] Production-like app: http://localhost:8080   (stop with "make.bat prod-local-down")
start "" http://localhost:8080
exit /b 0

:prod_local_down
call :ensure_docker || goto :fail
docker compose -f docker-compose.prod-local.yml down || goto :fail
echo [ibis] Production-like stack stopped.
exit /b 0

rem ---- Backend ----

:be_install
if not exist "%PYBIN%" (
  where py >nul 2>nul && (py -3 -m venv %VENV%) || (python -m venv %VENV%)
)
"%PYBIN%" -m pip install --upgrade pip || goto :fail
"%PYBIN%" -m pip install -e "backend[dev]"
exit /b %ERRORLEVEL%

:be_tests
call :check_venv || exit /b 1
pushd backend
venv\Scripts\python.exe -m pytest ibis/tests/%ARG% -v
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:be_tests_postgres
call :check_venv || exit /b 1
pushd backend
set "TEST_DATABASE_URL=postgresql://ibis:ibis@localhost:5432/ibis_test"
venv\Scripts\python.exe -m pytest ibis/tests -v
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:be_migration
call :check_venv || exit /b 1
if "%ARG%"=="" (
  echo Usage: make.bat be-migration "describe the change"
  exit /b 1
)
pushd backend\ibis
set "DATABASE_URL=postgresql://ibis:ibis@localhost:5432/ibis"
..\venv\Scripts\alembic.exe revision --autogenerate -m "%ARG%"
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

rem ---- Frontend ----

:fe_install
pushd frontend
call npm install
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:fe_build
pushd frontend
call npm run build
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:fe_tests
pushd frontend
call npx vitest run
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

rem ---- Helpers ----

:check_venv
if exist "%PYBIN%" exit /b 0
echo backend\venv not found. Run "make.bat be-install" first.
exit /b 1

rem Waits until the API answers /health. %1 = compose file (for logs on failure)
:wait_api
set /a TRIES=0
:wait_api_loop
curl.exe -s -f -o nul http://localhost:8000/health && exit /b 0
set /a TRIES+=1
if %TRIES% geq 90 (
  echo [ibis] The API did not come up. Last backend logs:
  docker compose -f %1 logs --tail 40 backend-api
  exit /b 1
)
ping -n 3 127.0.0.1 >nul
goto :wait_api_loop

rem Makes sure the docker CLI is reachable and the Docker engine is running (starts Docker Desktop if needed)
:ensure_docker
where docker >nul 2>nul
if errorlevel 1 (
  rem A fresh install isn't on PATH until a new terminal is opened: look in the usual places
  if exist "%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe" set "PATH=%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin;%PATH%"
  if exist "%ProgramFiles%\Docker\Docker\resources\bin\docker.exe" set "PATH=%ProgramFiles%\Docker\Docker\resources\bin;%PATH%"
)
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
if %IBIS_TRIES% lss 60 goto :wait_engine
echo [ibis] Docker Desktop did not start within 3 minutes. Open it, wait for "Engine running", then try again.
exit /b 1

:fail
echo.
echo [ibis] %TARGET% failed. See the messages above.
exit /b 1
