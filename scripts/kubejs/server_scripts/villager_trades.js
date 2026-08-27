/**
 * Modified Villager Trades
 *
 */

// ---- Librarian Nerf

// Remove the enchanted book from Novice
function nerfNoviceLibrarian(offerEvent) {
  // console.info("[MoreJS]: **VILLAGER OFFER EVENT**");

  if (!offerEvent.isProfession("minecraft:librarian")) return

  const offer = offerEvent.offer
  // console.info(
  //   `[librarian L${offerEvent.getVillagerLevel()}] ` +
  //   `${offer.firstCost} + ${offer.secondCost} -> ${offer.output}`
  // )

  if (offerEvent.getVillagerLevel() !== 1) return

  if (offerEvent.offer.output.id === "minecraft:enchanted_book") {
    // console.info("[MoreJS] Blocking novice librarian book offer")
    offerEvent.cancel()
  }
}

// Give an extra enchanted book to a Master to balance it out

// Rhino lets you load the Java trade class for later use
const EnchantBookForEmeralds = Java.loadClass("net.minecraft.world.entity.npc.VillagerTrades$EnchantBookForEmeralds")
const EnchantmentTags = Java.loadClass("net.minecraft.tags.EnchantmentTags")

function buffMasterLibrarian(offerEvent) {
  if (!offerEvent.isProfession("minecraft:librarian")) return
  if (offerEvent.getVillagerLevel() !== 5) return

  // todo: Dead Code?
  // let bookOffers = 0
  // for (const offer of offerEvent.getAllOffers()) {
  //   if (offer.output.id === "minecraft:enchanted_book") {
  //     bookOffers++
  //   }
  // }

  offerEvent.addTrade(new EnchantBookForEmeralds(20, EnchantmentTags.TRADEABLE))
  // console.info("Gave Master librarian extra enchanted book")
}



// Register villager trade callbacks
MoreJS.updateOffer(nerfNoviceLibrarian);
MoreJS.postUpdateOffers(buffMasterLibrarian);
