# Block hardness tags

KubeJS scripts for Minecraft 1.21.1 / NeoForge 21.1.233. Classify blocks into `rabid:hardness/<name>` tags and set their mining hardness, blast resistance, or both.

## Installation

Install these files relative to your Minecraft instance or dedicated-server directory:

| Package file | Destination |
| --- | --- |
| `startup_scripts/rabid_hardness_startup.js` | `kubejs/startup_scripts/rabid_hardness_startup.js` |
| `server_scripts/rabid_hardness_server.js` | `kubejs/server_scripts/rabid_hardness_server.js` |
| `config/rabid_hardness.example.json` | `kubejs/config/rabid_hardness.json` (copy and rename) |

Create `kubejs/config/` and `kubejs/export/` if absent. Install only the two production scripts; tests and diagnostic scripts are optional development tools. For an existing installation, preserve your config. The scripts do not create a default config.

1. Edit `kubejs/config/rabid_hardness.json`. Initially leave `applyGenerated` set to `false`.
2. Start Minecraft and open a world, or start the server.
3. Run **`/hardness generate`** as an operator (permission level 2).
4. Review `kubejs/export/rabid_hardness.report.json` and the generated assignments.
5. Set `applyGenerated` to `true` and fully restart Minecraft/server to activate the assignments.

The supplied example assigns stone to `rabid:hardness/reinforced`, with mining hardness `50` and blast resistance `1200`.

For multiplayer, install matching scripts, config, and `rabid_hardness.generated.json` on clients and server before restarting them. Distribution is manual. Other scripts that modify block stats should have priority greater than `-10000`, so their values are captured before these scripts apply changes.

## Configuration

```json
{
  "version": 1,
  "applyGenerated": false,
  "generateOnWorldLoad": false,
  "allowProtectedBlocks": false,
  "categories": [{
    "name": "reinforced",
    "hardness": 50,
    "blastResistance": 1200,
    "include": [{ "type": "id", "value": "minecraft:stone" }],
    "exclude": []
  }]
}
```

| Setting | Purpose |
| --- | --- |
| `version` | Required config format version: `1` |
| `applyGenerated` | Apply saved assignments at startup; defaults to `false` |
| `generateOnWorldLoad` | Generate automatically when a world/server starts; defaults to `false` |
| `allowProtectedBlocks` | Allow rules to affect air, liquid blocks, and negative-hardness blocks; defaults to `false` |
| `categories` | Array of categories; `[]` generates no assignments |

Each category requires a unique `name`, a nonempty `include` array, and at least one of `hardness` or `blastResistance`. `exclude` defaults to `[]`. Names use lowercase letters, digits, `_`, `.`, and `-`, starting with a letter, digit, or `_`.

Mining hardness applies to every state of an assigned block. Blast resistance sets `explosionResistance`. Values must fit a nonnegative Java float; hardness also accepts `-1` for unbreakable. Omitted stats and unmatched blocks stay unchanged.

Any inclusion qualifies a block; any exclusion vetoes that category for that block. Duplicate category names or blocks matching multiple categories reject the entire generation. Existing generated assignments and active stats/tags remain intact on rule rejection. Overlapping blocks and their categories appear in the log and report.

The same matchers work in `include` and `exclude`:

| Matcher | Example |
| --- | --- |
| Exact block ID | `{ "type": "id", "value": "minecraft:stone" }` |
| Block tag, including nested membership | `{ "type": "tag", "value": "minecraft:logs" }` |
| Regex on namespaced block ID | `{ "type": "regex", "value": "^minecraft:.*_ore$" }` |
| Exact original mining hardness | `{ "type": "hardness", "eq": 1.5 }` |
| Hardness range | `{ "type": "hardness", "gte": 1.5, "lt": 5 }` |

Numeric comparisons support `eq`, `gt`, `gte`, `lt`, and `lte`; all comparisons in one rule must hold. They use original default-state mining hardness, captured before these scripts change it. Equality is exact; use ranges for values with float-rounding artifacts.

Regex rules optionally accept `"flags": "i"`, `"m"`, or both. Use `^` and `$` for full-ID matches and escape backslashes for JSON. Tag inputs omit `#`. Unknown IDs and nonexistent tags raise KubeJS errors; existing empty tags are valid. Reserve `rabid:hardness/` for generated outputs and do not use those tags as rule inputs.

Protected blocks are skipped globally unless enabled. Waterlogged solid blocks are not treated as liquid blocks. See `config/examples/all_matchers.json` for a complete alternative config; copy its contents into your installed config to use it.

## Generation and activation

Run `/hardness generate` after changing category rules, mods that affect blocks or their original stats, or source block tags. Reload changed datapacks before generating. Recipe- or loot-only changes do not require regeneration.

`generateOnWorldLoad: true` enables automatic generation; the manual command is always available to operators. Generation only writes output files. Existing assignments continue to apply at startup when `applyGenerated` is enabled, regardless of automatic generation. Changing these two switches does not require regeneration.

**A full Minecraft/server restart activates newly generated assignments.** `/reload` and reopening a world keep the current session's stats and hardness tags. Reloading startup scripts is rejected. The server log's `Active this session` count describes the assignments currently applied.

## Generated files and recovery

All filenames below begin with `rabid_hardness`:

| Suffix | Directory | Purpose |
| --- | --- | --- |
| `.json` | `kubejs/config/` | Your authored config, format version 1 |
| `.generated.json` | `kubejs/config/` | Runtime assignments, format version 2 |
| `.backup.json` | `kubejs/config/` | Previous generated output, saved before a changed replacement |
| `.candidate.json` | `kubejs/export/` | New output, written and verified before replacement |
| `.report.json` | `kubejs/export/` | Counts, assignment rules, matched exclusions, protected blocks, and overlaps |

Do not hand-edit generated output. The config and generated file have independent format versions.

In the report, `assignments` lists each assigned block's `id`, `category`, and `matchedRule` (the first matching inclusion in config order). `exclusions` is a separate list with the same fields, showing the first matching exclusion for each block/category veto. Exclusions are recorded only after an inclusion matches. A block can be excluded from one category and assigned to another; globally protected blocks are skipped before matching.

`protectedBlocks` lists skipped blocks with their `id`, original default-state `hardness`, and `reasons` (`air`, `fluid`, or `negative hardness`). Its length matches the `protected` count. With `allowProtectedBlocks: true`, this list is empty because protection does not skip blocks. Unmatched blocks are reported as a count only.

The `assigned` and `excluded` counts match the lengths of these lists. `excluded` counts category vetoes, so a block can count more than once. Conflicting blocks appear in `conflicts` rather than `assignments`; a report containing conflicts describes a rejected candidate, not activated output. Match details are report-only and do not change the candidate/generated file formats.

Writes are verified but not atomic. If the final write fails, a candidate and any previous backup remain available. Identical regeneration preserves the older backup.

If generated output is damaged, stop the game and move that file aside. Either restore the backup with its matching config rules, or set `applyGenerated` to `false`, restart, open a world, and run `/hardness generate` to rebuild it. After successful generation, enable application and restart. For a stale-assignment error, regenerate from your current rules and restart.

To disable changes, set `applyGenerated` to `false` and fully restart. To uninstall, remove both scripts and restart. Stat changes are process-wide and are not saved into world blocks.
