tag @s add pending_horde

# Should be 3000t by default
schedule function rabidbalance:hordes/warning_final 3000t replace

tellraw @a [{"nbt":"trigger_msg","storage":"rabidbalance:hordes","color":"red"},{"text": "\nPrepare!","color":"red"}]