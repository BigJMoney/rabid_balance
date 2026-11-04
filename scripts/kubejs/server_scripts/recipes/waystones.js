/**
 * Waystones Recipes
 *
 *
 */

const PORTSTONE_COLORS = [
  'white', 'black', 'gray', 'light_gray', 'red', 'pink', 'green', 'lime',
  'blue', 'light_blue', 'cyan', 'magenta', 'purple', 'yellow', 'orange', 'brown'
];


// Scrolls
function returnScrollRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'waystones:return_scroll' });
  recipeEvent.shaped(
    Item.of('waystones:return_scroll', 1),
    [
      'ABA',
      'ACA',
      ' D '
    ],
    {
      A: 'minecraft:gold_nugget',
      B: 'minecraft:ender_pearl',
      C: 'minecraft:amethyst_shard',
      D: 'minecraft:paper'
    }
  ).id(`waystones:return_scroll`);
}

function blankScrollRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'waystones:blank_scroll' });
  recipeEvent.shaped(
    Item.of('waystones:blank_scroll', 1),
    [
      'ABA',
      'ACA',
      ' D '
    ],
    {
      A: 'minecraft:gold_nugget',
      B: 'minecraft:glow_ink_sac',
      C: 'minecraft:amethyst_shard',
      D: 'minecraft:paper'
    }
  ).id(`waystones:blank_scroll`);
}

function warpScrollRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'waystones:warp_scroll' });
  recipeEvent.shaped(
    Item.of('waystones:warp_scroll', 1),
    [
      'ABA',
      'ACA',
      ' D '
    ],
    {
      A: 'minecraft:gold_nugget',
      B: 'minecraft:breeze_rod',
      C: 'minecraft:amethyst_shard',
      D: 'minecraft:paper'
    }
  ).id(`waystones:warp_scroll`);
}

// todo: Portal Scroll?

//Portstones
function portstoneRecipes(recipeEvent) {

  PORTSTONE_COLORS.forEach(color => {
    recipeEvent.remove({ output: `waystones:${color}_portstone` });
    recipeEvent.shaped(
      Item.of(`waystones:${color}_portstone`, 1),
      [
        'ABA',
        'BCB',
        'DDD'
      ],
      {
        A: `${color}_dye`,
        B: 'minecraft:stone_bricks',
        C: 'minecraft:ender_eye',
        D: `minecraft:polished_andesite`
      }
    ).group('ws_portstone').id(`waystones:${color}_portstone`);
  })

}

// Warp Plates
function warpPlatesRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'waystones:dormant_shard' });
  recipeEvent.shaped(
    Item.of('waystones:dormant_shard', 1),
    [
      'AA ',
      'B  ',
      '   '
    ],
    {
      A: 'minecraft:small_amethyst_bud',
      B: 'minecraft:flint'
    }
  ).id(`waystones:dormant_shard`);
}

// Warpstone (requires Cataclysm)
function warpstoneRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'waystones:warp_stone' });
  recipeEvent.shaped(
    Item.of('waystones:warp_stone', 1),
    [
      'AAA',
      'AAA',
      'AAA'
    ],
    {
      A: 'cataclysm:amethyst_crab_shell'
    }
  ).id(`waystones:warp_stone`);
}


// Conditionally register mod recipe event callbacks
if (
  Platform.isLoaded('waystones')
) {
  ServerEvents.recipes(returnScrollRecipe);
  ServerEvents.recipes(blankScrollRecipe);
  ServerEvents.recipes(warpScrollRecipe);

  ServerEvents.recipes(portstoneRecipes);

  ServerEvents.recipes(warpPlatesRecipe);
}

if (
  Platform.isLoaded('waystones') &&
  Platform.isLoaded('cataclysm')
) {
  ServerEvents.recipes(warpstoneRecipe);
}
