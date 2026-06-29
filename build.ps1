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

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    & $VenvPython -c "import sys; print(sys.version)" *> $null
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -LiteralPath (Join-Path $Root ".venv") -Recurse -Force
    }
}

if (-not (Test-Path $VenvPython)) {
    Invoke-Step { & $Python -m venv .venv }
}

Invoke-Step { & $VenvPython -m pip --disable-pip-version-check install -r requirements.txt }
& $VenvPython -c "import win32api, pywintypes" *> $null
if ($LASTEXITCODE -ne 0) {
    Invoke-Step { & $VenvPython -m pip --disable-pip-version-check install --force-reinstall --no-cache-dir "pywin32>=306" }
    Invoke-Step { & $VenvPython -c "import win32api, pywintypes" }
}

$PyWin32System32 = Join-Path $Root ".venv\Lib\site-packages\pywin32_system32"
$PyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--collect-all", "qfluentwidgets",
    "--collect-all", "qframelesswindow",
    "--hidden-import", "win32api",
    "--hidden-import", "pywintypes",
    "--add-data", "Icon.png:.",
    "--icon", "Icon.png",
    "--name", "CapsLockShow"
)

if (Test-Path $PyWin32System32) {
    Get-ChildItem -Path $PyWin32System32 -Filter "*.dll" | ForEach-Object {
        $PyInstallerArgs += @("--add-binary", "$($_.FullName);.")
    }
}

$PyInstallerArgs += "main.py"
Invoke-Step { & $VenvPython -m PyInstaller @PyInstallerArgs }

Write-Host "Built: $Root\dist\CapsLockShow.exe"
