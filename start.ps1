# Startup script for Spotify Agent Service
# Kills existing processes and starts backend server

Write-Host "🚀 Starting Spotify Agent Service..." -ForegroundColor Cyan
Write-Host ""

# Function to kill process on a specific port
function Kill-ProcessOnPort {
    param([int]$Port)
    
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                $processId = $conn.OwningProcess
                if ($processId) {
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "Killing process $($process.ProcessName) (PID: $processId) on port $Port..." -ForegroundColor Yellow
                        try {
                            Stop-Process -Id $processId -Force -ErrorAction Stop
                            Write-Host "✓ Process killed successfully" -ForegroundColor Green
                        } catch {
                            Write-Host "⚠ Failed to kill process: $_" -ForegroundColor Red
                        }
                    }
                }
            }
        } else {
            Write-Host "No process found on port $Port" -ForegroundColor Gray
        }
    } catch {
        Write-Host "Error checking port $Port : $_" -ForegroundColor Red
    }
}

# Kill existing processes
Write-Host "Cleaning up existing processes..." -ForegroundColor Cyan
Kill-ProcessOnPort -Port 8000
Start-Sleep -Seconds 1
Write-Host ""

# Check if Python is installed
Write-Host "Checking dependencies..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python." -ForegroundColor Red
    exit 1
}

# Verify backend directory exists
if (-not (Test-Path "backend")) {
    Write-Host "✗ Backend directory not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Start Backend
Write-Host "Starting backend server..." -ForegroundColor Cyan
$backendScript = @"
`$ErrorActionPreference = 'Stop'
cd '$PWD\backend'

# Check for virtual environment
if (Test-Path 'venv\Scripts\Activate.ps1') {
    Write-Host 'Activating virtual environment (venv)...' -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} elseif (Test-Path '.venv\Scripts\Activate.ps1') {
    Write-Host 'Activating virtual environment (.venv)...' -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host 'No virtual environment found. Using system Python.' -ForegroundColor Yellow
}

Write-Host 'Starting FastAPI backend on http://localhost:8000' -ForegroundColor Green
python main.py
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript

Write-Host ""
Write-Host "✓ Backend server is starting in a new window" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs:    http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in the server window to stop it." -ForegroundColor Gray
