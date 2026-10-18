# Dispatch Engine for Windows. Run it through run.cmd, which bypasses the script
# execution policy and also works when double-clicked:
#
#   .\run.cmd             start the app and open it in the browser
#   .\run.cmd check       run every check: lint, types, unit, e2e, logs
#   .\run.cmd stop        stop everything
#   .\run.cmd logs        follow the container logs
#
# Add --db to start or check with Postgres + Redis. Needs only Docker Desktop.

Set-StrictMode -Version Latest
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
Set-Location (Split-Path -Parent $PSScriptRoot)

function Write-Fail([string]$Message) {
    Write-Host ""
    Write-Host $Message -ForegroundColor Red
    Exit-Script 1
}

# Started by double-clicking run.cmd? Then keep the window open at the end.
function Test-DoubleClicked {
    try {
        $self = Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
        $cmd = Get-CimInstance Win32_Process -Filter "ProcessId=$($self.ParentProcessId)"
        $launcher = Get-CimInstance Win32_Process -Filter "ProcessId=$($cmd.ParentProcessId)"
        return ($cmd.Name -eq 'cmd.exe' -and $launcher.Name -eq 'explorer.exe')
    } catch {
        return $false
    }
}

function Exit-Script([int]$Code) {
    if ($script:DoubleClicked) { Read-Host "Press Enter to close" | Out-Null }
    exit $Code
}

function Invoke-Quiet([string]$CommandLine) {
    # cmd keeps native stderr away from PowerShell's error handling (Windows PowerShell 5.1).
    $output = cmd /c "$CommandLine 2>&1"
    return [pscustomobject]@{ Ok = ($LASTEXITCODE -eq 0); Output = $output }
}

function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Fail "Docker is not installed. Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/"
    }
    if (-not (Invoke-Quiet "docker compose version").Ok) {
        Write-Fail "Docker Compose v2 is missing. Update Docker Desktop."
    }
    if (-not (Invoke-Quiet "docker info").Ok) {
        Write-Fail "Docker Desktop is installed but not running. Start it from the Start menu, wait until it says 'Engine running', then run this again."
    }
}

# Port of the app if it is already running, else $null.
function Get-RunningPort {
    $result = Invoke-Quiet "docker compose port web 80"
    if (-not $result.Ok -or -not $result.Output) { return $null }
    return (@($result.Output)[0] -split ':')[-1].Trim()
}

function Test-PortFree([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $Port)
    try { $listener.Start(); return $true } catch { return $false } finally { try { $listener.Stop() } catch { } }
}

# Keep the current port if the app is up; else WEB_PORT; else the first free one from 8080.
function Get-WebPort {
    $current = Get-RunningPort
    if ($current) { return $current }
    if ($env:WEB_PORT) { return $env:WEB_PORT }
    foreach ($port in 8080..8099) {
        if (Test-PortFree $port) { return "$port" }
    }
    Write-Fail "Ports 8080-8099 are all in use. Pick one first, for example:  `$env:WEB_PORT = '9090'"
}

function Invoke-Compose {
    $all = @('compose') + $script:DbArgs + $args
    # Out-Host streams docker's output to the screen, so the only return value is the bool.
    & docker @all | Out-Host
    return ($LASTEXITCODE -eq 0)
}

function Start-App {
    Test-Docker
    $env:WEB_PORT = Get-WebPort
    Write-Host "Building and starting the app (the first run downloads images and takes a few minutes)..."
    if (-not (Invoke-Compose up --build -d --wait)) {
        Write-Fail "The app did not start. See what happened with:  .\run.cmd logs"
    }
    $url = "http://localhost:$($env:WEB_PORT)"
    Write-Host ""
    Write-Host "Dispatch Engine is running" -ForegroundColor Green
    Write-Host "  App:       $url"
    Write-Host "  API docs:  $url/docs"
    Write-Host "  Stop:      .\run.cmd stop"
    if (-not $env:CI -and -not $env:NO_BROWSER) { Start-Process $url }
}

