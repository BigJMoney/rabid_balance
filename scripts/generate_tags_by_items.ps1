param(
  [string]$BaseUrl = 'http://localhost:61423',
  [string]$OutFile = (Join-Path $PSScriptRoot '..\docs\loot_docs\item_tags_by_item.json'),
  [string]$ItemIdsPath = ''
)

$ErrorActionPreference = 'Stop'
$BaseUrl = $BaseUrl.TrimEnd('/')
$OutFile = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutFile)

if ($ItemIdsPath) {
  $itemIds = Get-Content -LiteralPath $ItemIdsPath -Raw | ConvertFrom-Json
} else {
  $itemIds = Invoke-RestMethod "$BaseUrl/api/registries/minecraft/item/keys"
}
$itemIds = @($itemIds | ForEach-Object { $_.ToString() } | Sort-Object)

$byItem = [ordered]@{}

foreach ($id in $itemIds) {
  $parts = $id -split ':', 2
  if ($parts.Count -ne 2) {
    throw "Invalid item id '$id'"
  }

  $namespace = [Uri]::EscapeDataString($parts[0])
  # Resource paths may contain slashes; keep each ID part in one URL segment.
  $path = [Uri]::EscapeDataString($parts[1])

  $rawTags = Invoke-RestMethod "$BaseUrl/api/tags/minecraft/item/keys/$namespace/$path"
  $tags = @($rawTags | ForEach-Object { $_.ToString() } | Sort-Object)

  $byItem[$id] = $tags
}

$json = $byItem | ConvertTo-Json -Depth 3
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($OutFile)) | Out-Null
[System.IO.File]::WriteAllText($OutFile, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($byItem.Count) item tag rows to $OutFile"
