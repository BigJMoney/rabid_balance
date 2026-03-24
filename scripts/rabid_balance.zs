// All balance tweaks for my 1.21.1 game
//
// Copyright...(?)... just kidding, there's no copyright

import crafttweaker.api.ingredient.IIngredient;
import crafttweaker.api.item.ItemDefinition;
import crafttweaker.api.loot.condition.LootConditions;
import crafttweaker.api.loot.condition.LootTableIdLootCondition;
import crafttweaker.api.loot.modifier.CommonLootModifiers;


// + Waystones +
//

// Waystones drop obsidian instead of a waystone
var is_waystone = LootConditions.only(LootTableIdLootCondition.create(<resource:waystones:blocks/waystone>));
var drop_obsidian = CommonLootModifiers.chaining(
    CommonLootModifiers.replaceWith(<item:waystones:waystone>, <item:minecraft:obsidian>)
);

loot.modifiers.register(
     "waystones_drop_obsidian",
     is_waystone,
     drop_obsidian
);

// Scroll recipe changes
craftingTable.removeByName("waystones:return_scroll");
craftingTable.addShaped("ws_return_scroll", <item:waystones:return_scroll>, [
    [<item:minecraft:gold_nugget>, <item:minecraft:ender_pearl>, <item:minecraft:gold_nugget>],
    [<item:minecraft:gold_nugget>, <item:minecraft:amethyst_shard>, <item:minecraft:gold_nugget>],
    [<item:minecraft:air>, <item:minecraft:paper>]
]);

craftingTable.removeByName("waystones:blank_scroll");
craftingTable.addShaped("ws_blank_scroll", <item:waystones:blank_scroll>, [
    [<item:minecraft:gold_nugget>, <item:minecraft:glow_ink_sac>, <item:minecraft:gold_nugget>],
    [<item:minecraft:gold_nugget>, <item:minecraft:amethyst_shard>, <item:minecraft:gold_nugget>],
    [<item:minecraft:air>, <item:minecraft:paper>]
]);

craftingTable.removeByName("waystones:warp_scroll");
craftingTable.addShaped("ws_warp_scroll", <item:waystones:warp_scroll>, [
    [<item:minecraft:gold_nugget>, <item:minecraft:breeze_rod>, <item:minecraft:gold_nugget>],
    [<item:minecraft:gold_nugget>, <item:minecraft:amethyst_shard>, <item:minecraft:gold_nugget>],
    [<item:minecraft:air>, <item:minecraft:paper>]
]);

// Portstones
craftingTable.removeByName("waystones:white_portstone");
craftingTable.addShaped("ws_white_portstone", <item:waystones:white_portstone>, [
    [<item:minecraft:air>, <item:minecraft:stone_bricks>],
    [<item:minecraft:stone_bricks>, <item:minecraft:ender_eye>, <item:minecraft:stone_bricks>],
    [<item:minecraft:polished_andesite>, <item:minecraft:polished_andesite>, <item:minecraft:polished_andesite>]
]);

// **TODO: The rest of the portstone colors

// Warp Plates
craftingTable.removeByName("waystones:dormant_shard");
craftingTable.addShaped("ws_dormant_shard", <item:waystones:dormant_shard>, [
    [<item:minecraft:small_amethyst_bud>, <item:minecraft:small_amethyst_bud>],
    [<item:minecraft:flint>],
    [<item:minecraft:air>]
]);

// Warpstone
// Note: Requires L_Ender's Cataclysm
craftingTable.removeByName("waystones:warp_stone");
craftingTable.addShaped("ws_warp_stone", <item:waystones:warp_stone>, [
    [<item:cataclysm:amethyst_crab_shell>, <item:cataclysm:amethyst_crab_shell>, <item:cataclysm:amethyst_crab_shell>],
    [<item:cataclysm:amethyst_crab_shell>, <item:cataclysm:amethyst_crab_shell>, <item:cataclysm:amethyst_crab_shell>],
    [<item:cataclysm:amethyst_crab_shell>, <item:cataclysm:amethyst_crab_shell>, <item:cataclysm:amethyst_crab_shell>]
]);

// **TODO: lower durability (maybe)


// + Supplementaries +
//

