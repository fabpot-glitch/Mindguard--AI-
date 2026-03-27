@echo off
setlocal enabledelayedexpansion

:: MindGuard AI Training Script for Windows
:: Usage: run_training.bat [config] [data] [options]

echo ========================================
echo MindGuard AI Training Script
echo ========================================

:: Default values
set CONFIG=configs/training_config.yaml
set DATA=data/processed/deap_processed.npy
set EPOCHS=100
set BATCH_SIZE=32
set LR=0.001
set DEVICE=cpu
set WANDB=0

:: Parse arguments
:parse_args
if "%1"=="" goto :start_training
if "%1"=="--config" (
    set CONFIG=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--data" (
    set DATA=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--epochs" (
    set EPOCHS=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--batch-size" (
    set BATCH_SIZE=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--lr" (
    set LR=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--device" (
    set DEVICE=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--wandb" (
    set WANDB=1
    shift
    goto :parse_args
)
if "%1"=="--help" (
    goto :show_help
)
echo Unknown argument: %1
exit /b 1

:show_help
echo.
echo Usage: run_training.bat [options]
echo.
echo Options:
echo   --config FILE     Training configuration file (default: configs/training_config.yaml)
echo   --data FILE       Training data file (default: data/processed/deap_processed.npy)
echo   --epochs N        Number of training epochs (default: 100)
echo   --batch-size N    Batch size (default: 32)
echo   --lr VALUE        Learning rate (default: 0.001)
echo   --device DEVICE   Device to use (cpu/cuda) (default: cpu)
echo   --wandb           Enable Weights & Biases logging
echo   --help            Show this help message
echo.
exit /b 0

:start_training
echo.
echo Configuration:
echo   Config: %CONFIG%
echo   Data: %DATA%
echo   Epochs: %EPOCHS%
echo   Batch Size: %BATCH_SIZE%
echo   Learning Rate: %LR%
echo   Device: %DEVICE%
echo   WandB: %WANDB%
echo.

:: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.8 or later.
    exit /b 1
)

:: Check if config exists
if not exist "%CONFIG%" (
    echo WARNING: Config file not found: %CONFIG%
    echo Using default configuration.
    set CONFIG=
)

:: Check if data exists
if not exist "%DATA%" (
    echo ERROR: Data file not found: %DATA%
    exit /b 1
)

:: Create directories
echo Creating directories...
mkdir logs 2>nul
mkdir models\weights 2>nul

:: Set PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%CD%

:: Build command
set CMD=python -m models.train
if defined CONFIG set CMD=%CMD% --config "%CONFIG%"
set CMD=%CMD% --data "%DATA%"
set CMD=%CMD% --epochs %EPOCHS%
set CMD=%CMD% --batch-size %BATCH_SIZE%
set CMD=%CMD% --lr %LR%
set CMD=%CMD% --device %DEVICE%
if %WANDB%==1 set CMD=%CMD% --wandb

:: Log start
echo %DATE% %TIME% - Starting training... >> logs\training.log
echo Command: %CMD% >> logs\training.log

:: Run training
echo.
echo Starting training...
echo.

%CMD%

:: Check result
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Training completed successfully!
    echo ========================================
    
    :: Log success
    echo %DATE% %TIME% - Training completed successfully >> logs\training.log
    
    :: Find latest model
    for /f "delims=" %%i in ('dir models\weights\*.pt /b /o-d 2^>nul') do (
        set LATEST_MODEL=%%i
        goto :found_model
    )
    :found_model
    if defined LATEST_MODEL (
        echo Latest model: models\weights\!LATEST_MODEL!
    )
) else (
    echo.
    echo ========================================
    echo ERROR: Training failed!
    echo ========================================
    
    :: Log failure
    echo %DATE% %TIME% - Training failed with error %errorlevel% >> logs\training.log
    
    exit /b %errorlevel%
)

:: Create symlink to latest model (optional)
if defined LATEST_MODEL (
    if exist models\weights\mindguard_latest.pt del models\weights\mindguard_latest.pt
    mklink models\weights\mindguard_latest.pt models\weights\!LATEST_MODEL! >nul 2>&1
)

exit /b 0