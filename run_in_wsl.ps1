# EU Climate WSL Runner
# This script runs the EU Climate project in WSL where GDAL/Rasterio work properly

Write-Host "=== EU Climate WSL Runner ===" -ForegroundColor Green

# Change to project directory and activate WSL environment
$projectPath = "/mnt/c/Users/ykoen/Python/Semester 6/EU Geolytics/eu-data"
$activateEnv = "source ~/eu-climate-wsl/bin/activate"

# Function to run commands in WSL
function Run-InWSL {
    param($command)
    $fullCommand = "cd '$projectPath' && $activateEnv && $command"
    Write-Host "Running: $command" -ForegroundColor Yellow
    wsl bash -c "$fullCommand"
}

# Check what the user wants to do
param(
    [string]$Action = "demo"
)

switch ($Action.ToLower()) {
    "demo" {
        Write-Host "Running web export demo..." -ForegroundColor Cyan
        Run-InWSL "python3 run_eu_climate.py demo"
    }
    "main" {
        Write-Host "Running main analysis..." -ForegroundColor Cyan
        Run-InWSL "python3 run_eu_climate.py main"
    }
    "test" {
        Write-Host "Testing WSL setup..." -ForegroundColor Cyan
        Run-InWSL "python3 -c 'import rasterio, geopandas; print(\"All packages working!\")'"
    }
    "shell" {
        Write-Host "Opening WSL shell in project directory..." -ForegroundColor Cyan
        wsl bash -c "cd '$projectPath' && $activateEnv && bash"
    }
    default {
        Write-Host "Usage: .\run_in_wsl.ps1 [demo|main|test|shell]" -ForegroundColor Red
        Write-Host "  demo  - Run web export demo" -ForegroundColor White
        Write-Host "  main  - Run main climate analysis" -ForegroundColor White
        Write-Host "  test  - Test if packages work" -ForegroundColor White
        Write-Host "  shell - Open WSL shell in project directory" -ForegroundColor White
    }
} 