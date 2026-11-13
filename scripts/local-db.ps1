param(
    [ValidateSet('start','import','connect','sql-reader','stop','status')][string]$Action='status',
    [string]$PgBin='',
    [int]$Port=55437
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PgBin) {
    $client = Get-Command psql -ErrorAction SilentlyContinue
    if (-not $client) { throw '请用-PgBin指定PostgreSQL bin目录。' }
    $PgBin = Split-Path -Parent $client.Source
}
$runtimeDir = Join-Path $projectRoot '.runtime'
$dataDir = Join-Path $runtimeDir 'pgdata'
$pgControl = Join-Path $PgBin 'pg_ctl.exe'
$clientPath = Join-Path $PgBin 'psql.exe'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
function Invoke-MetroPsql {
    param([string[]]$PsqlArguments, [switch]$RenderInPowerShell)
    $previousInput = [Console]::InputEncoding
    $previousOutput = [Console]::OutputEncoding
    $previousClientEncoding = $env:PGCLIENTENCODING
    $previousLocale = $env:LC_ALL
    try {
        # Older Windows psql can emit GBK translations even with a UTF-8 connection.
        # C locale makes labels ASCII; result data and the console both use UTF-8.
        $env:LC_ALL = 'C'
        $env:PGCLIENTENCODING = 'UTF8'
        $OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
        if ($RenderInPowerShell) {
            # Route stdout through PowerShell's UTF-8 decoder instead of the older psql console writer.
            & $clientPath -X -h 127.0.0.1 -p $Port -U metro @PsqlArguments | ForEach-Object { Write-Host $_ }
        } else {
            & $clientPath -X -h 127.0.0.1 -p $Port -U metro @PsqlArguments
        }
    } finally {
        $env:PGCLIENTENCODING = $previousClientEncoding
        $env:LC_ALL = $previousLocale
        [Console]::InputEncoding = $previousInput
        [Console]::OutputEncoding = $previousOutput
    }
}
function Check-OwnedCluster {
    $actualData = Invoke-MetroPsql -PsqlArguments @('-d','postgres','-At','-c','SHOW data_directory')
    if ($LASTEXITCODE -ne 0) { throw '无法核对本地测试实例；不会导入或停止其他实例。' }
    $expectedPath = [IO.Path]::GetFullPath($dataDir).Replace('\','/').TrimEnd('/')
    if ($actualData.Trim().Replace('\','/').TrimEnd('/') -ine $expectedPath) { throw '端口指向其他数据库实例，操作已停止。' }
}
function Enable-SqlReader {
    Invoke-MetroPsql -PsqlArguments @('-d','metro_test','-v','ON_ERROR_STOP=1','-f',(Join-Path $projectRoot 'sql/web-reader.sql'))
    if ($LASTEXITCODE -ne 0) { throw 'SQL 查询账号配置失败' }
}
if ($Action -eq 'start') {
    if (-not (Test-Path -LiteralPath (Join-Path $dataDir 'PG_VERSION'))) {
        if (Test-Path -LiteralPath $dataDir) { throw 'pgdata目录已有内容但不是完整集群；请手工核查。' }
        & (Join-Path $PgBin 'initdb.exe') -D $dataDir -U metro --auth=trust --encoding=UTF8 --locale=C
        if ($LASTEXITCODE -ne 0) { throw 'initdb failed' }
    }
    & $pgControl -D $dataDir status *> $null
    if ($LASTEXITCODE -ne 0) {
        $startArgs = @('-D',('"'+$dataDir+'"'),'-l',('"'+(Join-Path $runtimeDir 'postgres.log')+'"'),'-o',('"-h 127.0.0.1 -p '+$Port+'"'),'-w','start')
        # Do not use Start-Process -Wait: Windows waits for the server descendants too.
        $pgStart = Start-Process -FilePath $pgControl -ArgumentList $startArgs -WindowStyle Hidden -PassThru
        if (-not $pgStart.WaitForExit(30000)) { throw 'PostgreSQL启动超时，请查看.runtime/postgres.log' }
    }
    Check-OwnedCluster
    $exists = Invoke-MetroPsql -PsqlArguments @('-d','postgres','-At','-c',"SELECT count(*) FROM pg_database WHERE datname='metro_test'")
    if ($LASTEXITCODE -ne 0) { throw '数据库检查失败' }
    if ($exists.Trim() -eq '0') {
        & (Join-Path $PgBin 'createdb.exe') -h 127.0.0.1 -p $Port -U metro metro_test
        if ($LASTEXITCODE -ne 0) { throw '创建测试库失败' }
    }
    Write-Output "本地测试库已启动：127.0.0.1:$Port / metro_test / metro（仅回环地址、trust认证）"
} elseif ($Action -eq 'import') {
    Check-OwnedCluster
    Write-Output '重建专用metro_test库内的project1六表；其他schema不会清理。'
    Invoke-MetroPsql -PsqlArguments @('-d','metro_test','-v','ON_ERROR_STOP=1','-f',(Join-Path $projectRoot 'sql/import.sql'))
    if ($LASTEXITCODE -ne 0) { throw '导入失败，事务已回滚' }
    Enable-SqlReader
} elseif ($Action -eq 'sql-reader') {
    Check-OwnedCluster
    Enable-SqlReader
} elseif ($Action -eq 'connect') {
    Check-OwnedCluster
    Write-Host '可输入 SQL 或 \dt project1.*；SQL 用分号结束，输入 \q 退出。'
    Invoke-MetroPsql -PsqlArguments @('-d','metro_test','-P','pager=off') -RenderInPowerShell
    if ($LASTEXITCODE -ne 0) { throw 'psql 连接异常退出' }
} elseif ($Action -eq 'stop') {
    & $pgControl -D $dataDir status *> $null
    if ($LASTEXITCODE -eq 0) {
        Check-OwnedCluster
        & $pgControl -D $dataDir -m fast -w stop
        if ($LASTEXITCODE -ne 0) { throw '停止失败' }
    }
    Write-Output '本项目测试实例已停止。'
} else {
    & $pgControl -D $dataDir status
}
