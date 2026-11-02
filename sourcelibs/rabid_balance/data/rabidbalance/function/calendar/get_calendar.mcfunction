execute store result score #calendar day run time query day
scoreboard players add #calendar day 1

scoreboard players operation #calendar season = #calendar day
scoreboard players remove #calendar season 1
scoreboard players operation #calendar season /= #calendar season_len
scoreboard players add #calendar season 1

tellraw @a [{"text":"Season: "},{"score":{"name":"#calendar","objective":"season"}},{"text":" | Day: "},{"score":{"name":"#calendar","objective":"day"}}]
execute unless score #calendar season > #calendar last_horde_season run tellraw @a [{"text":"debug: horde will NOT be triggered", "color":"green"}]
execute if score #calendar season > #calendar last_horde_season run tellraw @a [{"text":"debug: horde WILL be triggered", "color":"green"}]