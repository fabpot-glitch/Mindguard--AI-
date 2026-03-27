@echo off
setlocal enabledelayedexpansion

:: MindGuard AI Deployment Script for Windows
:: Usage: deploy.bat [environment] [version]

set ENV=%1
if "%ENV%"=="" set ENV=staging
set VERSION=%2
if "%VERSION%"=="" set VERSION=latest

echo ========================================
echo MindGuard AI Deployment Script
echo ========================================
echo Environment: %ENV%
echo Version: %VERSION%
echo.

:: Check prerequisites
echo Checking prerequisites...
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Docker not found. Please install Docker Desktop.
    exit /b 1
)

where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose not found. Please install Docker Desktop.
    exit /b 1
)

:: Load environment variables
if exist ..\.env (
    echo Loading environment variables...
    for /f "tokens=*" %%a in (..\.env) do set %%a
) else (
    echo WARNING: .env file not found. Using default values.
)

:: Set deployment-specific variables
set COMPOSE_FILE=..\deployment\docker\docker-compose.yml
if "%ENV%"=="production" (
    set COMPOSE_FILE=..\deployment\docker\docker-compose.prod.yml
)

:: Create necessary directories
echo Creating required directories...
mkdir ..\logs 2>nul
mkdir ..\data 2>nul
mkdir ..\models\weights 2>nul
mkdir ..\backups 2>nul

:: Backup current state
echo Creating backup...
set BACKUP_FILE=..\backups\pre_deploy_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.zip
powershell -Command "Compress-Archive -Path ..\data, ..\logs, ..\models\weights -DestinationPath '%BACKUP_FILE%' -Force"
echo Backup created: %BACKUP_FILE%

:: Pull latest images
echo Pulling Docker images...
docker-compose -f %COMPOSE_FILE% pull

:: Stop current containers
echo Stopping current containers...
docker-compose -f %COMPOSE_FILE% down

:: Run database migrations
echo Running database migrations...
docker-compose -f %COMPOSE_FILE% run --rm backend python scripts/migrate_db.py
if %errorlevel% neq 0 (
    echo ERROR: Database migration failed. Rolling back...
    call rollback.bat %ENV%
    exit /b 1
)

:: Start new containers
echo Starting new containers...
docker-compose -f %COMPOSE_FILE% up -d

:: Wait for services to be ready
echo Waiting for services to be ready...
set /a COUNTER=0
:health_check_loop
timeout /t 5 /nobreak >nul
docker-compose -f %COMPOSE_FILE% ps | findstr "Up" >nul
if %errorlevel% equ 0 (
    echo All services are running.
) else (
    set /a COUNTER+=1
    if !COUNTER! lss 12 (
        echo Waiting for services... (!COUNTER!/12)
        goto health_check_loop
    ) else (
        echo ERROR: Services failed to start. Rolling back...
        call rollback.bat %ENV%
        exit /b 1
    )
)

:: Run health checks
echo Running health checks...
call health_check.bat %ENV%
if %errorlevel% neq 0 (
    echo ERROR: Health checks failed. Rolling back...
    call rollback.bat %ENV%
    exit /b 1
)

:: Clean up old images
echo Cleaning up old images...
docker image prune -f

echo.
echo ========================================
echo Deployment completed successfully!
echo Environment: %ENV%
echo Version: %VERSION%
echo ========================================

:: Send notification
powershell -Command "
    $Toast = New-Object -ComObject Windows.UI.Notifications.ToastNotificationManager;
    $Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);
    $TextNodes = $Template.GetElementsByTagName('text');
    $TextNodes.Item(0).AppendChild($Template.CreateTextNode('MindGuard AI Deployment')) > $null;
    $TextNodes.Item(1).AppendChild($Template.CreateTextNode('Deployment to %ENV% completed successfully!')) > $null;
    $Toast.CreateToastNotifier('MindGuard AI').Show($Template);
"

exit /b 0