// Add flax to desert house
var is_desert_house = LootConditions.only(LootTableIdLootCondition.create(<resource:minecraft:chests/village/village_desert_house>));

var swap_wheat_for_flax = CommonLootModifiers.chaining(
    CommonLootModifiers.replaceWith(<item:minecraft:wheat>, <item:supplementaries:flax>),
    CommonLootModifiers.replaceWith(<item:minecraft:bread>, <item:supplementaries:flax_block>)
    //CommonLootModifiers.remove(<item:minecraft:wheat>), 
    //CommonLootModifiers.remove(<item:minecraft:hay_block>), 
    //CommonLootModifiers.addWithRandomAmount(<item:supplementaries:flax>, 1, 7), 
    //CommonLootModifiers.addWithRandomAmount(<item:supplementaries:flax_block>, 1, 4)
);

loot.modifiers.register(
     "deserthouse_replace_wheat",
     is_desert_house,
     swap_wheat_for_flax
);

// **TODO: Add to more chests, but only in the desert biome, using LocationCheckLootCondition and LocationPredicateBuilder


// + Immersive Aircraft +
//

// Engine requires a minor Nether item
craftingTable.removeByName("immersive_aircraft:engine");
craftingTable.addShaped("ia_engine", <item:immersive_aircraft:engine>, [
    [<item:minecraft:air>, <item:minecraft:netherrack>],
    [<item:minecraft:piston>, <item:minecraft:blast_furnace>, <item:minecraft:piston>],
    [<item:minecraft:netherrack>, <item:immersive_aircraft:boiler>, <item:minecraft:netherrack>]
]);

// Hull requires more iron
craftingTable.removeByName("immersive_aircraft:hull");
craftingTable.addShaped("ia_hull", <item:immersive_aircraft:hull>, [
    [<tag:item:minecraft:logs>, <tag:item:minecraft:logs>, <tag:item:minecraft:logs>],
    [<item:minecraft:air>, <item:minecraft:iron_block>],
    [<tag:item:minecraft:logs>, <tag:item:minecraft:logs>, <tag:item:minecraft:logs>]
]);


// Replace the sail's name with "Sailcloth" (to distinguish from small ships mod)
var sailcloth = <item:immersive_aircraft:sail>.withItemName("Sailcloth");

craftingTable.removeByName("immersive_aircraft:sail");
craftingTable.addShaped("ia_sailcloth1", sailcloth, [
    [<item:minecraft:white_carpet>, <item:minecraft:white_carpet>],
    [<item:minecraft:white_carpet>, <item:minecraft:white_carpet>, <tag:item:c:ropes>],
    [<item:minecraft:white_carpet>, <item:minecraft:white_carpet>],
]);

craftingTable.addShaped("ia_sailcloth2", sailcloth, [
    [<item:minecraft:white_carpet>, <item:minecraft:white_carpet>, <item:minecraft:string>],
    [<item:minecraft:white_carpet>, <item:minecraft:white_carpet>, <item:minecraft:string>],
    [<item:minecraft:white_carpet>, <item:minecraft:white_carpet>, <item:minecraft:string>],
]);

//craftingTable.removeByName("immersive_aircraft:airship");
//craftingTable.addShaped("ia_airship", <item:immersive_aircraft:airship>, [
//    [<item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>],
//    [<item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>],
//    [<item:immersive_aircraft:hull>, <item:immersive_aircraft:hull>, <item:immersive_aircraft:engine>]
//]);
//
//craftingTable.removeByName("immersive_aircraft:warship");
//craftingTable.addShaped("ia_warship", <item:immersive_aircraft:warship>, [
//    [<item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>],
//    [<item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>],
//    [<item:immersive_aircraft:hull>, <item:immersive_aircraft:hull>, <item:immersive_aircraft:engine>]
//]);
//
//craftingTable.removeByName("immersive_aircraft:gyrodyne");
//craftingTable.addShaped("ia_gyrodyne", <item:immersive_aircraft:gyrodyne>, [
//    [<item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>],
//    [<item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>, <item:immersive_aircraft:sailcloth>],
//    [<item:immersive_aircraft:hull>, <item:immersive_aircraft:hull>, <item:immersive_aircraft:engine>]
//]);

