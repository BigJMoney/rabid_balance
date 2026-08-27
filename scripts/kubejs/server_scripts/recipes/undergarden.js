/**
 * The Undergarden Recipes
 *
 *
 */

const UG_WOODS = [
  'ancient_root',
  'grongle',
  'wigglewood',
  'smogstem'
];

// Boats are more difficult to craft
function ugBoatRecipes(recipeEvent) {

  UG_WOODS.forEach(wood => {
    recipeEvent.remove({output: `undergarden:${wood}_boat`});
    recipeEvent.shaped(
      Item.of(`undergarden:${wood}_boat`, 1),
      [
        'ABA',
        'AAA'
      ],
      {
        A: `undergarden:${wood}_planks`,
        B: 'minecraft:iron_nugget'
      }
    ).group('boat').id(`undergarden:${wood}_boat`);
  })
}

// Conditionally register mod recipe event callbacks
if (Platform.isLoaded('undergarden')) {
  ServerEvents.recipes(ugBoatRecipes);
}
