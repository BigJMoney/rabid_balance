/**
 * Upgrade Aquatic Recipes
 *
 *
 */

const UA_WOODS = [
  'river',
  'driftwood'
];

// Boats are more difficult to craft
function uaBoatRecipes(recipeEvent) {

  UA_WOODS.forEach(wood => {
    recipeEvent.remove({output: `upgrade_aquatic:${wood}_boat`});
    recipeEvent.shaped(
      Item.of(`upgrade_aquatic:${wood}_boat`, 1),
      [
        'ABA',
        'AAA'
      ],
      {
        A: `upgrade_aquatic:${wood}_planks`,
        B: 'minecraft:iron_nugget'
      }
    ).group('boat').id(`upgrade_aquatic:${wood}_boat`);
  })
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('upgrade_aquatic')) {
  ServerEvents.recipes(uaBoatRecipes);
}
