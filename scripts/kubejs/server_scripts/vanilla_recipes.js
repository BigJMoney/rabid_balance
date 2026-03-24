/**
 * Vanilla Recipes
 *
 *
 */

const woods = ['spruce', 'cherry', 'mangrove', 'oak', 'dark_oak', 'birch', 'jungle', 'acacia']


// NOTE: Disabled for now to test if backport mods fix this
// Lodestone is easier to craft (for 1.21.1)
// function lodestoneRecipe(kevent) {
//   kevent.remove({ output: 'minecraft:lodestone' });
//   kevent.shaped(
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
//   );
//}

// Boats are more difficult to craft
function boatRecipe(kevent) {
  woods.forEach(wood => {
    kevent.remove({ output: `minecraft:${wood}_boat` });
    kevent.shaped(
      Item.of(`minecraft:${wood}_boat`, 1),
      [
        'ABA',
        'AAA'
      ],
      {
        A: `minecraft:${wood}_planks`,
        B: 'minecraft:iron_nugget'
      }
    );
  })
}

// TODO: ? Update the Twilight boat recipes? (IDK anything about Twilight, yet)

// Skipping the Honey Lead (again to test backport mods)

// Rails are easier to craft
function railRecipe(kevent) {
  kevent.remove({ output: 'minecraft:rail' });
  kevent.shaped(
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

function poweredRailRecipe(kevent) {
  kevent.remove({ output: 'minecraft:powered_rail' });
  kevent.shaped(
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

function detectorRailRecipe(kevent) {
  kevent.remove({ output: 'minecraft:detector_rail' });
  kevent.shaped(
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

function activatorRailRecipe(kevent) {
  kevent.remove({ output: 'minecraft:activator_rail' });
  kevent.shaped(
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
function leatherHelmetRecipe(kevent) {
  kevent.remove({ output: 'minecraft:leather_helmet' });
  kevent.shaped(
    Item.of('minecraft:leather_helmet', 1),
    [
      'BAB',
      'A A'
    ],
    {
      A: 'minecraft:leather',
      B: '#minecraft:leather_joinery'
    }
  );
}

function leatherChestplateRecipe(kevent) {
  kevent.remove({ output: 'minecraft:leather_chestplate' });
  kevent.shaped(
    Item.of('minecraft:leather_chestplate', 1),
    [
      'A A',
      'BAB',
      'BAB'
    ],
    {
      A: 'minecraft:leather',
      B: '#minecraft:leather_joinery'
    }
  );
}

function leatherLeggingsRecipe(kevent) {
  kevent.remove({ output: 'minecraft:leather_leggings' });
  kevent.shaped(
    Item.of('minecraft:leather_leggings', 1),
    [
      'ABA',
      'A A',
      'B B'
    ],
    {
      A: 'minecraft:leather',
      B: '#minecraft:leather_joinery'
    }
  );
}

function leatherBootsRecipe(kevent) {
  kevent.remove({ output: 'minecraft:leather_boots' });
  kevent.shaped(
    Item.of('minecraft:leather_boots', 1),
    [
      'B B',
      'A A'
    ],
    {
      A: 'minecraft:leather',
      B: '#minecraft:leather_joinery'
    }
  );
}

// Leather armor can be recycled (leather enhancement #1)
function recycledLeatherRecipes(kevent) {
  kevent.shapeless(
    Item.of('minecraft:leather', 1),
    [
      'minecraft:leather_helmet'
    ]
  );
  kevent.shapeless(
    Item.of('minecraft:leather', 1),
    [
      'minecraft:leather_chestplate'
    ]
  );
  kevent.shapeless(
    Item.of('minecraft:leather', 1),
    [
      'minecraft:leather_leggings'
    ]
  );
  kevent.shapeless(
    Item.of('minecraft:leather', 1),
    [
      'minecraft:leather_boots'
    ]
  );
}


// Register recipe callbacks
//ServerEvents.recipes(lodestoneRecipe);

ServerEvents.recipes(boatRecipe);

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
