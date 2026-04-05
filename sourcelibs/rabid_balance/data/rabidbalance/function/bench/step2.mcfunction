# move forward (adjust distance if needed)
execute as @p at @s run tp @p ~200 100 ~ -90 0

# after 5s → measure
schedule function rabidbalance:bench/measure 100t replace