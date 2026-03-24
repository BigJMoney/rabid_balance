/**
 * Loot Modifications
 *
 */


// ---- Vanilla

// Cows guarantee 1 leather, might give an additional (plus the default drop chance)
const extraLeather = LootEntry.of("minecraft:leather", 1).applyEnchantmentBonus([1, 1]);
const bonusLeather = LootEntry.of("minecraft:leather", 1).randomChance(0.2);


// ---- Waystones

// Waystones drop obsidian instead of a waystone


// ---- Supplementaries

// Add flax to desert house


// Register loot callbacks
LootJS.modifiers(kevent => {

  kevent.addEntityModifier("minecraft:cow").addLoot(extraLeather);
  kevent.addEntityModifier("minecraft:cow").addLoot(bonusLeather);

})
