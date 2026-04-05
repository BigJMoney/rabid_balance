# sample MSPT window
say Capture Now
tellraw @p {"text":"[Click to run spark]","color":"green","clickEvent":{"action":"run_command","value":"/spark tps --log"}}

# todo: try later:
# forge tps
# execute as @p at @s run forge tps

# after a tick → next step
schedule function rabidbalance:bench/step1 1t replace