# Copies ONLY into an explicitly selected test project. Dry-run by default.
# -ProjectRoot must have a .uefnproject descriptor. No overwrites, no asset movement.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot,
    [Parameter(Mandatory=$true)][string]$TargetVerseDirectory,
    [ValidateSet('A','B','C','ALL')][string]$Benchmark='A',
    [switch]$Apply
)
$ErrorActionPreference='Stop'
$Project=(Resolve-Path -LiteralPath $ProjectRoot).Path
if (-not (Get-ChildItem -LiteralPath $Project -Filter '*.uefnproject' -File)) {
    throw 'Not a UEFN project root: missing *.uefnproject'
}
$Target=(Resolve-Path -LiteralPath $TargetVerseDirectory).Path
$projectPrefix=$Project.TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar
if (-not $Target.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'TargetVerseDirectory must be an EXISTING directory under ProjectRoot'
}
$Root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$BenchmarkRoot=Join-Path $Root 'examples\benchmarks'
$Dirs=@()
if ($Benchmark -eq 'A' -or $Benchmark -eq 'ALL') { $Dirs+=Join-Path $BenchmarkRoot 'A-interactive-device' }
if ($Benchmark -eq 'B' -or $Benchmark -eq 'ALL') { $Dirs+=Join-Path $BenchmarkRoot 'B-verse-ui' }
if ($Benchmark -eq 'C' -or $Benchmark -eq 'ALL') { $Dirs+=Join-Path $BenchmarkRoot 'C-rp-garage' }
$Plan=@()
foreach($folder in $Dirs) {
    foreach($file in Get-ChildItem -LiteralPath $folder -Filter '*.verse' -File) {
        $dest=Join-Path $Target $file.Name
        if (Test-Path -LiteralPath $dest) { throw "Refusing to overwrite existing file: $dest" }
        $Plan+=@{Source=$file.FullName; Destination=$dest; Sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash}
    }
}
$Plan | ConvertTo-Json -Depth 4 | Write-Output
if (-not $Apply) {
    Write-Host 'DRY RUN: nothing copied. Pass -Apply explicitly to stage these sources.'
    return
}
$created=@()
try {
    foreach($entry in $Plan) {
        # Check again immediately before copy; concurrency guard.
        if (Test-Path -LiteralPath $entry.Destination) { throw "Concurrent change: $($entry.Destination)" }
        Copy-Item -LiteralPath $entry.Source -Destination $entry.Destination -ErrorAction Stop
        $created += $entry.Destination
    }
    Write-Host "Staged $($created.Count) Verse sources; UEFN compilation NOT TESTED."
} catch {
    # Remove only files created by this script, and only if their content still matches the source.
    foreach($p in $created) {
        $row=$Plan | Where-Object { $_.Destination -eq $p } | Select-Object -First 1
        if ((Test-Path -LiteralPath $p) -and (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -eq $row.Sha256) {
            Remove-Item -LiteralPath $p -ErrorAction SilentlyContinue
        }
    }
    throw
}