function Invoke-Checks {
    Test-Docker
    $wasRunning = [bool](Get-RunningPort)
    $env:WEB_PORT = Get-WebPort
    if ($script:DbArgs.Count -gt 0) {
        $mode = 'Postgres + Redis'; $storage = 'postgres'; $cache = 'redis'
    } else {
        $mode = 'in-memory storage, no cache'; $storage = 'memory'; $cache = 'none'
    }
    $steps = @(
        @{ Name = 'API: ruff, mypy (strict), pytest'; Run = { Invoke-Compose run --rm -T --build api-tests } },
        @{ Name = 'UI: npm ci (Node 22)'; Run = { Invoke-Compose run --rm -T tools ci } },
        @{ Name = 'UI: ESLint, TypeScript, Vitest, production build'; Run = { Invoke-Compose run --rm -T tools run check } },
        @{ Name = "Stack: build and start ($mode)"; Run = { Invoke-Compose up --build -d --wait } },
        @{ Name = 'API e2e: direct to the API'; Run = {
                Invoke-Compose run --rm -T -e "E2E_EXPECT_STORAGE=$storage" -e "E2E_EXPECT_CACHE=$cache" api-tests pytest -m e2e } },
        @{ Name = 'API e2e: through nginx'; Run = { Invoke-Compose run --rm -T -e E2E_BASE_URL=http://web api-tests pytest -m e2e } },
        @{ Name = 'UI e2e: Playwright (Chromium)'; Run = { Invoke-Compose run --rm -T e2e } },
        @{ Name = 'Container logs: no warnings or errors'; Run = {
                $logs = (Invoke-Quiet ("docker " + ((@('compose') + $script:DbArgs) -join ' ') + " logs --no-color")).Output
                $hits = @($logs | Where-Object {
                        $_ -match '(?i)warn|error|exception|traceback|fatal|deprecat|" 5\d\d ' -and $_ -notmatch '" 4\d\d '
                    })
                if ($hits.Count -gt 0) { $hits | ForEach-Object { Write-Host $_ }; return $false }
                Write-Host "No warnings or errors in any container log."
                return $true
            } }
    )

    $results = @()
    foreach ($step in $steps) {
        Write-Host ""
        Write-Host "> $($step.Name)" -ForegroundColor Cyan
        $out = @(& $step.Run)
        $ok = ($out.Count -gt 0) -and [bool]$out[-1]
        $results += [pscustomobject]@{ Name = $step.Name; Ok = $ok }
    }
    if (-not $wasRunning) { $null = Invoke-Quiet "docker compose --profile db --profile tools down" }

    Write-Host ""
    Write-Host "Summary ($mode)"
    foreach ($r in $results) {
        if ($r.Ok) { Write-Host "  PASS  $($r.Name)" -ForegroundColor Green }
        else { Write-Host "  FAIL  $($r.Name)" -ForegroundColor Red }
    }
    $failed = @($results | Where-Object { -not $_.Ok }).Count
    Write-Host ""
    if ($failed -eq 0) {
        Write-Host "ALL GREEN: $($results.Count)/$($results.Count) checks passed" -ForegroundColor Green
        if ($wasRunning) { Write-Host "App still running: http://localhost:$($env:WEB_PORT)" }
        Exit-Script 0
    }
    Write-Host "$failed of $($results.Count) checks failed" -ForegroundColor Red
    Exit-Script 1
}

function Stop-App {
    Test-Docker
    if (Invoke-Compose --profile db --profile tools down --remove-orphans) { Write-Host "Stopped." -ForegroundColor Green }
}

# ----- main -----
$script:DoubleClicked = Test-DoubleClicked
$script:DbArgs = @()
$command = 'start'
foreach ($arg in $args) {
    if ($arg -eq '--db') { $script:DbArgs = @('--env-file', '.env.db') }
    elseif (@('start', 'check', 'stop', 'logs', 'help') -contains $arg) { $command = $arg }
    else { Write-Host "Unknown option: $arg (see .\run.cmd help)"; Exit-Script 2 }
}

switch ($command) {
    'start' { Start-App }
    'check' { Invoke-Checks }
    'stop' { Stop-App }
    'logs' { Test-Docker; $null = Invoke-Compose logs -f --tail 100 }
    'help' { Get-Content $PSCommandPath -TotalCount 9 | ForEach-Object { $_ -replace '^# ?', '' } }
}
Exit-Script 0
