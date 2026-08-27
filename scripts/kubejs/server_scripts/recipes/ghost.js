/**
 * Ghosts Recipes
 *
 *
 */

const GHOST_WOODS = [
  'haunted',
];

// Boats are more difficult to craft
function ghostBoatRecipes(recipeEvent) {

  GHOST_WOODS.forEach(wood => {
    recipeEvent.remove({output: `ghosts:${wood}_boat`});
    recipeEvent.shaped(
      Item.of(`ghosts:${wood}_boat`, 1),
      [
        'ABA',
        'AAA'
      ],
      {
        A: `ghosts:${wood}_planks`,
        B: 'minecraft:iron_nugget'
      }
    ).group('boat').id(`ghosts:${wood}_boat`);
  })
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('ghosts')) {
  ServerEvents.recipes(ghostBoatRecipes);
}
