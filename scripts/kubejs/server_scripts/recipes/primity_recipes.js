/**
 * Primity Recipes
 *
 *
 */

// Remove junk tools
//  These tools are useless with the Primitiy mod
function removeUselessTools(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:wooden_axe' });
  recipeEvent.remove({ output: 'minecraft:wooden_pickaxe' });
  recipeEvent.remove({ output: 'minecraft:wooden_shovel' });
  recipeEvent.remove({ output: 'minecraft:wooden_hoe' });

  recipeEvent.remove({ output: 'minecraft:stone_pickaxe' });
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('primity')) {
  ServerEvents.recipes(removeUselessTools);
}
