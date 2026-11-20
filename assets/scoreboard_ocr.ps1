param([string]$ImagePath, [string]$Language = 'zh-Hans-CN', [switch]$StreamRequests)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Await-WinRT($operation, [type]$resultType) {
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.GetAwaiter().GetResult()
}
$engines = @{}
function Read-OcrImage([string]$Path, [string]$Locale) {
    if (-not $engines.ContainsKey($Locale)) {
        $ocrLanguage = [Windows.Globalization.Language]::new($Locale)
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($ocrLanguage)
        if (-not $engine) { throw "Windows OCR language component is unavailable: $Locale" }
        $engines[$Locale] = $engine
    }
    $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync([System.IO.Path]::GetFullPath($Path))) ([Windows.Storage.StorageFile])
    $stream = Await-WinRT ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    try {
        $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        try {
            $result = Await-WinRT ($engines[$Locale].RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $angle = $result.TextAngle
            $lines = @($result.Lines | ForEach-Object { @{ text = $_.Text; angle = $angle; words = @($_.Words | ForEach-Object { @{ text = $_.Text; x = $_.BoundingRect.X; y = $_.BoundingRect.Y; width = $_.BoundingRect.Width; height = $_.BoundingRect.Height } }) } })
            ConvertTo-Json -InputObject $lines -Depth 6 -Compress
        } finally { $bitmap.Dispose() }
    } finally { $stream.Dispose() }
}

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if (-not $StreamRequests) {
    if (-not $ImagePath) { throw 'ImagePath is required.' }
    Read-OcrImage $ImagePath $Language
    exit
}

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
while ($null -ne ($line = [Console]::ReadLine())) {
    $request = $null
    try {
        $request = ConvertFrom-Json -InputObject $line
        $recognized = Read-OcrImage $request.path $request.language
        [Console]::WriteLine('{"id":' + [int]$request.id + ',"lines":' + $recognized + '}')
    } catch {
        [Console]::WriteLine((ConvertTo-Json -InputObject @{ id = $request.id; error = $_.Exception.Message } -Compress))
    }
}
