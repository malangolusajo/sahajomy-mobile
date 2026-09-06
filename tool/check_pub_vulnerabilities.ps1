$ErrorActionPreference = 'Stop'

$dependencyGraph = dart pub deps --json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to resolve the Dart dependency graph.'
}

$packages = @($dependencyGraph.packages | Where-Object {
    $_.source -notin @('sdk', 'root')
})
$queries = @($packages | ForEach-Object {
    @{
        package = @{ ecosystem = 'Pub'; name = $_.name }
        version = $_.version
    }
})
$body = @{ queries = $queries } | ConvertTo-Json -Depth 6 -Compress
$result = Invoke-RestMethod `
    -Uri 'https://api.osv.dev/v1/querybatch' `
    -Method Post `
    -ContentType 'application/json' `
    -Body $body `
    -TimeoutSec 60

$findings = @()
for ($index = 0; $index -lt $result.results.Count; $index++) {
    $vulnerabilityValue = $result.results[$index].vulns
    if ($null -ne $vulnerabilityValue) {
        $vulnerabilities = @($vulnerabilityValue)
        $findings += [PSCustomObject]@{
            Package = $packages[$index].name
            Version = $packages[$index].version
            Vulnerabilities = ($vulnerabilities.id -join ', ')
        }
    }
}

if ($findings.Count -gt 0) {
    $findings | Format-Table -AutoSize
    throw 'Known Pub dependency vulnerabilities found.'
}

Write-Host "OSV Pub scan passed: $($queries.Count) resolved packages, 0 known vulnerabilities."
