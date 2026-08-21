param(
  [string]$Workspace = (Get-Location).Path
)

$specPath = Join-Path $Workspace 'lib\features\reference\presentation\native_screen_specs.dart'
$outputPath = Join-Path $Workspace 'lib\features\reference\presentation\dedicated_preview_pages.dart'
$source = Get-Content -LiteralPath $specPath -Raw
$matches = [regex]::Matches($source, "fileName: '([^']+)'" )

function Get-PageClassName([string]$fileName) {
  $name = $fileName.Replace('.html', '')
  $parts = $name -split '-'
  $pascal = ($parts | ForEach-Object { $_.Substring(0, 1).ToUpperInvariant() + $_.Substring(1) }) -join ''
  return "${pascal}PreviewPage"
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("// GENERATED CODE - DO NOT MODIFY BY HAND.")
$lines.Add("// Regenerate with: .\tool\generate_dedicated_preview_pages.ps1")
$lines.Add("")
$lines.Add("import 'package:flutter/material.dart';")
$lines.Add("")
$lines.Add("import 'native_reference_screen.dart';")
$lines.Add("import 'native_screen_specs.dart';")
$lines.Add("")
$lines.Add("Widget dedicatedPreviewPageFor(NativeScreenSpec spec) => switch (spec.fileName) {")
foreach ($match in $matches) {
  $fileName = $match.Groups[1].Value
  $className = Get-PageClassName $fileName
  $lines.Add("  '$fileName' => const $className(),")
}
$lines.Add("  _ => throw ArgumentError.value(spec.fileName, 'spec.fileName', 'Unknown preview'),")
$lines.Add("};")
$lines.Add("")
foreach ($match in $matches) {
  $fileName = $match.Groups[1].Value
  $className = Get-PageClassName $fileName
  $lines.Add("class $className extends StatelessWidget {")
  $lines.Add("  const $className({super.key});")
  $lines.Add("")
  $lines.Add("  @override")
  $lines.Add("  Widget build(BuildContext context) => PreviewPageLayout(")
  $lines.Add("    spec: nativeScreenSpecFor('$fileName'),")
  $lines.Add("  );")
  $lines.Add("}")
  $lines.Add("")
}

Set-Content -LiteralPath $outputPath -Value $lines -Encoding utf8
