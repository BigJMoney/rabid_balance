say END Perf Test

# Stop all perf scripts
schedule clear rabidbalance:bench/step1
schedule clear rabidbalance:bench/step2
schedule clear rabidbalance:bench/measure
schedule clear rabidbalance:bench/float_tick_loop
# Even clear the scheduled auto-stop
schedule clear rabidbalance:bench/stop

# Reset Gravity
data merge entity @p {NoGravity:0b}