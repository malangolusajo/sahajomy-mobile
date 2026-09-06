param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9:]{64,95}$')]
    [string]$AndroidSha256,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Z0-9]{10}$')]
    [string]$AppleTeamId,
    [string]$Domain = 'sahajomy.co.tz',
    [string]$AndroidPackage = 'com.sahajomy.mobile',
    [string]$AppleBundleId = 'com.sahajomy.mobile'
)

$ErrorActionPreference = 'Stop'
$fingerprint = $AndroidSha256.Replace(':', '').ToUpperInvariant()

$assetLinksUri = "https://$Domain/.well-known/assetlinks.json"
$assetLinks = Invoke-RestMethod -Uri $assetLinksUri -Method Get -TimeoutSec 20
$androidMatch = $assetLinks | Where-Object {
    $_.target.namespace -eq 'android_app' -and
    $_.target.package_name -eq $AndroidPackage -and
    ($_.target.sha256_cert_fingerprints | ForEach-Object {
        $_.Replace(':', '').ToUpperInvariant()
    }) -contains $fingerprint
}
if (-not $androidMatch) {
    throw "assetlinks.json does not contain the exact production package and certificate."
}

$aasaUri = "https://$Domain/.well-known/apple-app-site-association"
$aasa = Invoke-RestMethod -Uri $aasaUri -Method Get -TimeoutSec 20
$appId = "$AppleTeamId.$AppleBundleId"
$details = @($aasa.applinks.details)
$appleMatch = $details | Where-Object {
    $_.appID -eq $appId -or @($_.appIDs) -contains $appId
}
if (-not $appleMatch) {
    throw "apple-app-site-association does not contain the exact production app ID."
}

$apiUri = "https://$Domain/api/v1/"
$response = Invoke-WebRequest -Uri $apiUri -Method Head -TimeoutSec 20 -SkipHttpErrorCheck
if ($response.BaseResponse.RequestMessage.RequestUri.Scheme -ne 'https') {
    throw 'The production API redirected away from HTTPS.'
}

Write-Host 'Verified Android App Links, iOS Universal Links, and HTTPS API endpoint.'
