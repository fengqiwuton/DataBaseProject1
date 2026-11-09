param([switch]$Web, [int]$Port = 8088, [switch]$Rebuild)
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if ($Rebuild -or -not (Test-Path -LiteralPath 'app/build/metro.jar')) { & "$PSScriptRoot/build.ps1" }
    if ($Web) { & java '-Dfile.encoding=UTF-8' -jar app/build/metro.jar --web $Port }
    else { & java '-Dfile.encoding=UTF-8' -jar app/build/metro.jar }
    if ($LASTEXITCODE -ne 0) { throw '程序启动失败，请检查数据库连接和README。' }
} finally { Pop-Location }
