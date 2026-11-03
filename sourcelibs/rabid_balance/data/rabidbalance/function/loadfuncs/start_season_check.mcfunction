scoreboard objectives add season_len dummy
scoreboard objectives add season dummy
scoreboard objectives add day dummy
scoreboard objectives add season_day dummy
scoreboard objectives add last_horde_season dummy
scoreboard objectives add horde_delay dummy

scoreboard players set #calendar season_len 24
execute unless score #calendar last_horde_season matches 0..2147483647 run scoreboard players set #calendar last_horde_season 1
execute unless score #calendar horde_delay matches 0..4 run execute store result score #calendar horde_delay run random value 0..4

function rabidbalance:calendar/season_check