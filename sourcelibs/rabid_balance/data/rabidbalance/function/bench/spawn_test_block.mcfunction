# place command block at player feet
setblock ~ ~ ~ minecraft:command_block

# write command into it
data modify block ~ ~ ~ Command set value "execute as @p run spark tps"

# set it to impulse, needs redstone = false (auto run)
data modify block ~ ~ ~ auto set value 1b