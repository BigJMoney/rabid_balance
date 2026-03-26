"""
Resolve a list of Minecraft items, using a provided loot schema, to create a table that sets item value, kind and amount class for each item.

"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from fnmatch import fnmatch
from collections import Counter

import json
import yaml
import csv

BASE_DIR = Path(__file__).resolve().parent

DOCS_PATH = "../docs/"

YAML_PATH = DOCS_PATH + "loot_schema_v9.yaml"
ITEMS_PATH = DOCS_PATH + "minecraft_item_ids.json"
TAGS_BY_ITEM_PATH = DOCS_PATH + "item_tags_by_item-no_loot_tags.json"

schema_version = 0


@dataclass(frozen=True)
class AssignBlock:
    default: str
    buckets: dict[str, list[str]]


@dataclass(frozen=True)
class RuleSchema:
    rule_id: str
    priority: int
    match_selectors: list[str] | None
    assign_function: str
    assign_value: AssignBlock
    assign_amount_class: AssignBlock
    reason: str | None = None
    is_fallback: bool = False


@dataclass(frozen=True)
class AffinitySchema:
    affinity_id: str
    priority: int
    match_selectors: list[str] | None
    add: str
    reason: str | None = None


@dataclass(frozen=True)
class LootSchema:
    rules: list[RuleSchema]
    affinity_rules: list[AffinitySchema]


@dataclass(frozen=True)
class ItemRecord:
    """
    An item and its id and tags.
    """
    item_id: str
    short_name: str
    tags: frozenset[str]


@dataclass(frozen=True)
class CompiledRule:
    rule_id: str
    priority: int
    match_selectors: list[str] | None
    assign_function: str
    assign_value: AssignBlock
    assign_amount_class: AssignBlock
    reason: str | None
    is_fallback: bool


@dataclass(frozen=True)
class AffinityRule:
    rule_id: str
    priority: int
    match_selectors: list[str] | None
    add_affinity: str


@dataclass(frozen=True)
class MatchResult:
    matched: bool = False
    via: str | None = None              # explicit | tag | name_pattern | any | all
    detail: str | None = None           # exact value/pattern/tag that matched
    adetail: str | None = None          #  same but for affinity match


@dataclass(frozen=True)
class ResolvedItem:
    item_id: str
    value: str
    value_detail: str | None
    function: str
    amount_class: str
    amount_detail: str | None
    affinities: list[str]
    matched_rule_id: str
    amatched_rule_ids: list[str]
    matched_via: str
    matched_detail: str | None
    amatched_details: list[str]


# ---- File Loading

def load_yaml(path: str) -> dict[str, Any]:
    fullpath = BASE_DIR / path
    with open(fullpath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a dict: {fullpath}")
    return data


def load_item_ids(path: str) -> list[str]:
    fullpath = BASE_DIR / path
    with open(fullpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Item id file must be a list: {fullpath}")
    return [str(item_id) for item_id in data]


def load_tags_by_item(path: str) -> dict[str, set[str]]:
    fullpath = BASE_DIR / path
    with open(fullpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Tags-by-item file must be a dict: {fullpath}")

    result: dict[str, set[str]] = {}
    for item_id, tags in data.items():
        if not isinstance(tags, list):
            raise ValueError(f"Tags for {item_id} must be a list")
        result[str(item_id)] = {str(tag) for tag in tags}
    return result


def get_loot_classification(doc: dict[str, Any]) -> dict[str, Any]:
    schema = doc.get("loot_classification")
    if not isinstance(schema, dict):
        raise ValueError("Missing or invalid root key: loot_classification")
    return schema


# ---- Schema Rules

def validate_schema(raw_schema: dict[str, Any]) -> LootSchema:
    if not isinstance(raw_schema, dict):
        raise ValueError("schema must be a dict")

    version = raw_schema.get("version")
    global schema_version
    schema_version = str(version)

    # -- Property Rules
    raw_rules = raw_schema.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ValueError("schema.rules must be a non-empty list")

    rules: list[RuleSchema] = []
    seen_rule_ids: set[str] = set()

    for index, raw_rule in enumerate(raw_rules):
        rule = parse_rule_schema(raw_rule, index)

        if rule.rule_id in seen_rule_ids:
            raise ValueError(f"duplicate rule id: {rule.rule_id}")
        seen_rule_ids.add(rule.rule_id)

        rules.append(rule)

    # -- Fallback Property Rule
    fallback_rules = [rule for rule in rules if rule.is_fallback]
    if not fallback_rules:
        raise ValueError("schema must contain a fallback rule")
    if len(fallback_rules) > 1:
        raise ValueError("schema must contain exactly one fallback rule")

    if not rules[-1].is_fallback:
        raise ValueError("fallback rule must be last in schema.rules")

    # -- Affinity Rules
    raw_arules = raw_schema.get("affinity_rules")
    if not isinstance(raw_arules, list) or not raw_arules:
        raise ValueError("schema.affinity_rules must be a non-empty list")

    affinity_rules: list[AffinitySchema] = []
    seen_arule_ids: set[str] = set()

    for index, raw_arule in enumerate(raw_arules):
        arule = parse_affinity_schema(raw_arule, index)

        if arule.affinity_id in seen_arule_ids:
            raise ValueError(f"duplicate rule id: {arule.affinity_id}")
        seen_arule_ids.add(arule.affinity_id)

        affinity_rules.append(arule)

    return LootSchema(rules=rules, affinity_rules=affinity_rules)


def parse_rule_schema(raw_rule: Any, index: int) -> RuleSchema:
    where = f"rules[{index}]"

    if not isinstance(raw_rule, dict):
        raise ValueError(f"{where} must be a dict")

    rule_id = raw_rule.get("id")
    if not isinstance(rule_id, str) or not rule_id:
        raise ValueError(f"{where}.id must be a non-empty string")

    priority = raw_rule.get("priority")
    if not isinstance(priority, int):
        raise ValueError(f"{where}.priority must be an int")

    is_fallback = rule_id == "fallback"

    raw_match = raw_rule.get("match")
    if is_fallback:
        match_selectors = parse_fallback_match(raw_match, f"{where}.match")
    else:
        match_selectors = parse_selector_list(raw_match, f"{where}.match")

    raw_assign = raw_rule.get("assign")
    if not isinstance(raw_assign, dict):
        raise ValueError(f"{where}.assign must be a dict")

    assign_function = raw_assign.get("function")
    if not isinstance(assign_function, str) or not assign_function:
        raise ValueError(f"{where}.assign.function must be a non-empty string")

    assign_value = parse_assign_block(raw_assign.get("value"), f"{where}.assign.value")
    assign_amount_class = parse_assign_block(
        raw_assign.get("amount_class"),
        f"{where}.assign.amount_class",
    )

    reason = raw_rule.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError(f"{where}.reason must be a string if present")

    return RuleSchema(
        rule_id=rule_id,
        priority=priority,
        match_selectors=match_selectors,
        assign_function=assign_function,
        assign_value=assign_value,
        assign_amount_class=assign_amount_class,
        reason=reason,
        is_fallback=is_fallback,
    )


def parse_affinity_schema(raw_arule: Any, index: int) -> AffinitySchema:
    where = f"affinity rules[{index}]"

    if not isinstance(raw_arule, dict):
        raise ValueError(f"{where} must be a dict")

    affinity_id = raw_arule.get("id")
    if not isinstance(affinity_id, str) or not affinity_id:
        raise ValueError(f"{where}.id must be a non-empty string")

    priority = raw_arule.get("priority")
    if not isinstance(priority, int):
        raise ValueError(f"{where}.priority must be an int")

    raw_match = raw_arule.get("match")
    match_selectors = parse_selector_list(raw_match, f"{where}.match")

    # add = raw_arule.get("add")
    # if not isinstance(add, str) or not add:
    #     raise ValueError(f"{where}.add must be a nonstring")

    return AffinitySchema(
        affinity_id=affinity_id,
        priority=priority,
        match_selectors=match_selectors,
        add=affinity_id
    )


def parse_fallback_match(raw_match: Any, where: str) -> None:
    if not isinstance(raw_match, dict):
        raise ValueError(f"{where} must be a dict for fallback")
    summary = raw_match.get("summary")
    if not isinstance(summary, str) or not summary:
        raise ValueError(f"{where}.summary must be a non-empty string for fallback")
    return None


def parse_selector_list(raw_value: Any, where: str) -> list[str]:
    if not isinstance(raw_value, list) or not raw_value:
        raise ValueError(f"{where} must be a non-empty list")

    selectors: list[str] = []
    for i, selector in enumerate(raw_value):
        if not isinstance(selector, str) or not selector:
            raise ValueError(f"{where}[{i}] must be a non-empty string")
        selectors.append(selector)

    return selectors


def parse_assign_block(raw_value: Any, where: str) -> AssignBlock:
    if not isinstance(raw_value, dict):
        raise ValueError(f"{where} must be a dict")

    if "default" not in raw_value:
        raise ValueError(f"{where} missing required 'default' key")

    default = raw_value.get("default")
    if not isinstance(default, str) or not default:
        raise ValueError(f"{where}.default must be a non-empty string")

    buckets: dict[str, list[str]] = {}

    for bucket_name, raw_selectors in raw_value.items():
        if bucket_name == "default":
            continue

        if not isinstance(bucket_name, str) or not bucket_name:
            raise ValueError(f"{where} has an invalid bucket name")

        selectors = parse_selector_list(raw_selectors, f"{where}.{bucket_name}")
        buckets[bucket_name] = selectors

    return AssignBlock(
        default=default,
        buckets=buckets,
    )


def compile_rules(schema: LootSchema) -> list[CompiledRule]:
    compiled = [
        CompiledRule(
            rule_id=rule.rule_id,
            priority=rule.priority,
            match_selectors=rule.match_selectors,
            assign_function=rule.assign_function,
            assign_value=rule.assign_value,
            assign_amount_class=rule.assign_amount_class,
            reason=rule.reason,
            is_fallback=rule.is_fallback,
        )
        for rule in schema.rules
    ]
    # Fallback rule must have priority 0 with no other rule having 0 or lower
    compiled.sort(key=lambda rule: rule.priority, reverse=True)
    return compiled


def compile_affinity_rules(schema: LootSchema) -> list[AffinityRule]:
    compiled = [
        AffinityRule(
            rule_id=arule.affinity_id,
            priority=arule.priority,
            match_selectors=arule.match_selectors,
            add_affinity=arule.add
        )
        for arule in schema.affinity_rules
    ]
    # Fallback rule must have priority 0 with no other rule having 0 or lower
    compiled.sort(key=lambda arule: arule.priority, reverse=True)
    return compiled


# ---- Item Matching

def build_item_record(item_id: str, tags_by_item: dict[str, set[str]]) -> ItemRecord:
    return ItemRecord(
        item_id=item_id,
        short_name=item_id.split(":")[-1],
        tags=frozenset(tags_by_item.get(item_id, set())),
    )


def resolve_item(
        item: ItemRecord,
        rules: list[CompiledRule],
        arules: list[AffinityRule]
) -> ResolvedItem:
    rule, match = find_first_matching_rule(item, rules)

    kind = resolve_assign_kind(rule.assign_function)
    value, _value_detail = resolve_assign_property(item, rule.assign_value)
    amount_class, _amount_detail = resolve_assign_property(item, rule.assign_amount_class)

    arules, amatches = find_all_matching_affinities(item, arules)

    affinities = []
    amatched_details = []
    amatched_rule_ids = []
    if arules and amatches:
        affinities = [resolve_add_affinity(arule.add_affinity) for arule in arules]
        amatched_details = [amatch.detail for amatch in amatches]
        amatched_rule_ids = [arule.rule_id for arule in arules]

    return ResolvedItem(
        item_id=item.item_id,
        value=value,
        value_detail=_value_detail,
        function=kind,
        amount_class=amount_class,
        amount_detail=_amount_detail,
        affinities=affinities,
        matched_rule_id=rule.rule_id,
        amatched_rule_ids=amatched_rule_ids,
        matched_via=match.via or "unknown",
        matched_detail=match.detail,
        amatched_details=amatched_details,
    )


def find_first_matching_rule(
        item: ItemRecord,
        rules: list[CompiledRule]
) -> tuple[CompiledRule, MatchResult]:

    for rule in rules[:-1]:  # Omit the fallback rule, which isn't for matching
        result = match_selector_list(item, rule.match_selectors)
        if result.matched:
            return rule, result

    # Use the last rule (fallback) when no rule is found
    fallback_rule = rules[-1]
    if fallback_rule.rule_id != "fallback":
        raise ValueError(f"No matching rule for {item.item_id} and no fallback rule found")

    result = MatchResult(
        matched=True,  # Falling back counts as a "match"
        via="fallback",
        detail="no match"
    )
    return fallback_rule, result


def find_all_matching_affinities(
        item: ItemRecord,
        arules: list[AffinityRule]
) -> tuple[list[AffinityRule], list[MatchResult]]:

    rule_results = []
    match_results = []

    for arule in arules:  # Affinity rules don't have a fallback
        result = match_selector_list(item, arule.match_selectors)
        if result.matched:
            rule_results.append(arule)
            match_results.append(result)
    return rule_results, match_results


def match_selector_list(item: ItemRecord, selectors: list[str]) -> MatchResult:
    for selector in selectors:
        result = match_selector(item, selector)
        if result.matched:
            return result
    return MatchResult()


def match_selector(item: ItemRecord, selector: str) -> MatchResult:
    if looks_like_explicit_item_id(selector):
        if item.item_id == selector:
            return MatchResult(True, "explicit", selector)
        return MatchResult()

    if fnmatch(item.short_name, selector):
        return MatchResult(True, "name_pattern", selector)

    # Tags must not contain '*' or '?' or other wildcard sumbols
    if selector.startswith("#"):
        tag = selector[1:]
        if tag in item.tags:
            return MatchResult(True, "tag", selector)
        return MatchResult()

    return MatchResult()


def looks_like_explicit_item_id(selector: str) -> bool:
    return ":" in selector and not any(ch in selector for ch in "*?[]#")


# ---- Resolve Item Property Rules

def resolve_assign_property(
    item: ItemRecord,
    assign_block: AssignBlock,
) -> tuple[str, str | None]:
    # if isinstance(assign_block, str):
    #     return assign_block, None

    default_value = assign_block.default
    if default_value is None:
        raise ValueError("assign block missing required 'default'")

    for output_value, selectors in assign_block.buckets.items():
        if output_value == "default":
            continue

        if not isinstance(selectors, list):
            raise ValueError(f"assign bucket '{output_value}' must be a list")

        result = match_selector_list(item, selectors)
        if result.matched:
            return output_value, result.detail

    return default_value, "default"


def resolve_assign_kind(assign_kind: str) -> str:
    return assign_kind


def resolve_add_affinity(add_affinity: str) -> str:
    return add_affinity


# ---- Cleanup

def validate_results(results: list[ResolvedItem], item_ids: list[str]):
    if len(results) != len(item_ids):
        raise ValueError("result count does not match input item count")

    seen: set[str] = set()

    for r in results:
        if r.item_id in seen:
            raise ValueError(f"duplicate item_id: {r.item_id}")
        seen.add(r.item_id)

        if not r.function or not r.value or not r.amount_class:
            raise ValueError(f"incomplete assignment for {r.item_id}")


def write_csv(results: list[ResolvedItem], path: str):

    full_path = Path(path)

    fieldnames = [
        "item_id",
        "kind",
        "affinities",
        "value",
        "amount_class",
        "matched_rule_id",
        #  "amatched_rule_id",
        # "matched_via",  # redundant
        "matched_detail",
        "amatched_details",
    ]

    with open(full_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            writer.writerow({
                "item_id": r.item_id,
                "kind": r.function,
                "affinities": r.affinities,
                "value": r.value,
                "amount_class": r.amount_class,
                "matched_rule_id": r.matched_rule_id,
                # "amatched_rule_id": r.amatched_rule_id,  # redundant
                # "matched_via": r.matched_via,  # redundant
                "matched_detail": r.matched_detail or "",
                "amatched_details": r.amatched_details or "",
            })

    print(f"Wrote {len(results)} rows to {full_path}")


def write_json(results: list[ResolvedItem], path: str):

    full_path = Path(path)

    json_results = {}
    with open(full_path, "w", newline="", encoding="utf-8") as f:

        for r in results:
            json_item = {
                "kind": r.function,
                "affinities": r.affinities,
                "value": r.value,
                "amount_class": r.amount_class
            }
            json_results[r.item_id] = json_item

        json.dump(json_results, f, indent=4, ensure_ascii=False)
        print(f"Wrote JSON to {full_path}")


def write_report(
        results: list[ResolvedItem],
        rules: list[CompiledRule],
        arules: list[AffinityRule],
        path: str
) -> None:
    kind_counts = Counter(r.function for r in results)
    affinity_counts = Counter(c for r in results for c in r.affinities)
    value_counts = Counter(r.value for r in results)
    amount_counts = Counter(r.amount_class for r in results)
    rule_counts = Counter(r.matched_rule_id for r in results)
    arule_counts = Counter(c for r in results for c in r.amatched_rule_ids)

    fallback_items = [r.item_id for r in results if r.matched_via == "fallback"]
    dead_rules = [r.rule_id for r in rules if r.rule_id not in rule_counts]
    dead_affinities = [r.rule_id for r in arules if r.rule_id not in arule_counts]

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"total items: {len(results)}\n")
        f.write(f"fallback count: {len(fallback_items)}\n\n")

        f.write("kinds:\n")
        for k, v in kind_counts.most_common():
            f.write(f"  {k}: {v}\n")

        f.write("affinities:\n")
        for k, v in affinity_counts.most_common():
            f.write(f"  {k}: {v}\n")

        f.write("\nvalues:\n")
        for k, v in value_counts.most_common():
            f.write(f"  {k}: {v}\n")

        f.write("\namount_classes:\n")
        for k, v in amount_counts.most_common():
            f.write(f"  {k}: {v}\n")

        f.write("\ndead rules:\n")
        for r in dead_rules:
            f.write(f"  {r}\n")

        f.write("\ndead affinities:\n")
        for r in dead_affinities:
            f.write(f"  {r}\n")

        f.write("\nfallback items:\n")
        for item in fallback_items:
            f.write(f"  {item}\n")


def main() -> int:
    schemafile = load_yaml(YAML_PATH)
    schema = get_loot_classification(schemafile)
    item_ids = load_item_ids(ITEMS_PATH)
    tags_by_item = load_tags_by_item(TAGS_BY_ITEM_PATH)

    print("\n-- START")
    print(f"schema keys: {list(schema.keys())}")
    print(f"item count: {len(item_ids)}")
    print(f"tagged item count: {len(tags_by_item)}")

    print("\n-- ITEMS")
    for item_id in item_ids[:]:
        item = build_item_record(item_id, tags_by_item)
        print(item)

    schema = validate_schema(schema)
    compiled_rules = compile_rules(schema)
    compiled_affinity_rules = compile_affinity_rules(schema)

    print("\n-- RULES")
    print(f"rule count: {len(compiled_rules)}")
    for rule in compiled_rules[:]:
        print(rule)
    print("\n")
    print(f"affinity rule count: {len(compiled_affinity_rules)}")
    for arule in compiled_affinity_rules[:]:
        print(arule)

    results = []
    item_ids = item_ids[:]

    print("\n-- ITEM MATCHES")
    matched = 0
    amatched = 0
    fallback = 0

    for item_id in item_ids:
        item = build_item_record(item_id, tags_by_item)
        try:
            resolved = resolve_item(item, compiled_rules, compiled_affinity_rules)
            results.append(resolved)
            print(resolved)

            if resolved.matched_via == "fallback":
                fallback += 1
            else:
                matched += 1
            if resolved.affinities:
                amatched += 1

        except ValueError:
            print(item.item_id, "-> NO MATCH")
            raise
        except NotImplementedError as e:
            print(item.item_id, "-> NOT IMPLEMENTED:", e)

    validate_results(results, item_ids)

    print("\n-- COVERAGE REPORT")
    print("property rules matched:", matched)
    print("property rules fallback:", fallback)
    print("items with 1 or more affinities:", amatched)

    write_path = DOCS_PATH + f"resolved_loot_v{schema_version}"
    results = sorted(results, key=lambda r: (r.matched_via != "fallback", r.item_id))

    write_csv(results, f"{write_path}.csv")
    write_json(results, f"{write_path}.json")
    write_report(results, compiled_rules, compiled_affinity_rules, f"{write_path}_report.txt")

    return 0


if __name__ == "__main__":
    main()
