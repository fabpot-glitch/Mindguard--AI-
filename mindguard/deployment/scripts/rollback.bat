@echo off
setlocal enabledelayedexpansion

:: MindGuard AI Rollback Script for Windows
:: Usage: rollback.bat [environment] [backup_file]

set ENV=%1
if "%ENV%"=="" set ENV=staging
set BACKUP_FILE=%2

echo ========================================
echo MindGuard AI Rollback Script
echo ========================================
echo Environment: %ENV%
if defined BACKUP_FILE echo Backup File: %BACKUP_FILE%
echo.

set COMPOSE_FILE=..\deployment\docker\docker-compose.yml
if "%ENV%"=="production" (
    set COMPOSE_FILE=..\deployment\docker\docker-compose.prod.yml
)

:: Find latest backup if not specified
if not defined BACKUP_FILE (
    echo Finding latest backup...
    for /f "delims=" %%i in ('dir ..\backups\*.zip /b /o-d 2^>nul') do (
        set BACKUP_FILE=..\backups\%%i
        goto :found_backup
    )
    echo No backup files found.
    exit /b 1
)
:found_backup

if not exist "%BACKUP_FILE%" (
    echo ERROR: Backup file not found: %BACKUP_FILE%
    exit /b 1
)

echo Using backup: %BACKUP_FILE%

:: Stop current containers
echo Stopping current containers...
docker-compose -f %COMPOSE_FILE% down

:: Restore from backup
echo Restoring from backup...
powershell -Command "Expand-Archive -Path '%BACKUP_FILE%' -DestinationPath '..\' -Force"
if %errorlevel% neq 0 (
    echo ERROR: Failed to restore backup
    exit /b 1
)

:: Start previous version
echo Starting previous version...
docker-compose -f %COMPOSE_FILE% up -d

:: Wait for services to be ready
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

:: Verify rollback
echo Verifying rollback...
call health_check.bat %ENV%
if %errorlevel% neq 0 (
    echo WARNING: Health check failed after rollback
)

:: Log rollback
set LOG_FILE=..\logs\rollback_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%.log
echo Rollback performed at %DATE% %TIME% > %LOG_FILE%
echo Environment: %ENV% >> %LOG_FILE%
echo Backup used: %BACKUP_FILE% >> %LOG_FILE%
echo Status: Completed >> %LOG_FILE%

echo.
echo ========================================
echo Rollback completed!
echo Environment: %ENV%
echo Backup restored: %BACKUP_FILE%
echo Log saved to: %LOG_FILE%
echo ========================================

:: Send notification
powershell -Command "
    $Toast = New-Object -ComObject Windows.UI.Notifications.ToastNotificationManager;
    $Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);
    $TextNodes = $Template.GetElementsByTagName('text');
    $TextNodes.Item(0).AppendChild($Template.CreateTextNode('MindGuard AI Rollback')) > $null;
    $TextNodes.Item(1).AppendChild($Template.CreateTextNode('Rollback to %ENV% completed successfully!')) > $null;
    $Toast.CreateToastNotifier('MindGuard AI').Show($Template);
"

exit /b 0