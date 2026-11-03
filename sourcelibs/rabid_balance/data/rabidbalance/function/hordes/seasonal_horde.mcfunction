# Don't advance the countdown twice on the same day
execute if score #calendar day = #hordes last_warning_day run return 0

# Record the day being processed
scoreboard players operation #hordes last_warning_day = #calendar day

# Countdown 
execute if score #hordes countdown matches 3.. run return run function rabidbalance:hordes/warning1
execute if score #hordes countdown matches 2.. run return run function rabidbalance:hordes/warning2
execute if score #hordes countdown matches 1.. run return run function rabidbalance:hordes/warning3

# Spawn Horde
say debug: seasonal horde triggered
execute as @a at @s run function rabidbalance:hordes/trigger

# Reset for next season
scoreboard players operation #calendar last_horde_season = #calendar season
scoreboard players reset #calendar horde_delay
scoreboard players set #hordes countdown 3