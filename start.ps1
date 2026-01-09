# Startup script for Spotify Gemini Playlist Builder
# Kills existing processes and starts backend and frontend servers

Write-Host "🚀 Starting Spotify Gemini Playlist Builder..." -ForegroundColor Cyan
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
Kill-ProcessOnPort -Port 5173
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

# Check if Node.js is installed
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found. Please install Node.js." -ForegroundColor Red
    exit 1
}

# Check if npm is installed
try {
    $npmVersion = npm --version 2>&1
    Write-Host "✓ npm found: v$npmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ npm not found. Please install npm." -ForegroundColor Red
    exit 1
}

# Verify directories exist
if (-not (Test-Path "backend")) {
    Write-Host "✗ Backend directory not found!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "frontend")) {
    Write-Host "✗ Frontend directory not found!" -ForegroundColor Red
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
Start-Sleep -Seconds 2

# Start Frontend
Write-Host "Starting frontend server..." -ForegroundColor Cyan
$frontendScript = @"
`$ErrorActionPreference = 'Stop'
cd '$PWD\frontend'

# Check if node_modules exists
if (-not (Test-Path 'node_modules')) {
    Write-Host 'Installing npm dependencies...' -ForegroundColor Yellow
    npm install
}

Write-Host 'Starting Vite dev server on http://localhost:5173' -ForegroundColor Green
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript

Write-Host ""
Write-Host "✓ Backend and frontend servers are starting in separate windows" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in the respective windows to stop each server." -ForegroundColor Gray
