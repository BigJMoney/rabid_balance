/**
 * Vanilla changes
 *
 *
 */


// Soups / stews can be eaten even when full and stack to 8
function buffBowlFoods(itemModEvent) {

  const foods = [
    'minecraft:mushroom_stew',
    'minecraft:suspicious_stew',
    'minecraft:beetroot_soup',
    'minecraft:rabbit_stew'
  ]

  for (const food of foods) {
    itemModEvent.modify(food, item => {
      item.maxStackSize = 8
      item.modifyFood(food => {
        food.alwaysEdible()
        food.saturation(0.6)
      })
    })
  }

}

function buffTFBowlFoods(itemModEvent) {

  const foods = [
    'twilightforest:moss_soup'
  ]

  for (const food of foods) {
    itemModEvent.modify(food, item => {
      item.maxStackSize = 8
      item.modifyFood(food => {
        food.alwaysEdible()
        food.saturation(0.6)
      })
    })
  }

}

ItemEvents.modification(buffBowlFoods)

if (
  Platform.isLoaded('twilightforest')
) {
  ItemEvents.modification(buffTFBowlFoods)
}
