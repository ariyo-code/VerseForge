# Read-only diagnostics for a Windows computer running UEFN.
# Example: .\Diagnose-UEFN.ps1 -Project 'C:\UEFN\MyTestIsland' -Endpoint 'http://127.0.0.1:8000/mcp' -Probe
[CmdletBinding()]
param(
    [string]$Project,
    [string]$Endpoint,
    [string]$KnowledgeEndpoint,
    [switch]$Probe
)
$ErrorActionPreference = 'Stop'
$SkillRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$ArgsForPython = @((Join-Path $SkillRoot 'scripts\vf.py'), 'environment')
if ($Project) { $ArgsForPython += @('--project', $Project) }
if ($Endpoint) { $ArgsForPython += @('--endpoint', $Endpoint) }
if ($KnowledgeEndpoint) { $ArgsForPython += @('--knowledge-endpoint', $KnowledgeEndpoint) }
if ($Probe) { $ArgsForPython += '--probe' }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found on PATH. Install Python 3.11+ then retry.'
}
& python @ArgsForPython
if ($LASTEXITCODE -ne 0) { throw "VerseForge environment command failed with code $LASTEXITCODE" }
