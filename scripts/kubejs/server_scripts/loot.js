/**
 * Loot Modifications
 *
 */


// ---- Vanilla

// Cows guarantee 1 leather, might give an additional (plus the default drop chance)
LootJS.modifiers(lootModEvent => {

  const extraLeather = LootEntry.of("minecraft:leather", 1)
    .applyEnchantmentBonus([0, 1]);

  lootModEvent.addEntityModifier("minecraft:cow").addLoot(extraLeather);

})

// ---- Waystones

// Waystones drop obsidian instead of a waystone


// ---- Supplementaries

// Add flax to desert house
