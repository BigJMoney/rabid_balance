execute store result score #calendar day run time query day
scoreboard players add #calendar day 1

scoreboard players operation #calendar season = #calendar day
scoreboard players remove #calendar season 1
scoreboard players operation #calendar season /= #calendar season_len
scoreboard players add #calendar season 1

execute if score #calendar season > #calendar last_horde_season run function rabidbalance:hordes/seasonal_horde

# Default check is 4 times per MC day
schedule function rabidbalance:calendar/season_check 6000t replace