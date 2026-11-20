param(
    [Parameter(Mandatory=$true)][string]$Portable,
    [switch]$Publish
)

$ErrorActionPreference = 'Stop'
$repo = 'eistinlandfrank/wujindongri-mumu-assistant'
$watchdog = Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts/run_bounded.py'
function Invoke-GitHub {
    & python $watchdog --seconds 20 gh @args
    if ($LASTEXITCODE -ne 0) { throw "GitHub command failed (exit $LASTEXITCODE)." }
}

$file = Get-Item -LiteralPath $Portable
$match = [regex]::Match($file.Name, '^WJDRMuMuAssistant_v((?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){2})_Portable\.exe$')
if (-not $match.Success -or $file.PSIsContainer -or $file.Length -le 0 -or $file.Length -gt 512MB) {
    throw 'Select a versioned WJDR portable EXE.'
}
$version = $match.Groups[1].Value
$tag = "v$version"
if ($file.VersionInfo.FileVersion -ne "$version.0") { throw 'The EXE file version does not match its name.' }
$hasher = [Security.Cryptography.SHA256]::Create()
$stream = $file.OpenRead()
try {
    $digest = 'sha256:' + [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '').ToLowerInvariant()
} finally {
    $stream.Dispose()
    $hasher.Dispose()
}

$json = Invoke-GitHub release view $tag --repo $repo --json 'tagName,isDraft,isPrerelease,assets'
$release = $json | ConvertFrom-Json
$assets = @($release.assets | Where-Object { $_.name -ceq $file.Name })
$asset = $assets | Select-Object -First 1
if ($release.tagName -cne $tag -or $assets.Count -ne 1 -or $asset.state -cne 'uploaded' -or
    $asset.size -ne $file.Length -or $asset.digest -cne $digest) {
    throw 'The uploaded portable must match the local verified file by name, size and SHA-256.'
}

$latest = Invoke-GitHub api "repos/$repo/releases/latest" --jq .tag_name
if ($latest -ceq $tag -and -not $release.isDraft -and -not $release.isPrerelease -and $asset.label -ceq 'WJDR Stable') {
    Write-Output "$tag is already the stable update."
    exit 0
}
if (-not ($release.isDraft -or $release.isPrerelease)) { throw 'Stage the release as a draft or prerelease before approval.' }
if ($latest -notmatch '^v\d+\.\d+\.\d+$' -or [version]$version -le [version]$latest.Substring(1)) {
    throw "The proposed update must be newer than the current latest release ($latest)."
}
Write-Output "Verified $tag, $($file.Length) bytes, $digest."
if (-not $Publish) { exit 0 }

$assetId = $asset.apiUrl.Split('/')[-1]
if ($assetId -notmatch '^\d+$') { throw 'GitHub did not return a valid asset ID.' }
$label = Invoke-GitHub api --method PATCH "repos/$repo/releases/assets/$assetId" -f 'label=WJDR Stable' --jq .label
if ($label -cne 'WJDR Stable') { throw 'Could not mark the verified asset stable.' }
Invoke-GitHub release edit $tag --repo $repo --draft=false --prerelease=false --latest
$published = Invoke-GitHub api "repos/$repo/releases/latest" | ConvertFrom-Json
$promoted = $published.assets | Where-Object { $_.id -eq $assetId -and $_.digest -ceq $digest -and $_.label -ceq 'WJDR Stable' }
if ($published.tag_name -cne $tag -or $published.draft -or $published.prerelease -or -not $promoted) {
    throw 'GitHub has not confirmed this stable release as latest. Check the release before retrying.'
}
Write-Output "$tag is now available on the stable update channel."
