/**
 * Loot Modifications
 *
 */



LootJS.modifiers(lootModEvent => {


  // ---- Vanilla

  // Cows guarantee 1 leather, might give an additional (plus the default drop chance)
  const extraLeather = LootEntry.of("minecraft:leather", 1)
    .applyEnchantmentBonus([0, 1]);

  lootModEvent.addEntityModifier("minecraft:cow").addLoot(extraLeather);


  // ---- Primity

  if (Platform.isLoaded('primity')) {

    // Special replacements for the Bonus Chest
    lootModEvent
      .addTableModifier('minecraft:chests/spawn_bonus_chest')
      .replaceLoot('minecraft:stone_pickaxe', 'primity:flint_shovel')
      .replaceLoot('minecraft:wooden_pickaxe', 'primity:flint_shovel_head')


    // Generic replacements
    // - Replace all instances of stone pickaxe with flint pickaxe head
    // - Remove all instances of invalid wooden tools
    lootModEvent
      .addTableModifier(/.*/)
      .replaceLoot('minecraft:stone_pickaxe', 'primity:flint_pickaxe')
      .removeLoot('minecraft:wooden_pickaxe')
      .removeLoot('minecraft:wooden_axe')
      .removeLoot('minecraft:wooden_hoe')
      .removeLoot('minecraft:wooden_shovel')
  }


  // ---- Waystones

  // Waystones drop obsidian instead of a waystone


  // ---- Supplementaries

  // Add flax to desert house (actually, this should be done in a datapack)

})
