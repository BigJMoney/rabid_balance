See: Improving GLM Data Views, first

No. If your Structure Heatmap is based on `drop_events_expected`, then my earlier “Phase 1” was too weak.

Here’s the correction:

| Question | Answer |
|---|---|
| Would a presence/profile-only merged snapshot satisfy your real heatmap? | No |
| Why? | Because your heatmap is driven by `drop_events_expected`, not just item presence |
| What is the minimum correct solution? | A merged **table-item expectation** layer, then project that onto structures |

## Why The Current Model Still Falls Short

Right now you have:

| Layer | Current export |
|---|---|
| Base structure -> loot table | [structure_loot_links.csv](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/loot_stack_v1/structure_loot_links.csv) |
| Base loot-table expectations | [root_table_item_summary.csv](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/loot_stack_v1/root_table_item_summary.csv) |
| GLM added payload rows | [modifier_added_leaf_candidates.csv](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/loot_stack_v1/modifier_added_leaf_candidates.csv) |

What you **do not** have is:

| Missing layer | Why it matters |
|---|---|
| `merged_root_table_item_summary.csv` | needed for `drop_events_expected` after recognized GLMs |
| optionally `merged_structure_item_summary.csv` | convenience layer for heatmaps/profiles |

So yes, the core missing piece is not just “connect GLM data somehow.” It is:

- **recompute merged table-item expectations**
- then join/project those to structures

## Best General Solution

I think the right answer is a **third snapshot**, for example:

- `docs/loot_docs/loot_stack_merged_v1`

That avoids touching:
- [vanilla_loot_v1](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/vanilla_loot_v1)
- [loot_stack_v1](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/loot_stack_v1)

### Minimum useful outputs for that merged snapshot

| File | Grain | Purpose |
|---|---|---|
| `merged_root_table_item_summary.csv` | `table + item` | merged `drop_events_expected`, `drop_yield_expected`, `at_least_one_chance` |
| `merged_structure_item_summary.csv` | `structure + item` | heatmap-ready projection |
| `merged_structure_profile_summary.csv` | `structure` | high-level structure profile metrics |
| optional `merged_leaf_candidates.csv` | `table + path` | only if you want path-level merged analysis too |

## Why This Can Work Without A Full Simulator

For the currently recognized GLMs:
- `neoforge:add_table`
- `sophisticatedbackpacks:inject_loot`

the exporter already knows:

| Known now | Source |
|---|---|
| target table | GLM analysis |
| payload table | GLM analysis |
| payload leaf rows | Stage 2 payload parser |

And the base exporter already knows how to compute:
- `drop_events_expected`
- `drop_yield_expected`
- `at_least_one_chance`

So the practical merged model is:

1. keep base table metrics
2. compute payload-table metrics for recognized additive GLMs
3. add those payload contributions onto the target table’s metrics
4. project merged table metrics onto structures through [structure_loot_links.csv](/D:/keep/mods/Minecraft/my_tweaks/docs/loot_docs/loot_stack_v1/structure_loot_links.csv)

That would satisfy the **right heatmap view**, because it gives you merged `drop_events_expected`, not just merged presence.

## Important Accuracy Boundary

This would be strong for **recognized additive inject semantics**, but not universal.

| Case | Confidence |
|---|---|
| recognized additive GLMs with simple target-table gating | good |
| unsupported/custom GLM types | not covered |
| GLMs with extra unsupported conditions/context dependence | may need to fall back to unknown/partial |

So this is not “final runtime simulation for every mod,” but it is much better than the current disconnected delta tables.

## Revised Phase Estimate

| Phase | Scope | Time | Risk |
|---|---|---:|---|
| `Merged DOE snapshot` | merged table-item expectations + structure projection | 2–3 days | medium |
| `Merged path layer` | merged leaf/path exports too | +1–2 days | medium |
| `Broader GLM semantics` | more conditions/custom modifier support | several more days | high |

So the real minimal version that satisfies your heatmap is **not** my earlier Phase 1. It’s this revised first phase:
- **merged DOE snapshot**

## Impact On Current Functionality

| Concern | Impact |
|---|---|
| current exports | none, if we use a third snapshot |
| current workbook | none until you choose to point views at merged tables |
| current delta GLM tables | still useful for audit/debug |
| loss of functionality | none expected |

So the corrected answer is:

- **No**, my earlier Phase 1 would not fully satisfy a `drop_events_expected` heatmap.
- The minimum good solution is a new merged snapshot that materializes **merged table-item expectations**, then projects them to structures.

If you want, next I can turn that into a concrete implementation plan with exact filenames and the simplest viable merge math for recognized additive GLMs.