// **TODO: Make a datapack that adds Lumber, and use that in place of logs (9x Logs)


// + Small Ships +
//
// NOTE: Requires the mods: immersive aircraft and supplementaries
//   (and maybe Twilight, and maybe a compatibility mod between supplementaries and Twilight...)
//   (Supplementaries has its own ropes tag if I need to fall back to that)

// Sails require rope and sailcloth
craftingTable.removeByName("smallships:sail");
craftingTable.addShaped("ss_sail", <item:smallships:sail>, [
    [sailcloth, sailcloth, sailcloth],
    [sailcloth, <tag:item:minecraft:logs>, sailcloth],
    [<tag:item:c:ropes>, <tag:item:minecraft:logs>, <tag:item:c:ropes>],
]);

// Ships require hulls and rope

//Cogs
craftingTable.removeByName("smallships:oak_cog");
craftingTable.addShaped("ss_oak_cog", <item:smallships:oak_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:oak_planks>, <item:immersive_aircraft:hull>, <item:minecraft:oak_planks>]
]);

craftingTable.removeByName("smallships:spruce_cog");
craftingTable.addShaped("ss_spruce_cog", <item:smallships:spruce_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:spruce_planks>, <item:immersive_aircraft:hull>, <item:minecraft:spruce_planks>]
]);

craftingTable.removeByName("smallships:birch_cog");
craftingTable.addShaped("ss_birch_cog", <item:smallships:birch_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:birch_planks>, <item:immersive_aircraft:hull>, <item:minecraft:birch_planks>]
]);

craftingTable.removeByName("smallships:jungle_cog");
craftingTable.addShaped("ss_jungle_cog", <item:smallships:jungle_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:jungle_planks>, <item:immersive_aircraft:hull>, <item:minecraft:jungle_planks>]
]);

craftingTable.removeByName("smallships:acacia_cog");
craftingTable.addShaped("ss_acacia_cog", <item:smallships:acacia_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:acacia_planks>, <item:immersive_aircraft:hull>, <item:minecraft:acacia_planks>]
]);

craftingTable.removeByName("smallships:cherry_cog");
craftingTable.addShaped("ss_cherry_cog", <item:smallships:cherry_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:cherry_planks>, <item:immersive_aircraft:hull>, <item:minecraft:cherry_planks>]
]);

craftingTable.removeByName("smallships:dark_oak_cog");
craftingTable.addShaped("ss_dark_oak_cog", <item:smallships:dark_oak_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:dark_oak_planks>, <item:immersive_aircraft:hull>, <item:minecraft:dark_oak_planks>]
]);

craftingTable.removeByName("smallships:mangrove_cog");
craftingTable.addShaped("ss_mangrove_cog", <item:smallships:mangrove_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:mangrove_planks>, <item:immersive_aircraft:hull>, <item:minecraft:mangrove_planks>]
]);

craftingTable.removeByName("smallships:bamboo_cog");
craftingTable.addShaped("ss_bamboo_cog", <item:smallships:bamboo_cog>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:air>, <item:minecraft:chest>],
    [<item:minecraft:bamboo_planks>, <item:immersive_aircraft:hull>, <item:minecraft:bamboo_planks>]
]);

//Galleys
craftingTable.removeByName("smallships:oak_galley");
craftingTable.addShaped("ss_oak_galley", <item:smallships:oak_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:oak_planks>, <item:immersive_aircraft:hull>, <item:minecraft:oak_planks>]
]);

craftingTable.removeByName("smallships:spruce_galley");
craftingTable.addShaped("ss_spruce_galley", <item:smallships:spruce_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:spruce_planks>, <item:immersive_aircraft:hull>, <item:minecraft:spruce_planks>]
]);

craftingTable.removeByName("smallships:birch_galley");
craftingTable.addShaped("ss_birch_galley", <item:smallships:birch_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:birch_planks>, <item:immersive_aircraft:hull>, <item:minecraft:birch_planks>]
]);

craftingTable.removeByName("smallships:jungle_galley");
craftingTable.addShaped("ss_jungle_galley", <item:smallships:jungle_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:jungle_planks>, <item:immersive_aircraft:hull>, <item:minecraft:jungle_planks>]
]);

