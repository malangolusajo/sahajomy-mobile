param(
    [string]$AppName = "Sahajomy",
    [ValidateSet("aab", "apk")]
    [string]$Format = "aab",
    [string]$AndroidSha256,
    [string]$AppleTeamId,
    [switch]$SkipExternalSecurityGates
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$pubspecPath = Join-Path $projectRoot "pubspec.yaml"
$versionMatch = Select-String -Path $pubspecPath -Pattern '^\s*version:\s*([^\s#]+)' | Select-Object -First 1

if ($null -eq $versionMatch) {
    throw "Unable to find the version in pubspec.yaml."
}

$version = $versionMatch.Matches[0].Groups[1].Value
if ($Format -eq "aab") {
    $outputDirectory = Join-Path $projectRoot "build\app\outputs\bundle\release"
    $sourceRelease = Join-Path $outputDirectory "app-release.aab"
    $buildCommand = "appbundle"
}
else {
    $outputDirectory = Join-Path $projectRoot "build\app\outputs\flutter-apk"
    $sourceRelease = Join-Path $outputDirectory "app-release.apk"
    $buildCommand = "apk"
}

$versionedRelease = Join-Path $outputDirectory "$AppName-v$version.$Format"

Push-Location $projectRoot
try {
    flutter analyze --fatal-infos
    if ($LASTEXITCODE -ne 0) {
        throw "Static analysis failed."
    }
    flutter test
    if ($LASTEXITCODE -ne 0) {
        throw "Security regression tests failed."
    }
    & (Join-Path $PSScriptRoot "check_pub_vulnerabilities.ps1")

    Push-Location (Join-Path $projectRoot "android")
    try {
        if ($env:OS -eq 'Windows_NT') {
            & .\gradlew.bat :app:lintRelease
        }
        else {
            & ./gradlew :app:lintRelease
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Android release lint failed."
        }
    }
    finally {
        Pop-Location
    }

    if ($SkipExternalSecurityGates) {
        Write-Warning "External association/TLS gates were explicitly skipped. This artifact is not approved for production."
    }
    else {
        if ([string]::IsNullOrWhiteSpace($AndroidSha256) -or [string]::IsNullOrWhiteSpace($AppleTeamId)) {
            throw "Production release requires -AndroidSha256 and -AppleTeamId. Use -SkipExternalSecurityGates only for non-production builds."
        }
        & (Join-Path $PSScriptRoot "verify_release_security.ps1") `
            -AndroidSha256 $AndroidSha256 `
            -AppleTeamId $AppleTeamId
        if ($LASTEXITCODE -ne 0) {
            throw "External security gates failed."
        }
    }

    flutter build $buildCommand --release

    if ($LASTEXITCODE -ne 0) {
        throw "Release bundle build failed."
    }

    Copy-Item -LiteralPath $sourceRelease -Destination $versionedRelease -Force
    Write-Host "Versioned release $Format created: $versionedRelease"
}
finally {
    Pop-Location
}
