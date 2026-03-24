Yes — I think that’s the right direction, and the “structure is authoritative” idea is probably the missing anchor.

Your own notes already separate intrinsic item properties from extrinsic loot-opportunity properties, and they list `location` and `structure/source type` as context dimensions rather than item dimensions. They also explicitly describe loot as `score(item_profile, context_profile, economy_rules)` and say the resolved table is what KubeJS consumes.  

So I’d tighten your model like this:

**Structure should be the primary source of context.**
Not the only source, but the root object. A placed loot container is inside some generating circumstance, and the structure or loot source is usually what knows the strongest facts: what dimension it belongs to, what biome/environment it landed in, whether it is village-associated, what broad structure class it is, and often what danger/theme it implies. That fits your existing context list much better than treating context as something floating and hypothetical.  

That suggests a hierarchy like:

```yaml
context_profile:
  source_id: minecraft:chests/abandoned_mineshaft
  structure_class: dungeon
  location: overworld_underground
  environment: underground
  village: false
  affinity_domains: [underground]
```

Then your item side can have:

```yaml
item_profile:
  value: uncommon
  kind: material
  affinity: [underground, nature]
```

And the resolver asks:

* is this legal here?
* how much do the item’s affinities overlap the context’s affinities?
* what global economy rules still suppress or boost it?

I would also avoid making `village` a peer to everything else for very long. It probably starts as a boolean, but conceptually it feels more like either `structure_class: settlement` or a tag/domain on the context. Otherwise you may end up with awkward special casing where “village-ness” cuts across every other field. Your docs already lean toward orthogonal context attributes and away from baking combinations into special one-off categories.  

So my current read is:

* **`affinity`** is a good next intrinsic item dimension.
* **`structure/source`** should probably be the authoritative seed for `context_profile`.
* **`location` and `environment`** can be derived or normalized from the structure plus world placement.
* **`village`** is probably better as a context tag/domain than as a permanently special boolean.

The practical version is that your “mini schemas” may turn out to be less like full loot specs and more like **context templates keyed by source/structure**, with optional overrides from actual placement data. That feels very close to the architecture your docs are already pointing toward.
