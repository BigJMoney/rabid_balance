/**
 * Twilight Forest Recipes
 *
 *
 */

const TW_WOODS = [
  'mining',
  'time',
  'twilight_oak',
  'dark',
  'sorting',
  'transformation',
  'canopy',
  'mangrove',
];

// Boats are more difficult to craft
function tfBoatRecipes(recipeEvent) {

  TW_WOODS.forEach(wood => {
    recipeEvent.remove({output: `twilightforest:${wood}_boat`});
    recipeEvent.shaped(
      Item.of(`twilightforest:${wood}_boat`, 1),
      [
        'ABA',
        'AAA'
      ],
      {
        A: `twilightforest:${wood}_planks`,
        B: 'minecraft:iron_nugget'
      }
    ).group('boat').id(`twilightforest:${wood}_boat`);
  })
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('twilightforest')) {
  ServerEvents.recipes(tfBoatRecipes);
}
