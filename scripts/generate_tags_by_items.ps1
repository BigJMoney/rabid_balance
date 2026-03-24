$baseUrl = 'http://localhost:61423'
$outFile = 'D:\keep\mods\Minecraft\my_tweaks\docs\item_tags_by_item.json'

$itemIds = Invoke-RestMethod "$baseUrl/api/registries/minecraft/item/keys" | Sort-Object
$byItem = [ordered]@{}

foreach ($id in $itemIds) {
  $byItem[$id] = $tags

  $parts = $id -split ':', 2
  $namespace = $parts[0]
  $path = $parts[1]

  $rawTags = Invoke-RestMethod "$baseUrl/api/tags/minecraft/item/keys/$namespace/$path"
  $tags = @($rawTags | ForEach-Object { $_.ToString() } | Sort-Object)

  if ($tags.Count -eq 0) {
    continue
  }

  $byItem[$id] = $tags
}

$json = $byItem | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($outFile, $json, [System.Text.UTF8Encoding]::new($false))