craftingTable.removeByName("smallships:acacia_galley");
craftingTable.addShaped("ss_acacia_galley", <item:smallships:acacia_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:acacia_planks>, <item:immersive_aircraft:hull>, <item:minecraft:acacia_planks>]
]);

craftingTable.removeByName("smallships:cherry_galley");
craftingTable.addShaped("ss_cherry_galley", <item:smallships:cherry_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:cherry_planks>, <item:immersive_aircraft:hull>, <item:minecraft:cherry_planks>]
]);

craftingTable.removeByName("smallships:dark_oak_galley");
craftingTable.addShaped("ss_dark_oak_galley", <item:smallships:dark_oak_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:dark_oak_planks>, <item:immersive_aircraft:hull>, <item:minecraft:dark_oak_planks>]
]);

craftingTable.removeByName("smallships:mangrove_galley");
craftingTable.addShaped("ss_mangrove_galley", <item:smallships:mangrove_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:mangrove_planks>, <item:immersive_aircraft:hull>, <item:minecraft:mangrove_planks>]
]);

craftingTable.removeByName("smallships:bamboo_galley");
craftingTable.addShaped("ss_bamboo_galley", <item:smallships:bamboo_galley>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:leather>, <item:minecraft:leather>, <item:minecraft:leather>],
    [<item:minecraft:bamboo_planks>, <item:immersive_aircraft:hull>, <item:minecraft:bamboo_planks>]
]);

//Drakkar
craftingTable.removeByName("smallships:oak_drakkar");
craftingTable.addShaped("ss_oak_drakkar", <item:smallships:oak_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:oak_planks>, <item:minecraft:shield>, <item:minecraft:oak_planks>],
    [<item:minecraft:oak_planks>, <item:immersive_aircraft:hull>, <item:minecraft:oak_planks>]
]);

craftingTable.removeByName("smallships:spruce_drakkar");
craftingTable.addShaped("ss_spruce_drakkar", <item:smallships:spruce_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:spruce_planks>, <item:minecraft:shield>, <item:minecraft:spruce_planks>],
    [<item:minecraft:spruce_planks>, <item:immersive_aircraft:hull>, <item:minecraft:spruce_planks>]
]);

craftingTable.removeByName("smallships:birch_drakkar");
craftingTable.addShaped("ss_birch_drakkar", <item:smallships:birch_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:birch_planks>, <item:minecraft:shield>, <item:minecraft:birch_planks>],
    [<item:minecraft:birch_planks>, <item:immersive_aircraft:hull>, <item:minecraft:birch_planks>]
]);

craftingTable.removeByName("smallships:jungle_drakkar");
craftingTable.addShaped("ss_jungle_drakkar", <item:smallships:jungle_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:jungle_planks>, <item:minecraft:shield>, <item:minecraft:jungle_planks>],
    [<item:minecraft:jungle_planks>, <item:immersive_aircraft:hull>, <item:minecraft:jungle_planks>]
]);

craftingTable.removeByName("smallships:acacia_drakkar");
craftingTable.addShaped("ss_acacia_drakkar", <item:smallships:acacia_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:acacia_planks>, <item:minecraft:shield>, <item:minecraft:acacia_planks>],
    [<item:minecraft:acacia_planks>, <item:immersive_aircraft:hull>, <item:minecraft:acacia_planks>]
]);

craftingTable.removeByName("smallships:cherry_drakkar");
craftingTable.addShaped("ss_cherry_drakkar", <item:smallships:cherry_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:cherry_planks>, <item:minecraft:shield>, <item:minecraft:cherry_planks>],
    [<item:minecraft:cherry_planks>, <item:immersive_aircraft:hull>, <item:minecraft:cherry_planks>]
]);

craftingTable.removeByName("smallships:dark_oak_drakkar");
craftingTable.addShaped("ss_dark_oak_drakkar", <item:smallships:dark_oak_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:dark_oak_planks>, <item:minecraft:shield>, <item:minecraft:dark_oak_planks>],
    [<item:minecraft:dark_oak_planks>, <item:immersive_aircraft:hull>, <item:minecraft:dark_oak_planks>]
]);

