# Vanilla Loot V1

Scoped vanilla loot-table export for analysis and later round-tripping.

## Summary

- Source root: `D:\keep\mods\Minecraft\my_tweaks\libs\neoforge-21.1.162_ref\data\minecraft\loot_table`
- Included table total: 65
- Excluded table total: 1113
- Named table rows: 65
- Inline table rows: 3
- Pool rows: 128
- Entry rows: 752
- Leaf candidate rows: 810
- Table role rows: 65
- Table role evidence rows: 176

## Files

- `tables.csv`: one row per named table plus synthetic inline table.
- `pools.csv`: one row per pool with roll metadata and pool-level conditions.
- `entries.csv`: one row per entry with direct metadata, raw JSON, and reference targets.
- `leaf_candidates.csv`: denormalized root-to-leaf paths for Tableau-style analysis.
- `table_role_summary.csv`: one row per named scoped table with raw and Tableau-facing directness roles.
- `table_role_evidence.csv`: evidence edges behind the table role classification.
- `scope_report.json`: included and excluded folder scope with file counts.
- `manifest.json`: export counts for tables, pools, entries, references, and leaf rows.

## Join Keys

- `tables.csv.table_id` joins to `pools.csv.table_id` and `entries.csv.table_id`.
- `pools.csv.pool_id` joins to `entries.csv.pool_id`.
- `leaf_candidates.csv.root_table_id` joins back to named rows in `tables.csv`.
- `leaf_candidates.csv.leaf_table_id` joins back to terminal rows in `tables.csv`.
- `leaf_candidates.csv.root_table_id` joins to `table_role_summary.csv.table_id` for gameplay-source filtering.
- `table_role_summary.csv.table_id` joins to `table_role_evidence.csv.table_id` for provenance drill-down.

## Included Folders

- `chests`: 56 tables
- `equipment`: 3 tables
- `pots`: 1 tables
- `spawners`: 5 tables

## Excluded Folders

- `archaeology`: 6 tables
- `blocks`: 982 tables
- `dispensers`: 3 tables
- `entities`: 100 tables
- `gameplay`: 21 tables
- `shearing`: 1 tables

## Notes

- Inline tables use synthetic IDs in the form `inline:{entry_id}`.
- Inline tables can have blank `table_type` or `random_sequence` when the embedded object omits them.
- `entries.csv.conditions_json` stores only conditions declared directly on entry objects. In this scoped vanilla export, all entry rows are `[]` because the observed conditions are pool-level instead.
- `entries.csv.quality` and `leaf_candidates.csv.leaf_quality` remain in the schema because they are valid loot fields, but they are blank for this scoped vanilla export because no included entry declares `quality`.
- `set_count_min` and `set_count_max` only reflect explicit terminal `minecraft:set_count` functions.
- This export preserves roll, weight, condition, and function structure but does not compute expected value.
- For Tableau source counts, join `leaf_candidates.csv` to `table_role_summary.csv` and filter `count_as_direct = true`.
- `raw_role` keeps the conservative local-data provenance result; `effective_role` converts `unknown_directness` to `assumed_direct_for_tableau`.
- Unknown tables are counted as direct in Tableau because missing local data-side references are not treated as proof of helper-only status.
