# Uses Windows certificate trust. Saves source receipts, never a database dump.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskEvidenceRoot = Join-Path $taskRoot 'apps/api/src/property_platform/modules/evidence'
$taskProfiles = Get-Content -LiteralPath (Join-Path $taskEvidenceRoot 'property_presentations.json') -Raw | ConvertFrom-Json
$taskPhotos = Get-Content -LiteralPath (Join-Path $taskEvidenceRoot 'property_media.json') -Raw | ConvertFrom-Json -AsHashtable
$taskUrls = @($taskProfiles | ForEach-Object { $_.source_url })
foreach ($taskProfile in $taskProfiles) {
    if ($taskProfile.photo_key) {
        $taskPhoto = $taskPhotos[$taskProfile.photo_key]
        $taskUrls += @($taskPhoto.source_url, $taskPhoto.image_url)
    }
}
$taskReceipts = @()
foreach ($taskUrl in ($taskUrls | Select-Object -Unique)) {
    $taskStarted = [DateTimeOffset]::UtcNow
    $taskResponse = Invoke-WebRequest -Uri $taskUrl -TimeoutSec 30 -MaximumRedirection 0 -Headers @{ 'User-Agent' = 'PropertyPlatform/0.1 (manual property source acquisition)' }
    $taskBytes = $taskResponse.RawContentStream.ToArray()
    if ($taskBytes.Length -gt 4MB) { throw 'Capture exceeds the acquisition budget.' }
    $taskReceipts += @{
        url = $taskUrl
        fetched_started_at = $taskStarted.ToString('o')
        fetched_at = [DateTimeOffset]::UtcNow.ToString('o')
        http_status = [int]$taskResponse.StatusCode
        sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($taskBytes)).ToLowerInvariant()
        payload = [Convert]::ToBase64String($taskBytes)
    }
    Write-Output "Acquired $($taskResponse.StatusCode): $taskUrl"
}
$taskOutputDir = Join-Path $taskRoot '.cache/acquisition'
New-Item -ItemType Directory -Path $taskOutputDir -Force | Out-Null
$taskOutput = Join-Path $taskOutputDir 'property-presentations.json'
$taskReceipts | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskOutput -Encoding utf8
Write-Output "Receipts saved to $taskOutput"
