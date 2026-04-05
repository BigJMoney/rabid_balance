/**
 * Small Ships Recipes
 *
 *
 */

const SHIPKINDS = ['cog', 'galley', 'drakkar', 'brigg']
const SHIPWOODS = ['spruce', 'cherry', 'mangrove', 'oak', 'dark_oak', 'birch', 'jungle', 'acacia', 'bamboo'];

const IA_HULL = 'immersive_aircraft:hull';
const IA_SAILCLOTH = 'immersive_aircraft:sail';
const S_ROPES = '#c:ropes'


// Sails require supplementaries (or twilight_forest) rope and immersive aircraft sailcloth
function sailRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'smallships:sail' });
  recipeEvent.shaped(
    Item.of('smallships:sail', 1),
    [
      'AAA',
      'ABA',
      'CBC'
    ],
    {
      A: IA_SAILCLOTH,
      B: '#minecraft:logs',
      C: S_ROPES
    }
  );
}

// Ships require immersive aircraft hulls and supplementaries (or twilight_forest) rope

// Cog
function cogRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_cog` });
    recipeEvent.shaped(
      Item.of(`minecraft:${wood}_cog`, 1),
      [
        'ABA',
        ' C ',
        'DED'
      ],
      {
        A: S_ROPES,
        B: 'smallships:sail',
        C: 'minecraft:chest',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`minecraft:${wood}_cog`);
  })

}

// Galley
function galleyRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_galley` });
    recipeEvent.shaped(
      Item.of(`minecraft:${wood}_galley`, 1),
      [
        'ABA',
        'CCC',
        'DED'
      ],
      {
        A: S_ROPES,
        B: 'smallships:sail',
        C: 'minecraft:leather',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`minecraft:${wood}_galley`);
  })

}

// Drakkar
function drakkarRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_drakkar` });
    recipeEvent.shaped(
      Item.of(`minecraft:${wood}_drakkar`, 1),
      [
        'ABA',
        'DCD',
        'DED'
      ],
      {
        A: S_ROPES,
        B: 'smallships:sail',
        C: 'minecraft:shield',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`minecraft:${wood}_drakkar`);
  })

}

// Brigg
function briggRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_brigg` });
    recipeEvent.shaped(
      Item.of(`minecraft:${wood}_brigg`, 1),
      [
        'BAB',
        'CAC',
        'EDE'
      ],
      {
        A: S_ROPES,
        B: 'smallships:sail',
        C: 'minecraft:chest',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`minecraft:${wood}_brigg`);
  })

}


// Conditionally register mod recipe event callbacks
if (
  Platform.isLoaded('smallships') &&
  Platform.isLoaded('immersive_aircraft') &&
  Platform.isLoaded('supplementaries')  // todo: Find out if twilight forest can also work (depends on if it adds a
) {                                     //  ropes tag)
  ServerEvents.recipes(sailRecipe);

  ServerEvents.recipes(cogRecipes);
  ServerEvents.recipes(galleyRecipes);
  ServerEvents.recipes(drakkarRecipes);
  ServerEvents.recipes(briggRecipes);
}
