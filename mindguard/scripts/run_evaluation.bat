@echo off
setlocal enabledelayedexpansion

:: MindGuard AI Evaluation Script for Windows
:: Usage: run_evaluation.bat [model] [data] [options]

echo ========================================
echo MindGuard AI Evaluation Script
echo ========================================

:: Default values
set MODEL=models/weights/mindguard_best.pt
set DATA=data/processed/deap_processed.npy
set OUTPUT=evaluation_results
set BATCH_SIZE=32
set DEVICE=cpu
set PLOTS=1

:: Parse arguments
:parse_args
if "%1"=="" goto :start_evaluation
if "%1"=="--model" (
    set MODEL=%2
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
if "%1"=="--output" (
    set OUTPUT=%2
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
if "%1"=="--device" (
    set DEVICE=%2
    shift
    shift
    goto :parse_args
)
if "%1"=="--no-plots" (
    set PLOTS=0
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
echo Usage: run_evaluation.bat [options]
echo.
echo Options:
echo   --model FILE      Model checkpoint file (default: models/weights/mindguard_best.pt)
echo   --data FILE       Test data file (default: data/processed/deap_processed.npy)
echo   --output DIR      Output directory for results (default: evaluation_results)
echo   --batch-size N    Batch size (default: 32)
echo   --device DEVICE   Device to use (cpu/cuda) (default: cpu)
echo   --no-plots        Disable plot generation
echo   --help            Show this help message
echo.
exit /b 0

:start_evaluation
echo.
echo Configuration:
echo   Model: %MODEL%
echo   Data: %DATA%
echo   Output: %OUTPUT%
echo   Batch Size: %BATCH_SIZE%
echo   Device: %DEVICE%
echo   Generate Plots: %PLOTS%
echo.

:: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.8 or later.
    exit /b 1
)

:: Check if model exists
if not exist "%MODEL%" (
    echo ERROR: Model file not found: %MODEL%
    exit /b 1
)

:: Check if data exists
if not exist "%DATA%" (
    echo ERROR: Data file not found: %DATA%
    exit /b 1
)

:: Create output directory
echo Creating output directory...
mkdir "%OUTPUT%" 2>nul

:: Set PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%CD%

:: Build command
set CMD=python -m models.evaluate
set CMD=%CMD% --model "%MODEL%"
set CMD=%CMD% --data "%DATA%"
set CMD=%CMD% --output "%OUTPUT%"
set CMD=%CMD% --batch-size %BATCH_SIZE%
set CMD=%CMD% --device %DEVICE%
if %PLOTS%==0 set CMD=%CMD% --no-plots

:: Log start
echo %DATE% %TIME% - Starting evaluation... >> logs\evaluation.log
echo Command: %CMD% >> logs\evaluation.log

:: Run evaluation
echo.
echo Starting evaluation...
echo.

%CMD%

:: Check result
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Evaluation completed successfully!
    echo ========================================
    
    :: Log success
    echo %DATE% %TIME% - Evaluation completed successfully >> logs\evaluation.log
    
    :: Show results
    if exist "%OUTPUT%\evaluation_report.json" (
        echo.
        echo Results saved to: %OUTPUT%\evaluation_report.json
        echo.
        
        :: Display key metrics
        echo Key Metrics:
        python -c "
import json
with open(r'%OUTPUT%\evaluation_report.json') as f:
    data = json.load(f)
print(f'  Overall MAE: {data[\"metrics\"][\"overall_mae\"]:.4f}')
print(f'  Overall RMSE: {data[\"metrics\"][\"overall_rmse\"]:.4f}')
print(f'  Overall R²: {data[\"metrics\"][\"overall_r2\"]:.4f}')
print(f'  Fatigue MAE: {data[\"metrics\"][\"fatigue_mae\"]:.4f}')
print(f'  Stress MAE: {data[\"metrics\"][\"stress_mae\"]:.4f}')
print(f'  Attention MAE: {data[\"metrics\"][\"attention_mae\"]:.4f}')
print(f'  Cognitive Load MAE: {data[\"metrics\"][\"cognitive_load_mae\"]:.4f}')
        "
    )
) else (
    echo.
    echo ========================================
    echo ERROR: Evaluation failed!
    echo ========================================
    
    :: Log failure
    echo %DATE% %TIME% - Evaluation failed with error %errorlevel% >> logs\evaluation.log
    
    exit /b %errorlevel%
)

exit /b 0