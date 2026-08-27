/**
 * Build Your Campfire Recipes
 *
 *
 */

// Remove all campfire recipes (not just the ones from this mod) when this mod is loaded
//  Campfires are now made by hand
function removeCampfire(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:campfire' });
  // TODO: Remove the soul campfire recipes when this mod's bug is fixed
  //   (Currently cannot manually build soul campfires)
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('better_campfires')) {
  ServerEvents.recipes(removeCampfire);
}
