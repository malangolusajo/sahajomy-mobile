param(
  [string]$Workspace = (Get-Location).Path
)

$inventoryPath = Join-Path $Workspace 'Sahajomy-Mobile-App\Sahajomy-Mobile-App\GENERATED_SCREEN_INVENTORY.md'
$outputPath = Join-Path $Workspace 'lib\app\app_route_aliases.dart'
$rows = [System.Collections.Generic.List[object]]::new()

foreach ($line in Get-Content -LiteralPath $inventoryPath) {
  if ($line -match '^\|\s*([^|]+?)\s*\|\s*`(/[^`]*)`\s*\|\s*\[([^\]]+\.html)\]') {
    $rows.Add([pscustomobject]@{
      Path = $Matches[2]
      File = $Matches[3]
    })
  }
}

$extraRoutes = [ordered]@{
  '/screens' = $null
  '/customer/notifications' = 'customer-notifications.html'
  '/customer/reservations' = 'customer-sea-bookings.html'
  '/customer/profile' = 'customer-profile.html'
  '/customer/documents' = 'customer-documents.html'
  '/customer/track-shipment' = 'customer-shipment-tracking.html'
}

$routeMap = [ordered]@{}
foreach ($row in $rows | Sort-Object `
    @{ Expression = { ($_.Path -split '/').Count }; Descending = $true }, `
    @{ Expression = { ([regex]::Matches($_.Path, ':')).Count }; Ascending = $true }, `
    @{ Expression = { $_.Path.Length }; Descending = $true }) {
  $routeMap[$row.Path] = $row.File
}
foreach ($entry in $extraRoutes.GetEnumerator()) {
  if ($null -ne $entry.Value) {
    $routeMap[$entry.Key] = $entry.Value
  }
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('// Generated from Sahajomy-Mobile-App/GENERATED_SCREEN_INVENTORY.md.')
$lines.Add('// Regenerate with: .\tool\generate_app_route_aliases.ps1')
$lines.Add('const appRouteAliases = <String, String>{')
foreach ($entry in $routeMap.GetEnumerator()) {
  $lines.Add("  '$($entry.Key)': '$($entry.Value)',")
}
$lines.Add('};')

Set-Content -LiteralPath $outputPath -Value $lines -Encoding utf8
