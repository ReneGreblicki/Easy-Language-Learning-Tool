param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$installer = (Resolve-Path $InstallerPath).Path
$root = Join-Path $env:RUNNER_TEMP "ELT Acceptance Żółć"
$installDirectory = Join-Path $root "Application Files"
$appDataDirectory = Join-Path $env:LOCALAPPDATA "Easy Language Learning Tool"
$sentinel = Join-Path $appDataDirectory "installer-acceptance-sentinel.txt"
$application = Join-Path $installDirectory "EasyLanguageLearningTool.exe"
$uninstaller = Join-Path $installDirectory "unins000.exe"

function Invoke-Process {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        throw "$FilePath exited with code $($process.ExitCode)."
    }
}

function Install-Candidate {
    $quotedDirectory = '/DIR="{0}"' -f $installDirectory
    Invoke-Process -FilePath $installer -Arguments @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        $quotedDirectory
    )
}

if (Test-Path $root) {
    Remove-Item $root -Recurse -Force
}
New-Item $root -ItemType Directory -Force | Out-Null

try {
    Install-Candidate

    $required = @(
        $application,
        (Join-Path $installDirectory "README.md"),
        (Join-Path $installDirectory "RELEASE_NOTES.md"),
        (Join-Path $installDirectory "installer\bundled\ffmpeg\ffmpeg.exe"),
        (Join-Path $installDirectory "installer\bundled\ffmpeg\ffprobe.exe"),
        (Join-Path $installDirectory "resources\frequency_data\production\words.jsonl.gz")
    )
    foreach ($path in $required) {
        if (-not (Test-Path $path -PathType Leaf)) {
            throw "Installed release is missing $path."
        }
    }

    $process = Start-Process -FilePath $application -PassThru
    Start-Sleep -Seconds 8
    if ($process.HasExited -and $process.ExitCode -ne 0) {
        throw "Installed application exited with code $($process.ExitCode)."
    }
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id
        $process.WaitForExit()
    }

    New-Item $appDataDirectory -ItemType Directory -Force | Out-Null
    "preserve-on-upgrade-and-uninstall" | Set-Content $sentinel

    # A second install exercises the in-place upgrade/repair path.
    Install-Candidate
    if ((Get-Content $sentinel -Raw).Trim() -ne "preserve-on-upgrade-and-uninstall") {
        throw "The in-place upgrade modified app-owned user data."
    }
    if (-not (Test-Path $uninstaller -PathType Leaf)) {
        throw "The installed release does not contain an uninstaller."
    }

    Invoke-Process -FilePath $uninstaller -Arguments @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART"
    )
    if (Test-Path $application) {
        throw "Uninstall left the application executable behind."
    }
    if ((Get-Content $sentinel -Raw).Trim() -ne "preserve-on-upgrade-and-uninstall") {
        throw "Uninstall removed or modified app-owned user data."
    }
}
finally {
    if (Test-Path $uninstaller) {
        try {
            Invoke-Process -FilePath $uninstaller -Arguments @(
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART"
            )
        }
        catch {
            Write-Warning "Acceptance cleanup could not run the uninstaller: $_"
        }
    }
    if (Test-Path $sentinel) {
        Remove-Item $sentinel -Force
    }
    if (Test-Path $root) {
        Remove-Item $root -Recurse -Force
    }
}
