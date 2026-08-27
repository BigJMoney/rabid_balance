# move forward (adjust distance if needed)
execute as @p at @s run tp @p ~200 100 ~ -90 0

# after 5s → measure
schedule function rabidbalance:bench/measure 200t replace

# current test speed is 1block / tick (mild pressure)