/**
 * Immersive Aircraft Recipes
 *
 *
 */


// Engine requires a minor Nether item
function engineRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'immersive_aircraft:engine' });
  recipeEvent.shaped(
    Item.of('immersive_aircraft:engine', 1),
    [
      ' A ',
      'BCB',
      'ADA'
    ],
    {
      A: 'minecraft:netherrack',
      B: 'minecraft:piston',
      C: 'minecraft:blast_furnace',
      D: 'immersive_aircraft:boiler'
    }
  );
}

// Hull requires more iron
function hullRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'immersive_aircraft:hull' });
  recipeEvent.shaped(
    Item.of('immersive_aircraft:hull', 1),
    [
      'AAA',
      ' B ',
      'AAA'
    ],
    {
      A: 'minecraft:logs',
      B: 'minecraft:iron_block'
    }
  );
}

// Replace the sail's name with "Sailcloth" (to distinguish from small ships mod)
function sailclothRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'immersive_aircraft:sail' });
  recipeEvent.shaped(
    Item.of('immersive_aircraft:sail', 1).withCustomName(Text.of('Sailcloth')),
    [
      'AA ',
      'AAB',
      'AA '
    ],
    {
      A: 'minecraft:white_carpet',
      B: ROPES
    }
  );
}


// Conditionally register mod recipe event callbacks
if (
  Platform.isLoaded('immersive_aircraft') &&
  Platform.isLoaded('twilightforest')
) {
  ServerEvents.recipes(engineRecipe);
  ServerEvents.recipes(hullRecipe);
  ServerEvents.recipes(sailclothRecipe);
}
