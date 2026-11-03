scoreboard objectives add countdown dummy
scoreboard objectives add last_warning_day dummy

execute unless score #hordes countdown matches 0..3 run scoreboard players set #hordes countdown 3
function rabidbalance:hordes/reset_msg