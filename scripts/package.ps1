param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not $SkipBuild) { & "$PSScriptRoot/build.ps1" }
    if (-not (Test-Path -LiteralPath 'app/build/metro.jar')) { throw '入口JAR不存在，请先构建。' }
    New-Item -ItemType Directory -Force -Path dist | Out-Null
    @'
from pathlib import Path
import zipfile,hashlib
root=Path.cwd()
target=root/'dist/Project1_v0.zip'
folders=['app/src','app/lib','sql','tools','tests','scripts','docs','generated','source-data']
files=[p for d in folders for p in (root/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files += [root/'app/pom.xml',root/'app/build/metro.jar',root/'config/db.example.properties',root/'config/data-rules.json',root/'.gitignore']
files += list(root.glob('*.md'))+list(root.glob('*.json'))
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(set(files)):
        archive.write(p,Path('Project1_v0')/p.relative_to(root))
digest=hashlib.sha256(target.read_bytes()).hexdigest()
(root/'dist/Project1_v0.zip.sha256').write_text(digest+'  Project1_v0.zip\n',encoding='ascii')
print(f'Packaged {len(set(files))} files, {target.stat().st_size} bytes: {target}')
'@ | python -
    if ($LASTEXITCODE -ne 0) { throw '打包失败' }
} finally { Pop-Location }
