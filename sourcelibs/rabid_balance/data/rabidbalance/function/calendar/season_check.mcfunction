function rabidbalance:calendar/build_calendar

# Trigger the wandering horde
#   If a player is online
#   If it's a new season (i.e. no horde triggered yet)
#   If the season's day beats the random chance check (1/5)
execute if entity @a if score #calendar season > #calendar last_horde_season if score #calendar season_day > #calendar horde_delay run function rabidbalance:hordes/seasonal_horde

# Default check is 4 times per MC day
schedule function rabidbalance:calendar/season_check 6000t replace