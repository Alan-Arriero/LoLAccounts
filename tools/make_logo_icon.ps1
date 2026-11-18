$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if (-not ('RiftVaultIconNative' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class RiftVaultIconNative {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool DestroyIcon(IntPtr handle);
}
'@
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = [System.Drawing.Image]::FromFile((Join-Path $root 'image.png'))
$bitmap = New-Object System.Drawing.Bitmap(256, 256, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$icon = $null
$handle = [IntPtr]::Zero
$stream = $null

try {
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $scale = [Math]::Min(256.0 / $source.Width, 256.0 / $source.Height)
    $width = [int][Math]::Round($source.Width * $scale)
    $height = [int][Math]::Round($source.Height * $scale)
    $x = [int][Math]::Round((256 - $width) / 2.0)
    $y = [int][Math]::Round((256 - $height) / 2.0)
    $graphics.DrawImage($source, $x, $y, $width, $height)
    $handle = $bitmap.GetHicon()
    $icon = [System.Drawing.Icon]::FromHandle($handle)
    $stream = [System.IO.File]::Create((Join-Path $root 'logo.ico'))
    $icon.Save($stream)
}
finally {
    if ($stream) { $stream.Dispose() }
    if ($icon) { $icon.Dispose() }
    if ($handle -ne [IntPtr]::Zero) { [RiftVaultIconNative]::DestroyIcon($handle) | Out-Null }
    $graphics.Dispose()
    $bitmap.Dispose()
    $source.Dispose()
}
