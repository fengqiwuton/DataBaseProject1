param([switch]$Integration)
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    & python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Python tests failed' }
    if (Get-Command node -ErrorAction SilentlyContinue) {
        & node --test tests/test_web_ui.cjs
        if ($LASTEXITCODE -ne 0) { throw 'Frontend regression tests failed' }
    } else { Write-Output 'Node未安装：跳过前端回归测试；Java/数据库测试继续。' }
    & "$PSScriptRoot/build.ps1" -Tests
    $testClassPath = 'app/build/classes;app/build/test-classes;app/lib/postgresql-42.7.14.jar'
    $testClasses = @('metro.RouterTest','metro.FareTest','metro.CliTest')
    if ($Integration) { $testClasses += @('metro.IntegrationTest','metro.WebTest') }
    foreach ($testClass in $testClasses) {
        & java '-Dfile.encoding=UTF-8' -cp $testClassPath $testClass
        if ($LASTEXITCODE -ne 0) { throw "Test failed: $testClass" }
    }
    & java '-Dfile.encoding=UTF-8' -jar app/build/metro.jar --help
    if ($LASTEXITCODE -ne 0) { throw 'CLI help failed' }
    if ($Integration) {
        $smoke = & java '-Dfile.encoding=UTF-8' -jar app/build/metro.jar --action q1
        if ($LASTEXITCODE -ne 0 -or $smoke -notmatch '439') { throw 'Packaged CLI smoke failed' }
        $menu = '0' | & java '-Dfile.encoding=UTF-8' -jar app/build/metro.jar
        if ($LASTEXITCODE -ne 0 -or ($menu -join '') -notmatch '26\.') { throw 'Interactive CLI smoke failed' }
    }
    Write-Output 'ALL REQUESTED TESTS PASS'
} finally { Pop-Location }
