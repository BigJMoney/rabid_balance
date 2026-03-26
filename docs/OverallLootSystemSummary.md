# Custom Loot System (Overview)

This project replaces Minecraft’s fragmented loot systems with a **single, controlled loot economy**.

Vanilla and modded loot sources are inconsistent and often overly generous. Instead of editing them individually, this system treats them as **inputs to override** and routes everything through a unified model.

---

## Core Idea

Loot is not authored per chest.

Instead, loot is generated from:

```text
item_profile + context_profile + policy + value_model → loot
```

* **item_profile** = what the item is
* **context_profile** = what kind of loot opportunity this is
* **policy** = how context influences selection
* **value_model** = how rarity/power is distributed

---

## Item Classification

Items are classified once into a canonical dataset.

### Properties

* `function` — primary category (exclusive)
* `value` — rarity / power band
* `amount_class` — quantity band
* `affinities` — contextual tags (0–many)

### Invariants

* Every item has exactly one `function`
* Classification is **first-match / authoritative**
* `value` and `amount_class` are defaults attached to `function`
* `affinities` are additive and non-exclusive

### Implementation

* Schema: `loot_schema_v8.yaml`
* Resolver: `resolve_items_to_table.py`

This produces the canonical item dataset used by all downstream systems.

---

## Loot Context

Loot context describes the **type of loot opportunity**, not specific loot.

Contexts are derived from structures / sources:

```yaml
abandoned_mineshaft:
  realm: underworld
  activity: mining
  structure_class: dungeon
```

### Key Role

Context provides **descriptive inputs** used by policy to shape loot.

It does not directly define allowed items or weights.

---

## Policy Layer

Policy converts context into **selection behavior**.

It operates over both:

* **functions** (mechanical categories)
* **affinities** (thematic categories)

### Rule Types

* `allow`
* `disallow`
* `favor`
* `disfavor`

### Structure

Policy is typically defined globally:

```yaml
realm:
  Underworld:
    allow: [material, tool]
    favor: [underground]

activity:
  Mining:
    allow: [material]
    favor: [smithing]
    disfavor: [farming]
```

### Behavior

```text
context facts
→ policy lookup
→ combined rule sets
→ candidate shaping
```

Policy is reusable and consistent across all contexts.

---

## Local Overrides

Contexts may optionally define **local overrides**.

Used for:

* unique or special loot sources
* exceptions to global economy rules
* hand-authored thematic deviations

These apply after global policy and can:

* add/remove allowed items
* adjust favor/disfavor
* admit otherwise disallowed items

---

## Value Model

Value tables control **distribution of rarity**.

Example:

```yaml
uncommon_loot:
  junk: 0.05
  filler: 0.1
  common: 0.5
  uncommon: 0.75
  rare: 0.075
  epic: 0.005
```

This layer shapes:

* progression pacing
* loot quality curves
* overall economy balance

---

## Loot Generation Flow

```text
item dataset
→ filter by allow/disallow (function + affinity)
→ apply favor/disfavor weighting
→ apply value table
→ apply amount rules
→ output loot table
```

---

## Source Routing

All loot sources are mapped into the system:

```text
loot_table_id → context → generated_table
```

Example:

```text
minecraft:chests/simple_dungeon
  → abandoned_mineshaft
  → yourpack:generated/abandoned_mineshaft
```

---

## System Structure

```text
item classification (authoritative)
        ↓
context (descriptive)
        ↓
global policy (default behavior)
        ↓
local overrides (exceptions)
        ↓
value model (distribution)
        ↓
loot generation
```

---

## Summary

This system builds a **centralized loot authority layer** that:

* classifies items once
* separates description (context) from behavior (policy)
* allows global consistency with local exceptions
* generates loot programmatically instead of hand-authoring tables

The result is a **controlled, extensible, and coherent loot economy** across the entire pack.

---

Here’s a concise section you can drop into your Summary doc:

---

## Future Exploration 1: Economy Control Layer

The current system handles:

* **selection** via policy (`allow` / `disallow` / `favor` / `disfavor`)
* **rarity distribution** via value tables

This may be extended with an additional **economy control layer** applied after selection and value weighting.

### Purpose

Ensure overall loot economy health beyond contextual fit and rarity.

This layer answers:

> Even if an item fits the context and is correctly weighted, should it still be adjusted, limited, or suppressed?

### Potential Responsibilities

* **Abundance control**
  Prevent overrepresented items (e.g. bread, arrows) from dominating rolls

* **Progression gating**
  Suppress items that skip intended progression in early contexts

* **Craftability / replaceability adjustment**
  Reduce presence of easily crafted or trivial items in high-value loot

* **Duplicate suppression**
  Limit repeated items within a single loot container

* **Global scarcity tuning**
  Adjust overall availability of high-impact items across the pack

* **Stack / quantity caps**
  Enforce per-item or per-context quantity limits

### Conceptual Placement

```text
selection → weighting → economy control → final loot
```

### Notes

* This layer operates on **resolved item properties**, not raw context
* It is intended as a **global rule system**, not per-context mapping
* It complements, but does not replace, policy or value tables
* It may reuse existing item dimensions (e.g. value, affinities) or introduce new ones (e.g. progression tier, craftability)

---

This layer is not required for initial implementation, but may become important for maintaining long-term balance and consistency across the loot economy.
