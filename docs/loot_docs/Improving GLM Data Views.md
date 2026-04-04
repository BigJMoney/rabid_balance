>Me:
>1. A GLM structure profile view. I can see if the rarity / heatmap of a GLM "loot patch" matches the pre-glm shape
>2. A GLM total drop events view. I can get numbers for each structure to see which ones are "fattening up"

Yes, that’s a good pivot, and much cheaper than a full merged snapshot.

And you’re also right about the intuition: for these additive GLMs, loot pressure can grow by accretion. Since they append another rolled table instead of rebalancing the original one, mods can keep fattening the same targets.

On your two proposed views:

1. A GLM structure profile view
This is very plausible and probably the best next step.
You’d basically project:
- `modifier_added_leaf_candidates.target_table_id`
through
- `structure_loot_links.loot_table_id`
to
- `structure_id`

That gives you a structure-facing view of just the GLM-added loot patch.

2. A GLM total drop events view
Also plausible, if we compute Stage 2 DOE per target table/item first and then project it to structures.
That is more work than the profile view, but still much less than a full merged model.

On your assumption:
- you actually **can already map GLM loot to structures**, at least at the table-link level

Because current exports already give you:
- [modifier_added_leaf_candidates.csv](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/loot_stack_v1/modifier_added_leaf_candidates.csv).`target_table_id`
- [structure_loot_links.csv](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/loot_stack_v1/structure_loot_links.csv).`loot_table_id`

So the join is:
- `modifier_added_leaf_candidates.target_table_id = structure_loot_links.loot_table_id`

That means:
- yes, current recognized GLM additions can already be projected onto structures
- no exporter rewrite is needed just to get the basic structure mapping

What you do **not** have yet is:
- pre-aggregated GLM-only structure summaries
- or GLM-only DOE metrics

So I think the best next step is not a merged model yet. It’s a small new Stage 2 projection layer, something like:
- `structure_glm_added_leaf_candidates.csv`
- maybe `structure_glm_item_summary.csv`
- maybe `structure_glm_profile_summary.csv`

That would let you build both of the views you described without disturbing the existing base exports.

So the answer is:
- you probably don’t need a full merged view yet
- and you actually can already map current GLM loot to structures through `target_table_id -> loot_table_id`
- the missing piece is just a clean exported structure-facing Stage 2 projection