# Loot Stack V1

Effective layered Stage 1 loot-table export built from the implicit vanilla base plus selected mod packs.

## Summary

- Base pack root: `D:\keep\mods\Minecraft\my_tweaks\libs\neoforge-21.1.162_ref`
- Scope config: `D:\keep\mods\Minecraft\my_tweaks\configs\loot_scope.json`
- Ignore roots: `D:\keep\mods\Minecraft\my_tweaks\libs\ignore`
- Selected pack count: 2
- Named table rows: 72
- Inline table rows: 3
- Pool rows: 201
- Entry rows: 831
- Leaf candidate rows: 889
- Table role rows: 72
- Table role evidence rows: 195

## Selected Packs

- `base` (directory) from `D:\keep\mods\Minecraft\my_tweaks\libs\neoforge-21.1.162_ref`
- `illagerinvasion` (directory) from `D:\keep\mods\Minecraft\my_tweaks\libs\IllagerInvasion-v21.1.6-NeoForge`

## Files

- `precheck_report.json`: discovered packs, selected packs, effective order, overlap groups, and fatal precheck errors.
- `tables.csv`: one row per effective named table plus synthetic inline table.
- `pools.csv`: one row per pool with roll metadata and pool-level conditions.
- `entries.csv`: one row per entry with direct metadata, raw JSON, and reference targets.
- `leaf_candidates.csv`: denormalized root-to-leaf paths for Tableau-style analysis.
- `table_role_summary.csv`: one row per named effective table with raw and Tableau-facing directness roles.
- `table_role_evidence.csv`: evidence edges behind the table role classification.
- `scope_report.json`: allowed, excluded, and deferred top-level loot_table folder scope with warnings.
- `manifest.json`: export counts for tables, pools, entries, references, and leaf rows.

## Join Keys

- `tables.csv.table_id` joins to `pools.csv.table_id` and `entries.csv.table_id`.
- `pools.csv.pool_id` joins to `entries.csv.pool_id`.
- `leaf_candidates.csv.root_table_id` joins back to named rows in `tables.csv`.
- `leaf_candidates.csv.root_table_id` joins to `table_role_summary.csv.table_id` for gameplay-source filtering.
- `table_role_summary.csv.table_id` joins to `table_role_evidence.csv.table_id` for provenance drill-down.

## Allowed Folders

- `chests`: 63 effective loot-table resources
- `equipment`: 3 effective loot-table resources
- `pots`: 1 effective loot-table resources
- `spawners`: 5 effective loot-table resources

## Excluded Folders

- `archaeology`: 6 effective loot-table resources
- `blocks`: 984 effective loot-table resources
- `dispensers`: 3 effective loot-table resources
- `entities`: 114 effective loot-table resources
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
- `leaf_candidates.csv.root_entry_weight` and `leaf_candidates.csv.root_entry_quality` come from the first chain step only.
- `leaf_candidates.csv.leaf_weight` remains terminal-entry-only for backward compatibility; it is not a path weight or probability.
- `leaf_candidates.csv.path_explicit_weights_json` lists only explicitly declared weights encountered along the resolved path.
- `leaf_candidates.csv.path_explicit_weight_product` is the product of explicit path weights only; it is not normalized chance.
- `leaf_candidates.csv.path_has_implicit_default_weights = true` means at least one chain step omitted `weight`, so the explicit product is incomplete as a chance-like proxy.
- `set_count_min` and `set_count_max` only reflect explicit terminal `minecraft:set_count` functions.
- `leaf_candidates.csv` is a path table. For source counts in Tableau, join it to `table_role_summary.csv` on `root_table_id = table_id` and filter `count_as_direct = true`.
- `raw_role` keeps the conservative local-data provenance result; `effective_role` converts `unknown_directness` to `assumed_direct_for_tableau`.
- `tables.csv.source_pack`, `tables.csv.resource_path`, and `tables.csv.is_override` identify the winning source behind each effective table row.
