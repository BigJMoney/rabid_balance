say BEGIN Perf Test

# reset
schedule clear rabidbalance:bench/step1
schedule clear rabidbalance:bench/step2
schedule clear rabidbalance:bench/measure
schedule clear rabidbalance:bench/float_tick_loop
schedule clear rabidbalance:bench/stop

# start levitation loop
function rabidbalance:bench/float_tick_loop

# reset position
execute as @p at @s run tp @p 0 100 0 -90 0

# schedule perf end (60s)
schedule function rabidbalance:bench/stop 1200t replace

# start perf loop
function rabidbalance:bench/measure