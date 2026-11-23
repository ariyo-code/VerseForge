# Collects only a compiler log supplied by the operator. Does NOT locate or export personal game files.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$LogFile,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [switch]$ConfirmReviewedContent
)
$ErrorActionPreference='Stop'
if (-not $ConfirmReviewedContent) {throw 'Review the log for private paths, tokens and personal data, then pass -ConfirmReviewedContent'}
$Src=(Resolve-Path -LiteralPath $LogFile).Path
if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {throw 'Create the output directory explicitly first'}
$Dst=(Resolve-Path -LiteralPath $OutputDirectory).Path
$Text=[IO.File]::ReadAllText($Src)
$Text=[regex]::Replace($Text,'(?i)Bearer\s+[A-Za-z0-9._~+/-]+','Bearer [REDACTED]')
$Text=[regex]::Replace($Text,'(?i)(access_token|refresh_token|api_key|password|secret)\s*[=:]\s*\S+','$1=[REDACTED]')
$Name='uefn-compiler-'+[DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmss')+'.log'
$File=Join-Path $Dst $Name
[IO.File]::WriteAllText($File,$Text,[Text.UTF8Encoding]::new($false))
Get-FileHash -LiteralPath $File -Algorithm SHA256 | Format-List
Write-Host 'Sanitized local copy created. NOT proof of UEFN compilation until manually tied to a specific editor build and project.'
