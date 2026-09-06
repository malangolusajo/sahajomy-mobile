param(
    [string]$Workspace = (Split-Path -Parent $PSScriptRoot)
)

Add-Type -AssemblyName System.Drawing

$navyTop = [System.Drawing.ColorTranslator]::FromHtml('#164F73')
$navyBottom = [System.Drawing.ColorTranslator]::FromHtml('#062B44')
$coral = [System.Drawing.ColorTranslator]::FromHtml('#F36B4B')
$white = [System.Drawing.Color]::White

function New-SahajomyIcon {
    param(
        [Parameter(Mandatory = $true)][int]$Size,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $bitmap = [System.Drawing.Bitmap]::new($Size, $Size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $bounds = [System.Drawing.Rectangle]::new(0, 0, $Size, $Size)
    $background = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
        $bounds,
        $navyTop,
        $navyBottom,
        48.0
    )
    $graphics.FillRectangle($background, $bounds)

    $softGlow = [System.Drawing.SolidBrush]::new(
        [System.Drawing.Color]::FromArgb(13, 255, 255, 255)
    )
    $graphics.FillEllipse($softGlow, $Size * 0.62, -$Size * 0.12, $Size * 0.56, $Size * 0.56)
    $graphics.FillEllipse($softGlow, -$Size * 0.18, $Size * 0.66, $Size * 0.52, $Size * 0.52)

    $route = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $route.AddBezier(
        $Size * 0.70, $Size * 0.28,
        $Size * 0.61, $Size * 0.21,
        $Size * 0.32, $Size * 0.21,
        $Size * 0.29, $Size * 0.38
    )
    $route.AddBezier(
        $Size * 0.29, $Size * 0.38,
        $Size * 0.27, $Size * 0.51,
        $Size * 0.73, $Size * 0.49,
        $Size * 0.70, $Size * 0.65
    )
    $route.AddBezier(
        $Size * 0.70, $Size * 0.65,
        $Size * 0.68, $Size * 0.80,
        $Size * 0.38, $Size * 0.80,
        $Size * 0.29, $Size * 0.72
    )
    $routePen = [System.Drawing.Pen]::new($white, $Size * 0.105)
    $routePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $routePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $routePen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    $graphics.DrawPath($routePen, $route)

    $endpointBrush = [System.Drawing.SolidBrush]::new($coral)
    $endpointSize = $Size * 0.13
    $graphics.FillEllipse(
        $endpointBrush,
        $Size * 0.70 - $endpointSize / 2,
        $Size * 0.28 - $endpointSize / 2,
        $endpointSize,
        $endpointSize
    )
    $graphics.FillEllipse(
        $endpointBrush,
        $Size * 0.29 - $endpointSize / 2,
        $Size * 0.72 - $endpointSize / 2,
        $endpointSize,
        $endpointSize
    )

    $directory = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $bitmap.Save($Destination, [System.Drawing.Imaging.ImageFormat]::Png)

    $endpointBrush.Dispose()
    $routePen.Dispose()
    $route.Dispose()
    $softGlow.Dispose()
    $background.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}

$masterPath = Join-Path $Workspace 'assets\branding\sahajomy-app-icon.png'
New-SahajomyIcon -Size 1024 -Destination $masterPath

$androidIcons = @{
    'mipmap-mdpi\ic_launcher.png' = 48
    'mipmap-hdpi\ic_launcher.png' = 72
    'mipmap-xhdpi\ic_launcher.png' = 96
    'mipmap-xxhdpi\ic_launcher.png' = 144
    'mipmap-xxxhdpi\ic_launcher.png' = 192
}
$androidRoot = Join-Path $Workspace 'android\app\src\main\res'
foreach ($entry in $androidIcons.GetEnumerator()) {
    New-SahajomyIcon -Size $entry.Value -Destination (Join-Path $androidRoot $entry.Key)
    $roundPath = $entry.Key.Replace('ic_launcher.png', 'ic_launcher_round.png')
    New-SahajomyIcon -Size $entry.Value -Destination (Join-Path $androidRoot $roundPath)
}

$iosIcons = @{
    'Icon-App-20x20@1x.png' = 20
    'Icon-App-20x20@2x.png' = 40
    'Icon-App-20x20@3x.png' = 60
    'Icon-App-29x29@1x.png' = 29
    'Icon-App-29x29@2x.png' = 58
    'Icon-App-29x29@3x.png' = 87
    'Icon-App-40x40@1x.png' = 40
    'Icon-App-40x40@2x.png' = 80
    'Icon-App-40x40@3x.png' = 120
    'Icon-App-60x60@2x.png' = 120
    'Icon-App-60x60@3x.png' = 180
    'Icon-App-76x76@1x.png' = 76
    'Icon-App-76x76@2x.png' = 152
    'Icon-App-83.5x83.5@2x.png' = 167
    'Icon-App-1024x1024@1x.png' = 1024
}
$iosRoot = Join-Path $Workspace 'ios\Runner\Assets.xcassets\AppIcon.appiconset'
foreach ($entry in $iosIcons.GetEnumerator()) {
    New-SahajomyIcon -Size $entry.Value -Destination (Join-Path $iosRoot $entry.Key)
}

Write-Host "Generated Sahajomy brand assets from $masterPath"
