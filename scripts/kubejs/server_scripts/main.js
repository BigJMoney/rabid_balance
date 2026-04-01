// Visit the wiki for more info - https://kubejs.com/

// To write a Json export of all loaded game item ids or not
const DO_EXPORT = false;
const ITEM_EXPORT_PATH = 'kubejs/export/item_ids.json'
const LEGACY_ITEM_EXPORT_PATH = 'kubejs/export/minecraft_item_ids.json'

// Export all game items
ServerEvents.loaded(event => {
  if (DO_EXPORT) {

    const ArrayList = Java.loadClass('java.util.ArrayList')
    const Collections = Java.loadClass('java.util.Collections')

    const items = new ArrayList(Item.getTypeList())
    items.remove('minecraft:air')
    Collections.sort(items)

    JsonIO.write(ITEM_EXPORT_PATH, items)
    JsonIO.write(LEGACY_ITEM_EXPORT_PATH, items)
    console.info(`[KubeJS] [ServerLoaded] Exported ${items.size()} loaded item ids to ${ITEM_EXPORT_PATH} (and legacy copy ${LEGACY_ITEM_EXPORT_PATH})`)

  }
})

console.info('Server Script Initialized')
