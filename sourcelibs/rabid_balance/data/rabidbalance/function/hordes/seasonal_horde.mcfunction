tellraw @a [{"text":"debug: seasonal horde triggered", "color":"green"}]
scoreboard players operation #calendar last_horde_season = #calendar season
execute as @a at @s run function rabidbalance:hordes/trigger