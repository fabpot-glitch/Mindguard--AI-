@echo off
setlocal enabledelayedexpansion

:: MindGuard AI Health Check Script for Windows
:: Usage: health_check.bat [environment]

set ENV=%1
if "%ENV%"=="" set ENV=staging

echo ========================================
echo MindGuard AI Health Check
echo ========================================
echo Environment: %ENV%
echo.

set COMPOSE_FILE=..\deployment\docker\docker-compose.yml
if "%ENV%"=="production" (
    set COMPOSE_FILE=..\deployment\docker\docker-compose.prod.yml
)

:: Check if containers are running
echo Checking container status...
docker-compose -f %COMPOSE_FILE% ps

:: Get container names
for /f "tokens=1" %%i in ('docker-compose -f %COMPOSE_FILE% ps --services') do (
    set SERVICE=%%i
    set STATUS=unknown
    
    for /f "tokens=3" %%j in ('docker-compose -f %COMPOSE_FILE% ps %%i ^| findstr /C:"%%i"') do (
        set STATUS=%%j
    )
    
    if "!STATUS!"=="Up" (
        echo [OK] !SERVICE! is running
    ) else (
        echo [FAIL] !SERVICE! is not running (Status: !STATUS!)
        set FAILED=1
    )
)

echo.

:: Check backend health endpoint
echo Checking backend health...
for /f "tokens=*" %%i in ('docker-compose -f %COMPOSE_FILE% ps -q backend 2^>nul') do set BACKEND_ID=%%i
if defined BACKEND_ID (
    docker exec %BACKEND_ID% curl -s -f http://localhost:8000/api/v1/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Backend health check passed
    ) else (
        echo [FAIL] Backend health check failed
        set FAILED=1
    )
) else (
    echo [WARN] Backend service not found
)

:: Check frontend
echo Checking frontend...
for /f "tokens=*" %%i in ('docker-compose -f %COMPOSE_FILE% ps -q frontend 2^>nul') do set FRONTEND_ID=%%i
if defined FRONTEND_ID (
    docker exec %FRONTEND_ID% wget -q --spider http://localhost 2>nul
    if !errorlevel! equ 0 (
        echo [OK] Frontend is accessible
    ) else (
        echo [FAIL] Frontend check failed
        set FAILED=1
    )
) else (
    echo [WARN] Frontend service not found
)

:: Check database
echo Checking database...
for /f "tokens=*" %%i in ('docker-compose -f %COMPOSE_FILE% ps -q postgres 2^>nul') do set POSTGRES_ID=%%i
if defined POSTGRES_ID (
    docker exec %POSTGRES_ID% pg_isready -U mindguard -d mindguard >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Database is ready
    ) else (
        echo [FAIL] Database check failed
        set FAILED=1
    )
) else (
    echo [WARN] Database service not found
)

:: Check Redis
echo Checking Redis...
for /f "tokens=*" %%i in ('docker-compose -f %COMPOSE_FILE% ps -q redis 2^>nul') do set REDIS_ID=%%i
if defined REDIS_ID (
    docker exec %REDIS_ID% redis-cli ping | findstr "PONG" >nul
    if !errorlevel! equ 0 (
        echo [OK] Redis is responding
    ) else (
        echo [FAIL] Redis check failed
        set FAILED=1
    )
) else (
    echo [WARN] Redis service not found
)

:: Check disk space
echo Checking disk space...
for /f "tokens=3" %%i in ('wmic logicaldisk where DeviceID^="C:" get FreeSpace /format:value') do set FREE_SPACE=%%i
set /a FREE_SPACE_GB=!FREE_SPACE:~0,-9!
if !FREE_SPACE_GB! lss 10 (
    echo [WARN] Low disk space: !FREE_SPACE_GB!GB free
) else (
    echo [OK] Disk space: !FREE_SPACE_GB!GB free
)

:: Check memory usage
echo Checking memory usage...
for /f "skip=1" %%i in ('wmic os get TotalVisibleMemorySize /value') do set TOTAL_MEM=%%i
for /f "skip=1" %%i in ('wmic os get FreePhysicalMemory /value') do set FREE_MEM=%%i
set TOTAL_MEM=!TOTAL_MEM:*=!
set FREE_MEM=!FREE_MEM:*=!
set /a USED_MEM_PERCENT=(TOTAL_MEM - FREE_MEM) * 100 / TOTAL_MEM
if !USED_MEM_PERCENT! gtr 90 (
    echo [WARN] High memory usage: !USED_MEM_PERCENT!%%
) else (
    echo [OK] Memory usage: !USED_MEM_PERCENT!%%
)

:: Check CPU usage
echo Checking CPU usage...
for /f "skip=1" %%i in ('wmic cpu get loadpercentage /value') do set CPU_USAGE=%%i
set CPU_USAGE=!CPU_USAGE:*=!
if !CPU_USAGE! gtr 80 (
    echo [WARN] High CPU usage: !CPU_USAGE!%%
) else (
    echo [OK] CPU usage: !CPU_USAGE!%%
)

echo.

:: Generate health report
set REPORT_FILE=..\logs\health_report_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%.txt
echo MindGuard AI Health Report > %REPORT_FILE%
echo Generated: %DATE% %TIME% >> %REPORT_FILE%
echo Environment: %ENV% >> %REPORT_FILE%
echo. >> %REPORT_FILE%

docker-compose -f %COMPOSE_FILE% ps >> %REPORT_FILE% 2>&1
echo. >> %REPORT_FILE%
docker stats --no-stream >> %REPORT_FILE% 2>&1

echo Health report saved to: %REPORT_FILE%

if defined FAILED (
    echo [FAIL] Health check failed - some services are not healthy
    exit /b 1
) else (
    echo [OK] All health checks passed
    exit /b 0
)