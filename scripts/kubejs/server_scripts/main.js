// Visit the wiki for more info - https://kubejs.com/

// To write a Json export of all game item ids or not
const DO_EXPORT = false;

// Export all game items
ServerEvents.loaded(event => {
  if (DO_EXPORT) {

    const ArrayList = Java.loadClass('java.util.ArrayList')
    const Collections = Java.loadClass('java.util.Collections')

    const items = new ArrayList(Item.getTypeList())
    items.remove('minecraft:air')
    Collections.sort(items)

    JsonIO.write('kubejs/export/minecraft_item_ids.json', items)
    console.info(`[KubeJS] [ServerLoaded] Exported ${items.size()} item ids to kubejs/export/minecraft_item_ids.json`)

  }
})

console.info('Server Script Initialized')
