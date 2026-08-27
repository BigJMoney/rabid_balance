param(
  [string]$BaseUrl = 'http://localhost:61423',
  [string]$OutFile = 'D:\keep\mods\Minecraft\my_tweaks\docs\tags_by_entity_type.json',
  [string]$ItemIdsPath = ''
)

if ($ItemIdsPath) {
  $itemIds = Get-Content -LiteralPath $ItemIdsPath -Raw | ConvertFrom-Json
  $itemIds = @($itemIds | ForEach-Object { $_.ToString() } | Sort-Object)
} else {
  $itemIds = Invoke-RestMethod "$BaseUrl/api/registries/minecraft/entity_type/keys" | Sort-Object
}

$byItem = [ordered]@{}

foreach ($id in $itemIds) {
  $parts = $id -split ':', 2
  if ($parts.Count -ne 2) {
    throw "Invalid entity id '$id'"
  }

  $namespace = $parts[0]
  $path = $parts[1]

  $rawTags = Invoke-RestMethod "$BaseUrl/api/tags/minecraft/entity_type/keys/$namespace/$path"
  $tags = @($rawTags | ForEach-Object { $_.ToString() } | Sort-Object)

  $byItem[$id] = $tags
}

$json = $byItem | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($OutFile, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($byItem.Count) entity tag rows to $OutFile"
