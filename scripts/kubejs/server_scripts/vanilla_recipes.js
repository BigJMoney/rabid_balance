/**
 * Vanilla Recipes
 *
 *
 */


const WOODS = ['spruce', 'cherry', 'mangrove', 'oak', 'dark_oak', 'birch', 'jungle', 'acacia'];

// NOTE: Disabled for now to test if backport mods fix this
// Lodestone is easier to craft (for 1.21.1)
// function lodestoneRecipe(recipeEvent) {
//   recipeEvent.remove({ output: 'minecraft:lodestone' });
//   recipeEvent.shaped(
//     Item.of('minecraft:lodestone', 1),
//     [
//       'AAA',
//       'ABA',
//       'AAA'
//     ],
//     {
//       A: 'minecraft:chiseled_stone_bricks',
//       B: 'minecraft:iron_ingot'
//     }
//   ).id("minecraft:lodestone");
//}

// Boats are more difficult to craft
function boatRecipes(recipeEvent) {

  WOODS.forEach(wood => {
    recipeEvent.remove({ output: `minecraft:${wood}_boat` });
    recipeEvent.shaped(
      Item.of(`minecraft:${wood}_boat`, 1),
      [
        'ABA',
        'AAA'
      ],
      {
        A: `minecraft:${wood}_planks`,
        B: 'minecraft:iron_nugget'
      }
    ).id(`minecraft:${wood}_boat`);
  })

  // ...except the bamboo raft cause that's fun
  recipeEvent.remove({ output: `minecraft:bamboo_raft` });
  recipeEvent.shaped(
    Item.of('minecraft:bamboo_raft', 1),
    [
      '   ',
      'AAA'
    ],
    {
      A: 'minecraft:bamboo_planks'
    }
  ).id('minecraft:bamboo_raft');

}


// TODO: ? Update the Twilight boat recipes? (IDK anything about Twilight, yet)

// Skipping the Honey Lead (again to test backport mods)

// Rails are easier to craft
function railRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:rail' });
  recipeEvent.shaped(
    Item.of('minecraft:rail', 24),
    [
      'A A',
      'BCB',
      'A A'
    ],
    {
      A: '#minecraft:planks',
      B: 'minecraft:iron_ingot',
      C: 'minecraft:stick'
    }
  );
}

function poweredRailRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:powered_rail' });
  recipeEvent.shaped(
    Item.of('minecraft:powered_rail', 6),
    [
      'A A',
      'BCB',
      'ADA'
    ],
    {
      A: '#minecraft:planks',
      B: 'minecraft:copper_ingot',
      C: 'minecraft:stick',
      D: 'minecraft:redstone'
    }
  );
}

function detectorRailRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:detector_rail' });
  recipeEvent.shaped(
    Item.of('minecraft:detector_rail', 6),
    [
      'A A',
      'BCB',
      'ADA'
    ],
    {
      A: '#minecraft:planks',
      B: 'minecraft:iron_ingot',
      C: 'minecraft:stone_pressure_plate',
      D: 'minecraft:redstone'
    }
  );
}

function activatorRailRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:activator_rail' });
  recipeEvent.shaped(
    Item.of('minecraft:activator_rail', 6),
    [
      'A A',
      'BCB',
      'ADA'
    ],
    {
      A: '#minecraft:planks',
      B: 'minecraft:iron_ingot',
      C: 'minecraft:redstone_torch',
      D: 'minecraft:stick'
    }
  );
}


// Leather armor recipes use joinery
function addLeatherJoineryTag(tagEvent) {
  const joinery = ["minecraft:bone", "minecraft:string", "minecraft:copper_nugget", "minecraft:iron_nugget"];
  joinery.forEach(j => {
    tagEvent.add("rabidbalance:leather_joinery", j)
  });
}

function leatherHelmetRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:leather_helmet' });
  recipeEvent.shaped(
    Item.of('minecraft:leather_helmet', 1),
    [
      'BAB',
      'A A'
    ],
    {
      A: 'minecraft:leather',
      B: '#rabidbalance:leather_joinery'
    }
  ).id('minecraft:leather_helmet');
}

function leatherChestplateRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:leather_chestplate' });
  recipeEvent.shaped(
    Item.of('minecraft:leather_chestplate', 1),
    [
      'A A',
      'BAB',
      'BAB'
    ],
    {
      A: 'minecraft:leather',
      B: '#rabidbalance:leather_joinery'
    }
  ).id('minecraft:leather_chestplate');
}

function leatherLeggingsRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:leather_leggings' });
  recipeEvent.shaped(
    Item.of('minecraft:leather_leggings', 1),
    [
      'ABA',
      'A A',
      'B B'
    ],
    {
      A: 'minecraft:leather',
      B: '#rabidbalance:leather_joinery'
    }
  ).id('minecraft:leather_leggings');
}

function leatherBootsRecipe(recipeEvent) {
  recipeEvent.remove({ output: 'minecraft:leather_boots' });
  recipeEvent.shaped(
    Item.of('minecraft:leather_boots', 1),
    [
      'B B',
      'A A'
    ],
    {
      A: 'minecraft:leather',
      B: '#rabidbalance:leather_joinery'
    }
  ).id('minecraft:leather_boots');
}

// Leather armor can be recycled (leather enhancement #1)
function recycledLeatherRecipes(recipeEvent) {
  recipeEvent.shapeless(
    Item.of('minecraft:leather', 1),
    [
      'minecraft:leather_helmet'
    ]
  );
  recipeEvent.shapeless(
    Item.of('minecraft:leather', 3),
    [
      'minecraft:leather_chestplate'
    ]
  );
  recipeEvent.shapeless(
    Item.of('minecraft:leather', 2),
    [
      'minecraft:leather_leggings'
    ]
  );
  recipeEvent.shapeless(
    Item.of('minecraft:leather', 1),
    [
      'minecraft:leather_boots'
    ]
  );
}


// Register recipe event callbacks
//ServerEvents.recipes(lodestoneRecipe);

ServerEvents.recipes(boatRecipes);

//ServerEvents.recipes(honeyLeadRecipe);

ServerEvents.recipes(railRecipe);
ServerEvents.recipes(poweredRailRecipe);
ServerEvents.recipes(detectorRailRecipe);
ServerEvents.recipes(activatorRailRecipe);

ServerEvents.recipes(leatherHelmetRecipe);
ServerEvents.recipes(leatherChestplateRecipe);
ServerEvents.recipes(leatherLeggingsRecipe);
ServerEvents.recipes(leatherBootsRecipe);
ServerEvents.recipes(recycledLeatherRecipes);

// Register tag event callbacks
ServerEvents.tags("item", addLeatherJoineryTag);
