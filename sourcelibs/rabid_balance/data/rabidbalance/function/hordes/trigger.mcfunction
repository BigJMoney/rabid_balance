tag @s add pending_horde
schedule function rabidbalance:hordes/warning 3000t replace
tellraw @a {"text":"Someone's meddling with ancient magics has awakened a horde of monsters who will soon be on their way to you.","color":"red"}
tellraw @a {"text":"Prepare!","color":"red"}