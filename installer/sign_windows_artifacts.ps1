param(
    [Parameter(Mandatory = $true)]
    [string[]]$Paths
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$certificateBase64 = $env:WINDOWS_SIGNING_CERTIFICATE_BASE64
$certificatePassword = $env:WINDOWS_SIGNING_CERTIFICATE_PASSWORD
if ([string]::IsNullOrWhiteSpace($certificateBase64) -or
    [string]::IsNullOrWhiteSpace($certificatePassword)) {
    throw "Both Windows signing secrets are required."
}

$signToolCommand = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if ($null -ne $signToolCommand) {
    $signTool = $signToolCommand.Source
}
else {
    $sdkRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    $signTool = Get-ChildItem $sdkRoot -Filter "signtool.exe" -File -Recurse |
        Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
    if ([string]::IsNullOrWhiteSpace($signTool)) {
        throw "signtool.exe was not found in PATH or the Windows SDK."
    }
}
$certificatePath = Join-Path $env:RUNNER_TEMP "easy-language-learning-tool-signing.pfx"

try {
    [IO.File]::WriteAllBytes($certificatePath, [Convert]::FromBase64String($certificateBase64))
    foreach ($candidate in $Paths) {
        $resolved = (Resolve-Path $candidate).Path
        & $signTool sign /fd SHA256 /td SHA256 /tr "http://timestamp.digicert.com" `
            /f $certificatePath /p $certificatePassword $resolved
        if ($LASTEXITCODE -ne 0) {
            throw "signtool failed for $resolved with code $LASTEXITCODE."
        }
        $signature = Get-AuthenticodeSignature $resolved
        if ($signature.Status -ne "Valid") {
            throw "Authenticode verification failed for $resolved: $($signature.StatusMessage)"
        }
    }
}
finally {
    if (Test-Path $certificatePath) {
        Remove-Item $certificatePath -Force
    }
}
