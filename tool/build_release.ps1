param(
    [string]$AppName = "Sahajomy",
    [ValidateSet("aab", "apk")]
    [string]$Format = "aab"
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
