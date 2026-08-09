<#
    Build the Mac package zip from a staging folder.

    Why this exists rather than a one-liner:

    1. PowerShell 5.1's Compress-Archive writes BACKSLASH path separators into
       the zip. The spec (APPNOTE 4.4.17.1) requires forward slashes, and macOS
       may extract the tree as flat files literally named
       "MBC2Dashboard\app\server.py" - leaving the .command unable to find
       app/server.py. The shipped v4.0.1 Mac zip had this.

    2. bsdtar (tar.exe) writes forward slashes correctly but PADS the archive to
       a 10240-byte block boundary, leaving trailing zeros after the End of
       Central Directory record. Strict readers reject that outright.

    3. Neither can set the Unix execute bit, so the Mac README has always had to
       tell users to chmod the launcher by hand. Writing the zip directly lets
       us set ExternalAttributes, so the .command arrives executable.

    Usage: make-mac-zip.ps1 -StageDir <dir> -ZipPath <file> [-ExecPattern *.command]
#>
param(
    [Parameter(Mandatory=$true)][string]$StageDir,
    [Parameter(Mandatory=$true)][string]$ZipPath,
    [string]$ExecPattern = '*.command'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$stage = (Resolve-Path $StageDir).Path.TrimEnd('\')
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

# 0o100755 (regular file, rwxr-xr-x) and 0o100644 in the high 16 bits, which is
# where the zip format keeps Unix mode. Without this macOS unzips the launcher
# without its execute bit and the user has to chmod it by hand.
$MODE_EXEC = [Convert]::ToInt32('100755', 8) -shl 16
$MODE_FILE = [Convert]::ToInt32('100644', 8) -shl 16

$zip = [System.IO.Compression.ZipFile]::Open($ZipPath, 'Create')
try {
    foreach ($f in Get-ChildItem -Path $stage -Recurse -File) {
        # Forward slashes, always - this is the whole point of the script.
        $rel = $f.FullName.Substring($stage.Length + 1).Replace('\', '/')
        $entry = $zip.CreateEntry($rel, [System.IO.Compression.CompressionLevel]::Optimal)
        $entry.LastWriteTime = $f.LastWriteTime
        $entry.ExternalAttributes = if ($f.Name -like $ExecPattern) { $MODE_EXEC } else { $MODE_FILE }
        $out = $entry.Open()
        try { $in = [System.IO.File]::OpenRead($f.FullName); try { $in.CopyTo($out) } finally { $in.Dispose() } }
        finally { $out.Dispose() }
    }
}
finally { $zip.Dispose() }

# Verify by reading it back. A build that silently produces an unusable Mac zip
# is the failure this whole script exists to prevent, so fail loudly here rather
# than on someone's Mac.
$z = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path $ZipPath))
try {
    $bad  = @($z.Entries | Where-Object { $_.FullName -like '*\*' })
    $exec = @($z.Entries | Where-Object { $_.Name -like $ExecPattern })
    $n    = $z.Entries.Count
}
finally { $z.Dispose() }

if ($bad.Count)  { Write-Host "  ZIP CHECK FAILED - $($bad.Count) entries use backslashes"; exit 1 }
if (-not $n)     { Write-Host "  ZIP CHECK FAILED - archive is empty";                      exit 1 }
if (-not $exec.Count) { Write-Host "  ZIP CHECK FAILED - no $ExecPattern entry found";      exit 1 }
foreach ($e in $exec) {
    if ($e.ExternalAttributes -ne $MODE_EXEC) {
        Write-Host "  ZIP CHECK FAILED - $($e.FullName) is not marked executable"; exit 1
    }
}
Write-Host "  Zip check OK - $n entries, forward slashes, $($exec.Count) executable"
exit 0
