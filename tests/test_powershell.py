"""Check the scripts in the user's Windows PowerShell 5.1, not only pwsh 7."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which('powershell.exe') if os.name == 'nt' else None


@unittest.skipUnless(POWERSHELL, 'Windows PowerShell is not installed')
class WindowsPowerShellTest(unittest.TestCase):
    def test_scripts_parse_in_windows_powershell(self):
        command = r'''
$failed = @()
Get-ChildItem -LiteralPath $env:METRO_SCRIPT_TEST_DIR -Filter '*.ps1' | ForEach-Object {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count -gt 0) { $failed += ($_.Name + ': ' + $parseErrors.Count + ' parse errors') }
}
if ($failed.Count -gt 0) { $failed | Write-Output; exit 1 }
Write-Output 'Windows PowerShell parser: all scripts PASS'
'''
        env = dict(os.environ, METRO_SCRIPT_TEST_DIR=str(ROOT / 'scripts'))
        result = subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-Command', command],
                                env=env, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout.decode('utf-8', errors='replace') +
                         result.stderr.decode('utf-8', errors='replace'))

    def test_non_ascii_scripts_have_utf8_bom(self):
        for path in (ROOT / 'scripts').glob('*.ps1'):
            raw = path.read_bytes()
            if any(b >= 128 for b in raw):
                self.assertTrue(raw.startswith(b'\xef\xbb\xbf'),
                                path.name + ': Windows PowerShell requires an explicit UTF-8 BOM')


if __name__ == '__main__':
    unittest.main()
