/**
 * Small Ships Recipes
 *
 *
 */

const IA_SAILCLOTH = 'immersive_aircraft:sail';
const IA_HULL = 'immersive_aircraft:hull';
const CAST_IRON_BLOCK = 'primity:cast_iron_block'
const CAST_IRON_NUGGET = 'primity:cast_iron_nugget'

const SHIPWOODS = ['spruce', 'cherry', 'mangrove', 'oak', 'dark_oak', 'birch', 'jungle', 'acacia', 'bamboo'];

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
      C: ROPES
    }
  ).id(`smallships:sail`);
}

// Cannon and cannonball require primity's cast iron
function cannonRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'smallships:cannon' });
  recipeEvent.shaped(
    Item.of('smallships:cannon', 1),
    [
      '  A',
      'BBB',
      ' CC'
    ],
    {
      A: 'minecraft:string',
      B: CAST_IRON_BLOCK,
      C: '#minecraft:logs'
    }
  ).id(`smallships:cannon`);
}

function cannonBallRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'smallships:cannon_ball' });
  recipeEvent.shaped(
    Item.of('smallships:cannon_ball', 1),
    [
      'BBB',
      'BAB',
      'BBB'
    ],
    {
      A: 'minecraft:gunpowder',
      B: CAST_IRON_NUGGET
    }
  ).id(`smallships:cannon_ball`);
}

// Ships require immersive aircraft hulls and supplementaries (or twilight_forest) rope

// Cog
function cogRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_cog` });
    recipeEvent.shaped(
      Item.of(`smallships:${wood}_cog`, 1),
      [
        'ABA',
        ' C ',
        'DED'
      ],
      {
        A: ROPES,
        B: 'smallships:sail',
        C: 'minecraft:chest',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`smallships:${wood}_cog`);
  })

}

// Galley
function galleyRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_galley` });
    recipeEvent.shaped(
      Item.of(`smallships:${wood}_galley`, 1),
      [
        'ABA',
        'CCC',
        'DED'
      ],
      {
        A: ROPES,
        B: 'smallships:sail',
        C: 'minecraft:leather',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`smallships:${wood}_galley`);
  })

}

// Drakkar
function drakkarRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_drakkar` });
    recipeEvent.shaped(
      Item.of(`smallships:${wood}_drakkar`, 1),
      [
        'ABA',
        'DCD',
        'DED'
      ],
      {
        A: ROPES,
        B: 'smallships:sail',
        C: 'minecraft:shield',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`smallships:${wood}_drakkar`);
  })

}

// Brigg
function briggRecipes(recipeEvent) {

  SHIPWOODS.forEach(wood => {
    recipeEvent.remove({ output: `smallships:${wood}_brigg` });
    recipeEvent.shaped(
      Item.of(`smallships:${wood}_brigg`, 1),
      [
        'BAB',
        'CAC',
        'EDE'
      ],
      {
        A: ROPES,
        B: 'smallships:sail',
        C: 'minecraft:chest',
        D: `${wood}_planks`,
        E: IA_HULL,
      }
    ).id(`smallships:${wood}_brigg`);
  })

}


// Conditionally register mod recipe event callbacks
if (
  Platform.isLoaded('smallships') &&
  Platform.isLoaded('immersive_aircraft') &&
  Platform.isLoaded('twilightforest')
) {
  ServerEvents.recipes(sailRecipe);

  ServerEvents.recipes(cogRecipes);
  ServerEvents.recipes(galleyRecipes);
  ServerEvents.recipes(drakkarRecipes);
  ServerEvents.recipes(briggRecipes);
}

if (Platform.isLoaded('primity')) {
  ServerEvents.recipes(cannonRecipe);
  ServerEvents.recipes(cannonBallRecipe);
}
