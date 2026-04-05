/**
 * Custom tags for the Rabid Balance modpack custom loot economy.
 *
 */

const DO_LOOT_TAG_IMPORT = false;
const IMPORT_PATH = 'kubejs/export/resolved_loot_v10.json';

/**
 * Import loot properties from a JSON file table, and assign loot tags to all affected MC items.
 *
 * @param tagEvent - required event param
 */
function importLootTagsFromTable(tagEvent) {

  if (!DO_LOOT_TAG_IMPORT) {
    console.info(`[KubeJS] [LootImport] Loot import is disabled; aborting`)
    return
  }

  var raw = JsonIO.readString(IMPORT_PATH)
  var rows = JSON.parse(raw)
  var itemIds = Object.keys(rows)

  var i
  var itemId
  var row
  var func
  var affinities
  var value
  var amountClass

  for (i = 0; i < itemIds.length; i++) {
    itemId = itemIds[i]
    row = rows[itemId]

    func = row.function
    affinities = row.affinities
    value = row.value
    amountClass = row.amount_class

    if (func) {
      if (func === 'unmatched') continue
      tagEvent.add('rabbal:function/' + func, itemId)
    }
    if (affinities) {
      if (affinities.length > 0) {
        affinities.forEach(affinity => {
        tagEvent.add('rabbal:affinity/' + affinity, itemId)
      })
      }
    }
    if (value) {
      tagEvent.add('rabbal:loot/value/' + value, itemId)
    }
    if (amountClass) {
      tagEvent.add('rabbal:loot/amount/' + amountClass, itemId)
    }
  }

  console.info(`[KubeJS] [LootImport] Finished importing Rabid Balance loot tags from '${IMPORT_PATH}'`)

}

// Register tag importing function
ServerEvents.tags('item', importLootTagsFromTable)



