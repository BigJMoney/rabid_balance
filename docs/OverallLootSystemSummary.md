# Custom Loot System (Overview)

This project replaces Minecraft’s fragmented loot systems with a **single, controlled loot economy**.

Vanilla and modded loot sources are inconsistent and often overly generous. Instead of editing them individually, this system treats them as **inputs to override** and routes everything through a unified model.

---

## Core Idea

Loot is not authored per chest.

Instead, loot is generated from:

```text
item_profile + context_profile + economy_rules → loot
```

* **item_profile** = what the item is
* **context_profile** = what kind of loot opportunity this is
* **economy_rules** = global balance constraints

---

## Item Classification

Items are classified once into a canonical dataset.

### Source Files

* Schema: `loot_schema_v7.yaml`
* Item universe: `minecraft_item_ids.json`
* Tag source: `item_tags_by_item.json` 
* Tag generator: `generate_tags_by_items.ps1`

### Current properties

* `kind` — primary category (required, exclusive)
* `value` — rarity / power band
* `amount_class` — quantity band

### Invariants

* Every item has exactly one `kind`
* Classification is **first-match / authoritative**
* `value` and `amount_class` are defaults attached to `kind`

### Implementation

* Resolver: `resolve_items_to_table.py` 

This script:

* loads item IDs + tags
* applies schema rules
* outputs the canonical dataset

---

## Tag Generation (Upstream)

Tags are not authored manually per item.

They are generated via:

* `generate_tags_by_items.ps1`

This script produces:

* `item_tags_by_item.json` (used by the resolver) 
* a parallel tag dataset for KubeJS

### Role in the system

This is a **shared upstream dependency**:

1. **Classification input**
   → provides the initial tag surface for rule matching

2. **Runtime tagging (KubeJS)**
   → ensures the same tag semantics exist in-game

This keeps **classification and runtime behavior aligned**.

---

## Next Property: Affinity

Affinity adds contextual meaning to items.

Examples:

* `nether`, `end`, `underground`
* `sea`, `desert`, `arctic`
* `village`, `nature`

### Invariants

* Optional (not all items need it)
* Additive (0–many values)
* Not resolved the same way as `kind`

---

## Loot Context

Loot context describes the **type of loot opportunity**, not the loot itself.

Contexts are derived primarily from **structures / loot sources**.

Example:

```yaml
basic_adventure:
  location: overworld_underground
  structure_class: dungeon
  environment: underground
```

### Key idea

Loot context is **not hypothetical** — it is the input to generation.

---

## Loot Generation (Planned)

The system will generate loot tables from:

1. item dataset (resolver output)
2. context definition
3. economy rules

High-level flow:

* filter valid items
* apply base weighting (`value`, `kind`)
* apply context influence (`affinity`, etc.)
* apply global balancing rules
* output a loot table

---

## Source Routing

All loot sources are mapped into the system:

```text
loot_table_id → context → generated_table
```

Example:

```text
minecraft:chests/simple_dungeon
  → basic_adventure
  → yourpack:generated/basic_adventure
```

### Important

* You map **loot sources**, not blocks
* This mapping is the main manual step

---

## Minecraft Integration

LootJS (via KubeJS) is used to:

* replace loot tables by ID
* redirect sources to generated tables
* consume generated tag datasets

### Boundary

LootJS is the **application layer**, not the source of truth.

---

## Pipeline

```text
Minecraft world load
  → KubeJS server scripts run
  → tag webserver becomes available
  → generate_tags_by_items.ps1
  → item_tags_by_item.json (base tags)
  → resolve_items_to_table.py
  → generated loot-tag mapping / canonical loot outputs
  → copy generated loot-tag table into kubejs export/input location
  → reload world so KubeJS applies new loot tags
  → generate_tags_by_items.ps1 again
  → item_tags_by_item.json now includes rabidbalance loot tags
  → (future) loot table generator
```
>**Current workflow note:** the upstream tag export is currently iterative, not one-shot. Minecraft/KubeJS must run once to expose the base tag data, then again after resolver output is fed back into KubeJS so the exported tag set includes the newly assigned loot tags.
---

## Current Status

Implemented:

* item classification system (`kind`, `value`, `amount_class`)
* resolver + outputs (see report) 

In progress:

* affinity dimension
* context modeling

Not yet implemented:

* loot table generator
* full routing map
* full modded loot interception

---

## Summary

This system builds a **canonical loot authority layer** that:

* classifies items once (resolver + schema)
* derives tags from a shared generator
* defines reusable loot contexts
* generates loot programmatically
* replaces all existing loot sources

The end goal is consistent, controlled, and extensible loot across the entire pack.
