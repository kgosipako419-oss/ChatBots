# Installs the British English (en-GB) text-to-speech voice and makes it visible
# to classic apps like Ekko (pyttsx3/SAPI5). Self-elevates (one UAC prompt).
$ErrorActionPreference = "Stop"

function Test-Admin {
    (([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent())
        ).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "Requesting administrator rights (approve the prompt)..."
    Start-Process powershell -Verb RunAs -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    return
}

Write-Host "=== Installing British English voice ===" -ForegroundColor Cyan

# 1) Install the en-GB text-to-speech capability if it isn't already present.
try {
    $caps = Get-WindowsCapability -Online | Where-Object { $_.Name -like "Language.TextToSpeech*en-GB*" }
    if (-not $caps) {
        Write-Host "No en-GB voice package was offered by Windows Update." -ForegroundColor Yellow
    }
    foreach ($c in $caps) {
        if ($c.State -eq "Installed") {
            Write-Host "Already installed: $($c.Name)"
        } else {
            Write-Host "Downloading & installing: $($c.Name) ..."
            Add-WindowsCapability -Online -Name $c.Name | Out-Null
            Write-Host "  done."
        }
    }
} catch {
    Write-Host "Install step failed: $($_.Exception.Message)" -ForegroundColor Red
}

# 2) Copy any en-GB voice from the modern (OneCore) store into the classic SAPI5
#    store so pyttsx3 can use it. This only ADDS keys and is easily reversible.
$srcRoot = "HKLM:\SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"
$dstRoot = "HKLM:\SOFTWARE\Microsoft\Speech\Voices\Tokens"
$copied = 0
if (Test-Path $srcRoot) {
    Get-ChildItem $srcRoot | ForEach-Object {
        $lang = (Get-ItemProperty "$($_.PSPath)\Attributes" -ErrorAction SilentlyContinue).Language
        if ($lang -eq "809") {  # 0x809 = en-GB
            $dest = Join-Path $dstRoot $_.PSChildName
            try {
                Copy-Item -Path $_.PSPath -Destination $dest -Recurse -Force
                $copied++
            } catch { }
        }
    }
}
Write-Host "Exposed $copied British voice(s) to apps." -ForegroundColor Green

# 3) Report the British voices now visible to classic apps.
Write-Host ""
Write-Host "British voices now available:" -ForegroundColor Cyan
Get-ChildItem $dstRoot | ForEach-Object {
    $n = (Get-ItemProperty $_.PSPath).'(default)'
    $l = (Get-ItemProperty "$($_.PSPath)\Attributes" -ErrorAction SilentlyContinue).Language
    if ($l -eq "809") { Write-Host "  - $n" }
}
Write-Host ""
Read-Host "All done. Press Enter to close"
