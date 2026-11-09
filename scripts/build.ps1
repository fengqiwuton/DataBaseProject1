param([switch]$Tests)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Get-Command javac -ErrorAction SilentlyContinue)) { throw '需要JDK 17或更新版本（包含javac）。' }
    $driverPath = Join-Path $projectRoot 'app/lib/postgresql-42.7.14.jar'
    if (-not (Test-Path -LiteralPath $driverPath)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $driverPath) | Out-Null
        Invoke-WebRequest -Uri 'https://jdbc.postgresql.org/download/postgresql-42.7.14.jar' -OutFile $driverPath
    }
    $expectedHash = '73914527305A40CCE504B0D3D90B23CAF565136912D607AE8AE7C5895512332C'
    if ((Get-FileHash -LiteralPath $driverPath -Algorithm SHA256).Hash -ne $expectedHash) { throw 'JDBC驱动哈希不匹配，请核对下载来源。' }
    New-Item -ItemType Directory -Force -Path 'app/build/classes/sql','app/build/classes/web','app/build/test-classes' | Out-Null
    $mainSources = @(Get-ChildItem -LiteralPath 'app/src/main/java' -Recurse -Filter '*.java' | ForEach-Object FullName)
    & javac --release 17 -encoding UTF-8 -d app/build/classes $mainSources
    if ($LASTEXITCODE -ne 0) { throw 'Java compilation failed' }
    Copy-Item -Path 'sql/q*.sql' -Destination 'app/build/classes/sql' -Force
    Copy-Item -Path 'app/src/main/resources/web/*' -Destination 'app/build/classes/web' -Force
    "Manifest-Version: 1.0`nMain-Class: metro.Main`nClass-Path: ../lib/postgresql-42.7.14.jar`n`n" | Set-Content -LiteralPath 'app/build/MANIFEST.MF' -Encoding ascii
    & jar --create --file app/build/metro.jar --manifest app/build/MANIFEST.MF -C app/build/classes .
    if ($LASTEXITCODE -ne 0) { throw 'JAR packaging failed' }
    if ($Tests) {
        $testSources = @(Get-ChildItem -LiteralPath 'app/src/test/java' -Recurse -Filter '*.java' | ForEach-Object FullName)
        & javac --release 17 -encoding UTF-8 -cp app/build/classes -d app/build/test-classes $testSources
        if ($LASTEXITCODE -ne 0) { throw 'Test compilation failed' }
    }
    Write-Output 'Build PASS: app/build/metro.jar'
} finally { Pop-Location }
