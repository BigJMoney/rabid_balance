param(
  [string]$BaseUrl = 'http://localhost:61423',
  [string]$OutFile = 'D:\keep\mods\Minecraft\my_tweaks\docs\loot_docs\item_tags_by_item-no_loot_tags.json',
  [string]$ItemIdsPath = ''
)

if ($ItemIdsPath) {
  $itemIds = Get-Content -LiteralPath $ItemIdsPath -Raw | ConvertFrom-Json
  $itemIds = @($itemIds | ForEach-Object { $_.ToString() } | Sort-Object)
} else {
  $itemIds = Invoke-RestMethod "$BaseUrl/api/registries/minecraft/item/keys" | Sort-Object
}

$byItem = [ordered]@{}

foreach ($id in $itemIds) {
  $parts = $id -split ':', 2
  if ($parts.Count -ne 2) {
    throw "Invalid item id '$id'"
  }

  $namespace = $parts[0]
  $path = $parts[1]

  $rawTags = Invoke-RestMethod "$BaseUrl/api/tags/minecraft/item/keys/$namespace/$path"
  $tags = @($rawTags | ForEach-Object { $_.ToString() } | Sort-Object)

  $byItem[$id] = $tags
}

$json = $byItem | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($OutFile, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($byItem.Count) item tag rows to $OutFile"
