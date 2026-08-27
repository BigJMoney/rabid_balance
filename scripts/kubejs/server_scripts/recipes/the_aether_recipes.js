/**
 * The Aether Recipes
 *
 *
 */

const AETHER_WOODS = [
  'skyroot',
];

// Boats are more difficult to craft
function aetherBoatRecipes(recipeEvent) {

  AETHER_WOODS.forEach(wood => {
    recipeEvent.remove({output: `aether:${wood}_boat`});
    recipeEvent.shaped(
      Item.of(`aether:${wood}_boat`, 1),
      [
        'ABA',
        'AAA'
      ],
      {
        A: `aether:${wood}_planks`,
        B: 'minecraft:iron_nugget'
      }
    ).group('boat').id(`aether:${wood}_boat`);
  })
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('aether')) {
  ServerEvents.recipes(aetherBoatRecipes);
}
