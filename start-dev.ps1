$ErrorActionPreference = "Stop"

function Stop-StalePort {
    param([int]$Port)

    $ids = @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)

    if (-not $ids) {
        return
    }

    foreach ($id in $ids) {
        if ($null -eq $id -or $id -eq 0) { continue }
        try {
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped stale process PID $id on port $Port"
        } catch {
            Write-Host "Could not stop PID $id on port $Port" -ForegroundColor Yellow
        }
    }
}

function Stop-StaleProcessName {
    param([string]$ProcessName)

    $matches = Get-CimInstance Win32_Process | Where-Object { $_.Name -match $ProcessName }
    foreach ($match in $matches) {
        try {
            Stop-Process -Id $match.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped stale $ProcessName process PID $($match.ProcessId)"
        } catch {
            Write-Host "Could not stop stale $ProcessName process PID $($match.ProcessId)" -ForegroundColor Yellow
        }
    }
}

function Ensure-PythonEnv {
    param(
        [string]$BackendDir
    )

    Stop-StaleProcessName -ProcessName "python.exe"
    Stop-StaleProcessName -ProcessName "pip.exe"
    Stop-StaleProcessName -ProcessName "uvicorn.exe"

    $venvDir = Join-Path $BackendDir ".venv"
    $pythonExe = Join-Path $venvDir "Scripts\python.exe"

    if (-not (Test-Path $pythonExe)) {
        Write-Host "Creating Python virtual environment in $venvDir"
        python -m venv $venvDir
    }

    if (-not (Test-Path $pythonExe)) {
        throw "Python virtual environment did not get created at $pythonExe"
    }

    & $pythonExe -m pip install --upgrade pip --retries 5 --timeout 120 | Out-Null
    & $pythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt") --retries 5 --timeout 120 | Out-Null
    Write-Host "Backend dependencies ensured for $BackendDir"
}

function Ensure-NodeDeps {
    param(
        [string]$FrontendDir
    )

    $nodeModules = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "Installing frontend dependencies in $FrontendDir"
        Push-Location $FrontendDir
        try {
            npm install
        } finally {
            Pop-Location
        }
    }
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60,
        [int]$ExpectedStatus = 200
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 5 -SkipHttpErrorCheck
            if ($response.StatusCode -eq $ExpectedStatus) {
                return $true
            }
            if ($response.StatusCode -eq 404) {
                return $false
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Ensure-FrontendHealthy {
    param(
        [string]$FrontendDir,
        [int]$RetryCount = 2
    )

    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        $frontendUrl = "http://127.0.0.1:5174/"
        $status = Wait-ForHttp -Url $frontendUrl -TimeoutSeconds 30 -ExpectedStatus 200

        if ($status) {
            Write-Host "Frontend verified healthy at $frontendUrl"
            return $true
        }

        Write-Host "Frontend check failed on attempt $attempt; forcing restart..."
        Stop-StalePort -Port 5173
        Stop-StalePort -Port 5174
        Stop-StalePort -Port 4173

        $frontendCmd = "cd '$FrontendDir'; npm run dev -- --host 127.0.0.1 --port 5174 --strictPort"
        Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCmd | Out-Null
        Start-Sleep -Seconds 2
    }

    return $false
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

$ports = 8000, 5173, 5174, 4173
foreach ($port in $ports) {
    Stop-StalePort -Port $port
}

Ensure-PythonEnv -BackendDir $backendDir
Ensure-NodeDeps -FrontendDir $frontendDir

$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$backendCmd = "cd '$backendDir'; `$env:PYTHONPATH='.'; & '$venvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
$frontendCmd = "cd '$frontendDir'; npm run dev"

Start-Process powershell -ArgumentList '-NoExit', '-Command', $backendCmd | Out-Null
Start-Sleep -Seconds 2

if (-not (Wait-ForHttp -Url "http://127.0.0.1:8000/api/health" -TimeoutSeconds 40 -ExpectedStatus 200)) {
    Write-Error "Backend did not become healthy on http://127.0.0.1:8000/api/health"
    exit 1
}

Write-Host "Backend verified healthy at http://127.0.0.1:8000/api/health"

Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCmd | Out-Null
Start-Sleep -Seconds 2

if (-not (Ensure-FrontendHealthy -FrontendDir $frontendDir -RetryCount 2)) {
    Write-Error "Frontend did not become healthy on http://127.0.0.1:5174/. Check the dev server logs and port state."
    exit 1
}

Write-Host "Open: http://127.0.0.1:5174/"
Write-Host "Use a fresh browser tab; avoid stale localhost or 5174 tabs."
Write-Host "If the page still looks blank, close the browser tab and reopen the URL in a fresh tab."
