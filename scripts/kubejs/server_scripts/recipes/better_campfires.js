/**
 * Build Your Campfire Recipes
 *
 *
 */

// Remove all campfire recipes (not just the ones from this mod) when this mod is loaded
//  Campfires are now made by hand
function removeCampfire(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:campfire' });
  recipeEvent.remove({ output: 'minecraft:soul_campfire' });
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('better_campfires')) {
  ServerEvents.recipes(removeCampfire);
}
