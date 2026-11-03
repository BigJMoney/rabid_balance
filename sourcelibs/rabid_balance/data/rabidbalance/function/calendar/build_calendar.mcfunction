# Get the MC day
execute store result score #calendar day run time query day
scoreboard players add #calendar day 1

# Calculate the MC season
scoreboard players operation #calendar season = #calendar day
scoreboard players remove #calendar season 1
scoreboard players operation #calendar season /= #calendar season_len
scoreboard players add #calendar season 1

# Calculate this season's current day
scoreboard players operation #calendar season_day = #calendar day
scoreboard players remove #calendar season_day 1
scoreboard players operation #calendar season_day %= #calendar season_len
scoreboard players add #calendar season_day 1

# Initialize the horde's random delay (0–4 days) if unset
execute unless score #calendar horde_delay matches 0..4 run execute store result score #calendar horde_delay run random value 0..4