craftingTable.removeByName("smallships:mangrove_drakkar");
craftingTable.addShaped("ss_mangrove_drakkar", <item:smallships:mangrove_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:mangrove_planks>, <item:minecraft:shield>, <item:minecraft:mangrove_planks>],
    [<item:minecraft:mangrove_planks>, <item:immersive_aircraft:hull>, <item:minecraft:mangrove_planks>]
]);

craftingTable.removeByName("smallships:bamboo_drakkar");
craftingTable.addShaped("ss_bamboo_drakkar", <item:smallships:bamboo_drakkar>, [
    [<tag:item:c:ropes>, <item:smallships:sail>, <tag:item:c:ropes>],
    [<item:minecraft:bamboo_planks>, <item:minecraft:shield>, <item:minecraft:bamboo_planks>],
    [<item:minecraft:bamboo_planks>, <item:immersive_aircraft:hull>, <item:minecraft:bamboo_planks>]
]);

//Brigg
craftingTable.removeByName("smallships:oak_brigg");
craftingTable.addShaped("ss_oak_brigg", <item:smallships:oak_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:oak_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:spruce_brigg");
craftingTable.addShaped("ss_spruce_brigg", <item:smallships:spruce_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:spruce_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:birch_brigg");
craftingTable.addShaped("ss_birch_brigg", <item:smallships:birch_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:birch_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:jungle_brigg");
craftingTable.addShaped("ss_jungle_brigg", <item:smallships:jungle_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:jungle_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:acacia_brigg");
craftingTable.addShaped("ss_acacia_brigg", <item:smallships:acacia_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:acacia_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:cherry_brigg");
craftingTable.addShaped("ss_cherry_brigg", <item:smallships:cherry_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:cherry_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:dark_oak_brigg");
craftingTable.addShaped("ss_dark_oak_brigg", <item:smallships:dark_oak_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:dark_oak_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:mangrove_brigg");
craftingTable.addShaped("ss_mangrove_brigg", <item:smallships:mangrove_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:mangrove_planks>, <item:immersive_aircraft:hull>]
]);

craftingTable.removeByName("smallships:bamboo_brigg");
craftingTable.addShaped("ss_bamboo_brigg", <item:smallships:bamboo_brigg>, [
    [<item:smallships:sail>, <tag:item:c:ropes>, <item:smallships:sail>],
    [<item:minecraft:chest>, <tag:item:c:ropes>, <item:minecraft:chest>],
    [<item:immersive_aircraft:hull>, <item:minecraft:bamboo_planks>, <item:immersive_aircraft:hull>]
]);


// + Vanilla +
//

// Lodestone is easier to craft
craftingTable.removeByName("minecraft:lodestone");
craftingTable.addShaped("mc_lodestone", <item:minecraft:lodestone>, [
    [<item:minecraft:chiseled_stone_bricks>, <item:minecraft:chiseled_stone_bricks>, <item:minecraft:chiseled_stone_bricks>],
    [<item:minecraft:chiseled_stone_bricks>, <item:minecraft:iron_ingot>, <item:minecraft:chiseled_stone_bricks>],
    [<item:minecraft:chiseled_stone_bricks>, <item:minecraft:chiseled_stone_bricks>, <item:minecraft:chiseled_stone_bricks>]
]);


// Boats are more difficult to craft
craftingTable.removeByName("minecraft:spruce_boat");
craftingTable.addShaped("mc_spruce_boat", <item:minecraft:spruce_boat>, [
    [<item:minecraft:spruce_planks>, <item:minecraft:iron_nugget>, <item:minecraft:spruce_planks>],
    [<item:minecraft:spruce_planks>, <item:minecraft:spruce_planks>, <item:minecraft:spruce_planks>],
]);

craftingTable.removeByName("minecraft:cherry_boat");
craftingTable.addShaped("mc_cherry_boat", <item:minecraft:cherry_boat>, [
    [<item:minecraft:cherry_planks>, <item:minecraft:iron_nugget>, <item:minecraft:cherry_planks>],
    [<item:minecraft:cherry_planks>, <item:minecraft:cherry_planks>, <item:minecraft:cherry_planks>]
]);

craftingTable.removeByName("minecraft:mangrove_boat");
craftingTable.addShaped("mc_mangrove_boat", <item:minecraft:mangrove_boat>, [
    [<item:minecraft:mangrove_planks>, <item:minecraft:iron_nugget>, <item:minecraft:mangrove_planks>],
    [<item:minecraft:mangrove_planks>, <item:minecraft:mangrove_planks>, <item:minecraft:mangrove_planks>]
]);

craftingTable.removeByName("minecraft:oak_boat");
craftingTable.addShaped("mc_oak_boat", <item:minecraft:oak_boat>, [
    [<item:minecraft:oak_planks>, <item:minecraft:iron_nugget>, <item:minecraft:oak_planks>],
    [<item:minecraft:oak_planks>, <item:minecraft:oak_planks>, <item:minecraft:oak_planks>]
]);

craftingTable.removeByName("minecraft:dark_oak_boat");
craftingTable.addShaped("mc_dark_oak_boat", <item:minecraft:dark_oak_boat>, [
    [<item:minecraft:dark_oak_planks>, <item:minecraft:iron_nugget>, <item:minecraft:dark_oak_planks>],
    [<item:minecraft:dark_oak_planks>, <item:minecraft:dark_oak_planks>, <item:minecraft:dark_oak_planks>]
]);

craftingTable.removeByName("minecraft:birch_boat");
craftingTable.addShaped("mc_birch_boat", <item:minecraft:birch_boat>, [
    [<item:minecraft:birch_planks>, <item:minecraft:iron_nugget>, <item:minecraft:birch_planks>],
    [<item:minecraft:birch_planks>, <item:minecraft:birch_planks>, <item:minecraft:birch_planks>]
]);

craftingTable.removeByName("minecraft:jungle_boat");
craftingTable.addShaped("mc_jungle_boat", <item:minecraft:jungle_boat>, [
    [<item:minecraft:jungle_planks>, <item:minecraft:iron_nugget>, <item:minecraft:jungle_planks>],
    [<item:minecraft:jungle_planks>, <item:minecraft:jungle_planks>, <item:minecraft:jungle_planks>]
]);

craftingTable.removeByName("minecraft:acacia_boat");
craftingTable.addShaped("mc_acacia_boat", <item:minecraft:acacia_boat>, [
    [<item:minecraft:acacia_planks>, <item:minecraft:iron_nugget>, <item:minecraft:acacia_planks>],
    [<item:minecraft:acacia_planks>, <item:minecraft:acacia_planks>, <item:minecraft:acacia_planks>]
]);

// **TODO: ? Update the Twilight boat recipes? (IDK anything about Twilight, yet)

// Additional versions of the lead that are easier to craft
// Rope version (from Supplementaries)
craftingTable.addShaped("mc_lead1", <item:minecraft:lead>, [
    [<item:minecraft:string>],
    [<item:minecraft:air>, <tag:item:c:ropes>]
]);

// Honey version
craftingTable.addShaped("mc_lead2", <item:minecraft:lead> * 2, [
    [<item:minecraft:string>, <item:minecraft:string>],
    [<item:minecraft:string>, <item:minecraft:honey_bottle>],
    [<item:minecraft:air>, <item:minecraft:air>, <item:minecraft:string>]
]);

// Rails are easier to craft
craftingTable.removeByName("minecraft:rail");
craftingTable.addShaped("mc_rail", <item:minecraft:rail> * 24, [
    [<tag:item:minecraft:planks>, <item:minecraft:air>, <tag:item:minecraft:planks>],
    [<item:minecraft:iron_ingot>, <item:minecraft:stick>, <item:minecraft:iron_ingot>],
    [<tag:item:minecraft:planks>, <item:minecraft:air>, <tag:item:minecraft:planks>]
]);

craftingTable.removeByName("minecraft:powered_rail");
craftingTable.addShaped("mc_powered_rail", <item:minecraft:powered_rail> * 6, [
    [<tag:item:minecraft:planks>, <item:minecraft:air>, <tag:item:minecraft:planks>],
    [<item:minecraft:copper_ingot>, <item:minecraft:stick>, <item:minecraft:copper_ingot>],
    [<tag:item:minecraft:planks>, <item:minecraft:redstone>, <tag:item:minecraft:planks>]
]);

craftingTable.removeByName("minecraft:detector_rail");
craftingTable.addShaped("mc_detector_rail", <item:minecraft:detector_rail> * 6, [
    [<tag:item:minecraft:planks>, <item:minecraft:air>, <tag:item:minecraft:planks>],
    [<item:minecraft:iron_ingot>, <item:minecraft:stone_pressure_plate>, <item:minecraft:iron_ingot>],
    [<tag:item:minecraft:planks>, <item:minecraft:redstone>, <tag:item:minecraft:planks>]
]);

craftingTable.removeByName("minecraft:activator_rail");
craftingTable.addShaped("mc_activator_rail", <item:minecraft:activator_rail> * 6, [
    [<tag:item:minecraft:planks>, <item:minecraft:stick>, <tag:item:minecraft:planks>],
    [<item:minecraft:iron_ingot>, <item:minecraft:redstone_torch>, <item:minecraft:iron_ingot>],
    [<tag:item:minecraft:planks>, <item:minecraft:stick>, <tag:item:minecraft:planks>]
]);

// Cows guarantee 1 leather
var is_cow = LootConditions.only(LootTableIdLootCondition.create(<resource:minecraft:entities/cow>));
var guaranteed_leather = CommonLootModifiers.chaining(
    CommonLootModifiers.addWithUniformBonus(<enchantment:minecraft:looting>, 1, <item:minecraft:leather>),
    CommonLootModifiers.addWithRandomAmount(<item:minecraft:leather>, 0, 1)
);

loot.modifiers.register(
     "guaranteed_leather_fromcows",
     is_cow,
     guaranteed_leather
);


// Leather armor recipe uses joinery
craftingTable.removeByName("minecraft:leather_helmet");
craftingTable.addShaped("mc_leather_helmet", <item:minecraft:leather_helmet>, [
    [<tag:item:mypack:leather_joinery>, <item:minecraft:leather>, <tag:item:mypack:leather_joinery>],
    [<item:minecraft:leather>, <item:minecraft:air>, <item:minecraft:leather>]
]);

craftingTable.removeByName("minecraft:leather_chestplate");
craftingTable.addShaped("mc_leather_chestplate", <item:minecraft:leather_chestplate>, [
    [<item:minecraft:leather>, <item:minecraft:air>, <item:minecraft:leather>],
    [<tag:item:mypack:leather_joinery>, <item:minecraft:leather>, <tag:item:mypack:leather_joinery>],
    [<tag:item:mypack:leather_joinery>, <item:minecraft:leather>, <tag:item:mypack:leather_joinery>]         
]);

craftingTable.removeByName("minecraft:leather_leggings");
craftingTable.addShaped("mc_leather_leggings", <item:minecraft:leather_leggings>, [
    [<item:minecraft:leather>, <tag:item:mypack:leather_joinery>, <item:minecraft:leather>],
    [<item:minecraft:leather>, <item:minecraft:air>, <item:minecraft:leather>],
    [<tag:item:mypack:leather_joinery>, <item:minecraft:air>, <tag:item:mypack:leather_joinery>]         
]);

craftingTable.removeByName("minecraft:leather_boots");
craftingTable.addShaped("mc_leather_boots", <item:minecraft:leather_boots>, [
    [<tag:item:mypack:leather_joinery>, <item:minecraft:air>, <tag:item:mypack:leather_joinery>],
    [<item:minecraft:leather>, <item:minecraft:air>, <item:minecraft:leather>]
]);

// Leather armor can be recycled (leather enhancement #1)
craftingTable.addShapeless("mc_leather_helmet_scrap", <item:minecraft:leather>, [
    <item:minecraft:leather_helmet>.anyDamage()
]);

craftingTable.addShapeless("mc_leather_boots_scrap", <item:minecraft:leather>, [
    <item:minecraft:leather_boots>.anyDamage()
]);

craftingTable.addShapeless("mc_leather_legs_scrap", <item:minecraft:leather> * 2, [
    <item:minecraft:leather_leggings>.anyDamage()
]);

craftingTable.addShapeless("mc_leather_chest_scrap", <item:minecraft:leather> * 3, [
    <item:minecraft:leather_chestplate>.anyDamage()
]);
