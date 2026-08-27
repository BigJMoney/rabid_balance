Using `rhino-kubejs`. Put these under `kubejs/server_scripts/professions/`.

**00_profession_registry.js**
```js
var PROFESSION_RECIPES = {}

function addProfessionRecipe(profession, recipe, advancement, unlock) {
  if (!Object.prototype.hasOwnProperty.call(PROFESSION_RECIPES, profession)) {
    PROFESSION_RECIPES[profession] = []
  }

  PROFESSION_RECIPES[profession].push({
    recipe: String(recipe),
    advancement: String(advancement),
    unlock: unlock
  })
}
```

**10_blacksmith.js**
```js
addProfessionRecipe(
  'blacksmith',
  'yourpack:steel_sword',
  'yourpack:recipes/combat/steel_sword',
  ['minecraft:iron_ingot']
)

addProfessionRecipe(
  'blacksmith',
  'minecraft:iron_pickaxe',
  'minecraft:recipes/tools/iron_pickaxe',
  ['minecraft:iron_ingot']
)
```

**10_alchemist.js**
```js
addProfessionRecipe(
  'alchemist',
  'yourpack:healing_flask',
  'yourpack:recipes/alchemy/healing_flask',
  ['minecraft:glass_bottle', 'minecraft:glowstone_dust']
)
```

**90_profession_logic.js**
```js
function professionTag(profession) {
  return 'profession_' + profession
}

function getProfession(player) {
  var profession = player.persistentData.profession

  if (profession == null || profession == '') {
    return 'none'
  }

  return String(profession)
}

function hasProfession(profession) {
  return Object.prototype.hasOwnProperty.call(PROFESSION_RECIPES, profession)
}

function itemPredicate(item) {
  item = String(item)

  if (item.charAt(0) == '#') {
    return { items: item.substring(1) }
  }

  return { items: item }
}

function unlockPredicates(entry) {
  var out = []
  var unlock = entry.unlock
  var i

  if (unlock == null) {
    return out
  }

  for (i = 0; i < unlock.length; i++) {
    out.push(itemPredicate(unlock[i]))
  }

  return out
}

function setProfessionTags(player, profession) {
  var professions = Object.keys(PROFESSION_RECIPES)
  var i
  var p
  var tag

  for (i = 0; i < professions.length; i++) {
    p = professions[i]
    tag = professionTag(p)

    if (p == profession) {
      player.addTag(tag)
    } else {
      player.removeTag(tag)
    }
  }
}

function removeUnavailableRecipes(player) {
  var current = getProfession(player)
  var professions = Object.keys(PROFESSION_RECIPES)
  var i
  var j
  var profession
  var entries
  var entry

  for (i = 0; i < professions.length; i++) {
    profession = professions[i]
    entries = PROFESSION_RECIPES[profession]

    if (profession == current) {
      continue
    }

    for (j = 0; j < entries.length; j++) {
      entry = entries[j]
      player.runCommandSilent('recipe take @s ' + entry.recipe)
      player.revokeAdvancement(entry.advancement)
    }
  }
}

function setProfession(player, profession) {
  if (!hasProfession(profession)) {
    player.tell('Unknown profession: ' + profession)
    return
  }

  player.persistentData.profession = profession
  setProfessionTags(player, profession)
  removeUnavailableRecipes(player)
  player.tell('Profession set to ' + profession)
}

function generatedAdvancementPath(id) {
  return String(id).replace(':', ':advancement/')
}

function classRecipeAdvancement(profession, entry) {
  var materialCriterion = 'has_' + profession + '_materials'
  var criteria = {}

  criteria.has_the_recipe = {
    trigger: 'minecraft:recipe_unlocked',
    conditions: {
      recipe: entry.recipe
    }
  }

  criteria[materialCriterion] = {
    trigger: 'minecraft:inventory_changed',
    conditions: {
      player: [
        {
          condition: 'minecraft:entity_properties',
          entity: 'this',
          predicate: {
            nbt: '{Tags:["' + professionTag(profession) + '"]}'
          }
        }
      ],
      items: unlockPredicates(entry)
    }
  }

  return {
    parent: 'minecraft:recipes/root',
    criteria: criteria,
    requirements: [
      [
        'has_the_recipe',
        materialCriterion
      ]
    ],
    rewards: {
      recipes: [
        entry.recipe
      ]
    }
  }
}

ServerEvents.generateData('last', function (event) {
  var professions = Object.keys(PROFESSION_RECIPES)
  var seen = {}
  var i
  var j
  var profession
  var entries
  var entry
  var adv

  for (i = 0; i < professions.length; i++) {
    profession = professions[i]
    entries = PROFESSION_RECIPES[profession]

    for (j = 0; j < entries.length; j++) {
      entry = entries[j]
      adv = entry.advancement

      if (seen[adv]) {
        continue
      }

      seen[adv] = true
      event.json(generatedAdvancementPath(adv), classRecipeAdvancement(profession, entry))
    }
  }
})

ServerEvents.loaded(function (event) {
  event.server.runCommandSilent('gamerule doLimitedCrafting true')
})

PlayerEvents.loggedIn(function (event) {
  setProfessionTags(event.player, getProfession(event.player))
  removeUnavailableRecipes(event.player)
})

ServerEvents.basicPublicCommand('profession', function (event) {
  var player = event.player
  var input
  var parts
  var action
  var profession

  if (player == null) {
    return
  }

  input = String(event.input).trim()
  parts = input.length == 0 ? [] : input.split(' ')
  action = parts.length > 0 ? parts[0] : 'sync'
  profession = parts.length > 1 ? parts[1] : ''

  if (action == 'choose') {
    setProfession(player, profession)
    return
  }

  if (action == 'sync') {
    setProfessionTags(player, getProfession(player))
    removeUnavailableRecipes(player)
    player.tell('Profession recipe state synced')
    return
  }

  player.tell('Usage: /profession choose <name> or /profession sync')
})
```

Patchouli can run:

```mcfunction
/profession choose blacksmith
```

One practical note: if the player already has the unlock materials before choosing the class, the generated `inventory_changed` advancement may not fire until their inventory changes again. That preserves natural unlocking, but it means “choose class while already holding the item” may need a pickup/move/drop event to trigger.

This will likely NOT limit modded recipes. To do that, use BlockEvents.rightClicked to check for a valid profession on modded crafting stations, etc. Something like:

```
BlockEvents.rightClicked(function (event) {
  var player = event.player
  var block = event.block

  if (!player || !block) {
    return
  }

  if (block.id == 'ars_nouveau:imbuement_chamber') {
    if (!player.tags.contains('profession_mage')) {
      player.tell('You need the Mage profession to use this.')
      event.cancel()
    }
  }

  if (block.id == 'ars_nouveau:enchanting_apparatus') {
    if (!player.tags.contains('profession_mage')) {
      player.tell('You need the Mage profession to use this.')
      event.cancel()
    }
  }
})
```