param([switch]$Tests)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $javac = Get-Command javac -ErrorAction SilentlyContinue
    if (-not $javac) { throw '需要JDK 17或更新版本（包含javac）。' }
    # Oracle 的 javapath 只代理 java/javac，jar 常常不在 PATH：按 JAVA_HOME -> java.home 顺序找。
    $jarExe = (Get-Command jar -ErrorAction SilentlyContinue).Source
    if (-not $jarExe -and $env:JAVA_HOME) {
        $candidate = Join-Path $env:JAVA_HOME 'bin/jar.exe'
        if (Test-Path -LiteralPath $candidate) { $jarExe = $candidate }
    }
    if (-not $jarExe) {
        $javaExe = (Get-Command java -ErrorAction SilentlyContinue).Source
        if ($javaExe) {
            $errFile = Join-Path ([IO.Path]::GetTempPath()) ('metro_java_home_' + [guid]::NewGuid().ToString('N') + '.txt')
            try {
                # java -XshowSettings 把属性写到 stderr，重定向到文件可避开 ErrorActionPreference=Stop
                Start-Process -FilePath $javaExe -ArgumentList '-XshowSettings:properties','-version' -NoNewWindow -Wait -RedirectStandardError $errFile -RedirectStandardOutput "$errFile.out" | Out-Null
                $text = (Get-Content -LiteralPath $errFile -Raw -ErrorAction SilentlyContinue) + (Get-Content -LiteralPath "$errFile.out" -Raw -ErrorAction SilentlyContinue)
                if ($text -match 'java\.home = (.+)') {
                    $candidate = Join-Path $Matches[1].Trim() 'bin\jar.exe'
                    if (Test-Path -LiteralPath $candidate) { $jarExe = $candidate }
                }
            } catch { } finally { Remove-Item -LiteralPath $errFile,"$errFile.out" -Force -ErrorAction SilentlyContinue }
        }
    }
    if (-not $jarExe) { throw '找不到 jar.exe：请把 JDK 的 bin 目录加入 PATH，或设置 JAVA_HOME 指向 JDK。' }
    $driverPath = Join-Path $projectRoot 'app/lib/postgresql-42.7.14.jar'
    if (-not (Test-Path -LiteralPath $driverPath)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $driverPath) | Out-Null
        Invoke-WebRequest -Uri 'https://jdbc.postgresql.org/download/postgresql-42.7.14.jar' -OutFile $driverPath
    }
    $expectedHash = '73914527305A40CCE504B0D3D90B23CAF565136912D607AE8AE7C5895512332C'
    if ((Get-FileHash -LiteralPath $driverPath -Algorithm SHA256).Hash -ne $expectedHash) { throw 'JDBC驱动哈希不匹配，请核对下载来源。' }
    New-Item -ItemType Directory -Force -Path 'app/build/classes/sql','app/build/classes/web','app/build/test-classes' | Out-Null
    $mainSources = @(Get-ChildItem -LiteralPath 'app/src/main/java' -Recurse -Filter '*.java' | ForEach-Object FullName)
    & javac --release 17 -encoding UTF-8 -cp $driverPath -d app/build/classes $mainSources
    if ($LASTEXITCODE -ne 0) { throw 'Java compilation failed' }
    Copy-Item -Path 'sql/q*.sql' -Destination 'app/build/classes/sql' -Force
    Copy-Item -Path 'app/src/main/resources/web/*' -Destination 'app/build/classes/web' -Force
    "Manifest-Version: 1.0`nMain-Class: metro.Main`nClass-Path: ../lib/postgresql-42.7.14.jar`n`n" | Set-Content -LiteralPath 'app/build/MANIFEST.MF' -Encoding ascii
    & $jarExe --create --file app/build/metro.jar --manifest app/build/MANIFEST.MF -C app/build/classes .
    if ($LASTEXITCODE -ne 0) { throw 'JAR packaging failed' }
    if ($Tests) {
        $testSources = @(Get-ChildItem -LiteralPath 'app/src/test/java' -Recurse -Filter '*.java' | ForEach-Object FullName)
        & $javac.Source --release 17 -encoding UTF-8 -cp app/build/classes -d app/build/test-classes $testSources
        if ($LASTEXITCODE -ne 0) { throw 'Test compilation failed' }
    }
    Write-Output 'Build PASS: app/build/metro.jar'
} finally { Pop-Location }
