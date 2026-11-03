function rabidbalance:calendar/build_calendar

tellraw @a [{"text":"Day: "},{"score":{"name":"#calendar","objective":"day"}},{"text":" | Season: "},{"score":{"name":"#calendar","objective":"season"}},{"text":" | Season Day: "},{"score":{"name":"#calendar","objective":"season_day"}},{"text":" | Random: "},{"score":{"name":"#calendar","objective":"horde_delay"}}]
execute if entity @a if score #calendar season > #calendar last_horde_season if score #calendar season_day > #calendar horde_delay run tellraw @a [{"text":"debug: horde WILL be triggered this season", "color":"green"}]