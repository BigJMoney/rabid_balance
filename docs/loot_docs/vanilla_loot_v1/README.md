# Loot Stack V1

Effective layered Stage 1 loot-table export built from the implicit vanilla base plus selected mod packs.

## Summary

- Base pack root: `D:\keep\mods\Minecraft\my_tweaks\libs\neoforge-21.1.162_ref`
- Scope config: `<in-memory scope override>`
- Ignore roots: `D:\keep\mods\Minecraft\my_tweaks\libs\ignore`
- Selected pack count: 1
- Classification source: `D:\keep\mods\Minecraft\my_tweaks\docs\loot_docs\resolved_loot_v10.csv`
- Classification version: `10`
- Named table rows: 65
- Inline table rows: 3
- Pool rows: 128
- Entry rows: 752
- Leaf candidate rows: 810
- Table role rows: 65
- Table role evidence rows: 176
- GLM chain rows: 0
- Modifier-added leaf rows: 0
- Target table modifier summary rows: 0
- Target table added item summary rows: 0
- Item classification rows: 1332
- Item affinity rows: 1174
- Classification coverage rows: 235
- Structure rows: 34
- Structure loot-link rows: 49
- Structure loot-link audit rows: 142
- Classified loot items: 235
- Missing loot items: 0

## Selected Packs

- `base` (directory) from `D:\keep\mods\Minecraft\my_tweaks\libs\neoforge-21.1.162_ref`

## Files

- `precheck_report.json`: discovered packs, selected packs, effective order, overlap groups, and fatal precheck errors.
- `tables.csv`: one row per effective named table plus synthetic inline table.
- `pools.csv`: one row per pool with roll metadata and pool-level conditions.
- `entries.csv`: one row per entry with direct metadata, raw JSON, reference targets, and entry-level pool weight shares.
- `leaf_candidates.csv`: denormalized root-to-leaf paths for Tableau-style analysis, including raw path weights and normalized pool-share metrics.
- `table_role_summary.csv`: one row per named effective table with raw and Tableau-facing directness roles.
- `table_role_evidence.csv`: evidence edges behind the table role classification.
- `glm_modifier_chain.csv`: one row per effective NeoForge GLM chain entry with target-table and payload-table analysis status.
- `modifier_added_leaf_candidates.csv`: one row per resolved added payload leaf for recognized Stage 2 modifiers.
- `target_table_modifier_summary.csv`: one row per target table summarizing modifier counts and added-item novelty/overlap.
- `target_table_added_item_summary.csv`: one row per target table plus item_id summarizing modifier-added item paths.
- `stage2_report.json`: Stage 2 chain counts, recognized/unsupported totals, and warnings.
- `structure_loot_resolution_report.json`: exact-match, ambiguous-match, and no-match structure resolution counts plus stale-row warnings.
- `item_classification.csv`: one row per classified item_id sourced from the canonical resolved_loot export.
- `item_affinities.csv`: one row per item_id plus affinity for relational Tableau joins.
- `classification_coverage.csv`: one row per distinct loot item_id with classified-or-missing coverage status.
- `structures.csv`: one row per active structure_id with source metadata, active structure-set provenance, and structure detection status.
- `structure_loot_links.csv`: one row per applied structure_id plus loot_table_id link after exact-match detection, ambiguous autoresolve, and manual no-match mapping.
- `structure_loot_link_audit.csv`: audit trail for exact-match detections, ambiguous-match candidates, manual no-match mappings, and stale skipped rows.
- `scope_report.json`: allowed, excluded, and deferred top-level loot_table folder scope with warnings.
- `manifest.json`: export counts for tables, pools, entries, references, and leaf rows.

## Join Keys

- `tables.csv.table_id` joins to `pools.csv.table_id` and `entries.csv.table_id`.
- `pools.csv.pool_id` joins to `entries.csv.pool_id`.
- `leaf_candidates.csv.root_table_id` joins back to named rows in `tables.csv`.
- `glm_modifier_chain.csv.target_table_id` joins to `tables.csv.table_id` for target-table metadata.
- `modifier_added_leaf_candidates.csv.target_table_id` joins to `tables.csv.table_id` for base target-table context.
- `modifier_added_leaf_candidates.csv.item_id` joins to `item_classification.csv.item_id` for Stage 2 item traits.
- `target_table_added_item_summary.csv.item_id` joins to `item_classification.csv.item_id` for Stage 2 added-item slicing.
- `leaf_candidates.csv.item_id` joins to `item_classification.csv.item_id` for Stage 1.5 item traits.
- `structure_loot_links.csv.loot_table_id` joins to `tables.csv.table_id` for loot-table metadata when the linked table is in Stage 1 scope.
- `leaf_candidates.csv.root_table_id` joins to `table_role_summary.csv.table_id` for gameplay-source filtering.
- `item_classification.csv.item_id` joins to `item_affinities.csv.item_id` for affinity slicing.
- `classification_coverage.csv.item_id` joins to `item_classification.csv.item_id` for audit and completeness checks.
- `table_role_summary.csv.table_id` joins to `table_role_evidence.csv.table_id` for provenance drill-down.

## Allowed Folders

- `chests`: 56 effective loot-table resources
- `equipment`: 3 effective loot-table resources
- `pots`: 1 effective loot-table resources
- `spawners`: 5 effective loot-table resources

## Excluded Folders

