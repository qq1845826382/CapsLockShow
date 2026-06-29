$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

dotnet restore
dotnet publish .\CapsLockShow.csproj `
    -c Release `
    -r win-x64 `
    --self-contained false `
    /p:PublishSingleFile=true `
    /p:PublishReadyToRun=true `
    /p:PublishDir="$Root\dist\"

Write-Host "Built: $Root\dist\CapsLockShow.exe"
