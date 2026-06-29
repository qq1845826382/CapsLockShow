param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not $Python) {
    $Python = "python"
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step { & $Python -m venv .venv }
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

Invoke-Step { & $VenvPython -m pip --disable-pip-version-check install -r requirements.txt }
Invoke-Step { & $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --collect-all qfluentwidgets `
    --name CapsLockShow `
    main.py }

Write-Host "Built: $Root\dist\CapsLockShow.exe"