- `archaeology`: 6 effective loot-table resources
- `blocks`: 982 effective loot-table resources
- `dispensers`: 3 effective loot-table resources
- `entities`: 100 effective loot-table resources
- `gameplay`: 21 effective loot-table resources
- `shearing`: 1 effective loot-table resources

## Deferred Stage 2 Folders

- None

## Warnings

- None

## Notes

- The scope config is always authoritative for Stage 1 allowed and deferred top-level loot_table directories.
- Descendants of the configured ignore roots are skipped during auto-discovery and archive-root scans unless you include them explicitly with `--pack`.
- Top-level `loot_table/inject/...` is treated as deferred Stage 2 and is intentionally omitted from Stage 1 outputs.
- Nested paths like `loot_table/entities/inject/...` are still ordinary Stage 1 loot tables because the top-level directory is `entities`.
- Inline tables use synthetic IDs in the form `inline:{entry_id}`.
- `entries.csv.conditions_json` stores only conditions declared directly on entry objects. In many vanilla and modded tables, real conditions may still live at the pool level instead.
- `entries.csv.quality` and `leaf_candidates.csv.leaf_quality` remain in the schema because they are valid loot fields even when blank in a given scope.
- Raw `weight` values are not standardized across unrelated pools or tables, so compare normalized share fields when you need cross-table weighting context.
- For the current scope, normalization is pool-based because the parsed entries are all top-level pool entries rather than nested composite siblings.
- Missing entry `weight` values are normalized as Minecraft's implicit default of `1` for the pool-share calculations.
- `entries.csv.pool_weight_share` is the entry's local share of its pool total and is the authoritative raw normalized-weight field for this scope.
- `leaf_candidates.csv.root_entry_weight` and `leaf_candidates.csv.root_entry_quality` come from the first chain step only.
- `leaf_candidates.csv.root_pool_weight_share` describes the normalized root-step context without restating an effective-weight denominator column.
- `leaf_candidates.csv.path_pool_shares_json` lists the ordered local pool shares across the resolved path.
- `leaf_candidates.csv.path_pool_share_product` is a relative path-choice share, not final drop probability.
- `leaf_candidates.csv.leaf_weight` remains terminal-entry-only for backward compatibility; it is not a path weight or probability.
- `leaf_candidates.csv.path_explicit_weights_json` lists only explicitly declared weights encountered along the resolved path.
- `leaf_candidates.csv.path_explicit_weight_product` is the product of explicit path weights only; it is not normalized chance.
- `set_count_min` and `set_count_max` only reflect explicit terminal `minecraft:set_count` functions.
- `leaf_candidates.csv` is a path table. For source counts in Tableau, join it to `table_role_summary.csv` on `root_table_id = table_id` and filter `count_as_direct = true`.
- For Tableau weighting work, prefer `entries.csv.pool_weight_share`, `leaf_candidates.csv.root_pool_weight_share`, and `leaf_candidates.csv.path_pool_share_product` over raw weight sums.
- Stage 2 inventories NeoForge Global Loot Modifiers only. LootJS/KubeJS runtime mutations remain out of scope.
- `glm_modifier_chain.csv` inventories every effective GLM in order, but detailed delta rows only exist for recognized inject/add-table semantics.
- `modifier_added_leaf_candidates.csv` is a delta table, not a final runtime probability model. It shows what recognized modifiers add, not exact post-modifier odds.
- Structure-based exports are keyed by active unique `structure_id`. Structure sets are used only internally to discover active structures.
- Structure pairing is built from the final effective layered resource set after pack stacking, not from per-pack intermediate passes.
- Exact-match links apply automatically from the conservative structure-side detector.
- Ambiguous-match candidates live in `D:\keep\mods\Minecraft\my_tweaks\configs\structure_loot_ambiguous_resolution_map.yaml`. Review them there and set `autoresolve: true` only for the specific rows you want applied automatically.
- No-match manual resolutions live in `D:\keep\mods\Minecraft\my_tweaks\configs\structure_loot_manual_resolution_map.yaml`. Open the file, research unresolved rows, fill in `structure_id`, then set `status: mapped`.
- Use `--clean-structure-resolution-maps` to prune stale ambiguous/manual mapped rows after mod-list changes while preserving current approvals and current manual mappings.
- Use `--rebuild-all-structure-resolution-maps` only when you intentionally want a destructive rebuild of both structure resolution YAMLs from current export results.
- No suppressions are part of this workflow. If an exact detected link is wrong, the matching logic should be corrected instead of overridden.
- Automatic structure-to-loot mapping remains conservative: jigsaw start-pool traversal, pool aliases, reachable template pools, template NBT loot-table scans, explicit processor-list loot assignments, and ambiguous candidates from real structure roots, active structure-id stems, or reduced structure-id submatches.
- Non-jigsaw structures may still land in ambiguous-match or no-match until you confirm them through the resolution YAMLs.
- `structure_loot_links.csv` is the raw structure-to-loot-table layer for this corrected first pass.
- `resolved_loot_v*.csv` remains the canonical raw classification export, but its `affinities` field is a serialized list. Prefer `item_classification.csv` plus `item_affinities.csv` for Tableau.
- `classification_coverage.csv` makes missing loot-item classifications explicit instead of silently dropping them.
- `raw_role` keeps the conservative local-data provenance result; `effective_role` converts `unknown_directness` to `assumed_direct_for_tableau`.
- `tables.csv.source_pack`, `tables.csv.resource_path`, and `tables.csv.is_override` identify the winning source behind each effective table row.
