scoreboard objectives add season_len dummy
scoreboard objectives add season dummy
scoreboard objectives add day dummy
scoreboard objectives add last_horde_season dummy

scoreboard players set #calendar season_len 24
execute unless score #calendar last_horde_season matches -2147483648..2147483647 run scoreboard players set #calendar last_horde_season 0

function rabidbalance:calendar/season_check