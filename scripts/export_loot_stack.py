from __future__ import annotations

import argparse
import ast
import csv
import gzip
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_PACK_ROOT = PROJECT_ROOT / "libs" / "neoforge-21.1.162_ref"
DEFAULT_MODS_ROOT = PROJECT_ROOT / "libs"
DEFAULT_IGNORE_ROOT = DEFAULT_MODS_ROOT / "ignore"
DEFAULT_SCOPE_CONFIG = PROJECT_ROOT / "configs" / "loot_scope.json"
DEFAULT_AMBIGUOUS_STRUCTURE_RESOLUTION_CONFIG = (
    PROJECT_ROOT / "configs" / "structure_loot_ambiguous_resolution_map.yaml"
)
DEFAULT_MANUAL_STRUCTURE_RESOLUTION_CONFIG = (
    PROJECT_ROOT / "configs" / "structure_loot_manual_resolution_map.yaml"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "loot_docs" / "loot_stack_v1"
DEFAULT_CLASSIFICATION_SEARCH_ROOT = PROJECT_ROOT / "docs" / "loot_docs"
DEFAULT_PRECHECK_FILENAME = "precheck_report.json"
DEFAULT_STRUCTURE_LOOT_RESOLUTION_REPORT = "structure_loot_resolution_report.json"
DIRECT_ASSIGNMENT_DIRS = ("worldgen/processor_list",)
DIRECT_ASSIGNMENT_KEYS = {"loot_table", "LootTable"}
STRUCTURE_EVIDENCE_TYPE = "structure_nbt"
LOOT_REF_EVIDENCE_TYPE = "loot_table_ref"
DATA_ASSIGNMENT_EVIDENCE_TYPE = "data_assignment_json"
GLM_REGISTRY_RESOURCE_PATH = "neoforge/loot_modifiers/global_loot_modifiers.json"
LOOT_ID_SEARCH_PATTERN = re.compile(rb"[a-z_](?:[a-z0-9_.-]*):[a-z0-9_./-]+")
RESOLVED_LOOT_FILENAME_PATTERN = re.compile(r"resolved_loot_v(?P<version>\d+)\.csv$")

STRUCTURE_FAMILY_TYPE_REGISTRY = {
    "end_city": "minecraft:end_city",
    "igloo": "minecraft:igloo",
    "labyrinth": "illagerinvasion:labyrinth",
    "ocean_ruin": "minecraft:ocean_ruin",
    "ruined_portal": "minecraft:ruined_portal",
    "shipwreck": "minecraft:shipwreck",
    "woodland_mansion": "minecraft:woodland_mansion",
}

LOOSE_TABLE_CANDIDATE_REGISTRY = {
    "minecraft:chests/abandoned_mineshaft": [
        ("minecraft:mineshafts", "minecraft:mineshaft"),
        ("minecraft:mineshafts", "minecraft:mineshaft_mesa"),
    ],
    "minecraft:chests/buried_treasure": [("minecraft:buried_treasures", "minecraft:buried_treasure")],
    "minecraft:chests/desert_pyramid": [("minecraft:desert_pyramids", "minecraft:desert_pyramid")],
    "minecraft:chests/end_city_treasure": [("minecraft:end_cities", "minecraft:end_city")],
    "minecraft:chests/igloo_chest": [("minecraft:igloos", "minecraft:igloo")],
    "minecraft:chests/jungle_temple": [("minecraft:jungle_temples", "minecraft:jungle_pyramid")],
    "minecraft:chests/jungle_temple_dispenser": [("minecraft:jungle_temples", "minecraft:jungle_pyramid")],
    "minecraft:chests/nether_bridge": [("minecraft:nether_complexes", "minecraft:fortress")],
    "minecraft:chests/shipwreck_map": [
        ("minecraft:shipwrecks", "minecraft:shipwreck"),
        ("minecraft:shipwrecks", "minecraft:shipwreck_beached"),
    ],
    "minecraft:chests/shipwreck_supply": [
        ("minecraft:shipwrecks", "minecraft:shipwreck"),
        ("minecraft:shipwrecks", "minecraft:shipwreck_beached"),
    ],
    "minecraft:chests/shipwreck_treasure": [
        ("minecraft:shipwrecks", "minecraft:shipwreck"),
        ("minecraft:shipwrecks", "minecraft:shipwreck_beached"),
    ],
    "minecraft:chests/stronghold_corridor": [("minecraft:strongholds", "minecraft:stronghold")],
    "minecraft:chests/stronghold_crossing": [("minecraft:strongholds", "minecraft:stronghold")],
    "minecraft:chests/stronghold_library": [("minecraft:strongholds", "minecraft:stronghold")],
    "minecraft:chests/trial_chambers/intersection": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:chests/trial_chambers/reward_common": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:chests/trial_chambers/reward_rare": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:chests/trial_chambers/reward_unique": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:chests/trial_chambers/reward_ominous_common": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:chests/trial_chambers/reward_ominous_rare": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:chests/trial_chambers/reward_ominous_unique": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:chests/underwater_ruin_big": [
        ("minecraft:ocean_ruins", "minecraft:ocean_ruin_cold"),
        ("minecraft:ocean_ruins", "minecraft:ocean_ruin_warm"),
    ],
    "minecraft:chests/underwater_ruin_small": [
        ("minecraft:ocean_ruins", "minecraft:ocean_ruin_cold"),
        ("minecraft:ocean_ruins", "minecraft:ocean_ruin_warm"),
    ],
    "minecraft:chests/woodland_mansion": [("minecraft:woodland_mansions", "minecraft:mansion")],
    "minecraft:equipment/trial_chamber": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:spawners/trial_chamber/consumables": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
    "minecraft:spawners/trial_chamber/items_to_drop_when_ominous": [
        ("minecraft:trial_chambers", "minecraft:trial_chambers")
    ],
    "minecraft:spawners/trial_chamber/key": [("minecraft:trial_chambers", "minecraft:trial_chambers")],
}

AMBIGUOUS_RESOLUTION_YAML_HEADER = [
    "# One-to-many model:",
    "# A single loot_table_id may legitimately map to multiple structure_set_id + structure_id pairs.",
    "# Each entry in this file represents one ambiguous candidate relationship at that exact grain.",
    "# Do not assume loot_table_id is unique within this document.",
]

MANUAL_RESOLUTION_YAML_HEADER = [
    "# One-to-many model:",
    "# A single loot_table_id may legitimately map to multiple structure_set_id + structure_id pairs.",
    "# Each entry in this file represents one unresolved or mapped relationship at that exact grain.",
    "# An unresolved placeholder row may remain beside mapped rows while research is still in progress.",
    "# Removing the unresolved placeholder row is the signal that manual research is complete.",
]

TABLES_FIELDNAMES = [
    "table_id",
    "table_id_kind",
    "generated_from_entry_id",
    "namespace",
    "path",
    "category",
    "table_type",
    "random_sequence",
    "source_pack",
    "source_file",
    "resource_path",
    "is_override",
]

POOLS_FIELDNAMES = [
    "pool_id",
    "table_id",
    "pool_index",
    "rolls_kind",
    "rolls_min",
    "rolls_max",
    "rolls_raw",
    "bonus_rolls_kind",
    "bonus_rolls_min",
    "bonus_rolls_max",
    "bonus_rolls_raw",
    "condition_types",
    "conditions_json",
]

ENTRIES_FIELDNAMES = [
    "entry_id",
    "pool_id",
    "table_id",
    "entry_path",
    "entry_type",
    "name",
    "value_kind",
    "ref_table_id",
    "inline_table_id",
    "weight",
    "quality",
    "pool_weight_share",
    "condition_types",
    "function_types",
    "conditions_json",
    "functions_json",
    "raw_entry_json",
]

LEAF_FIELDNAMES = [
    "root_table_id",
    "root_category",
    "root_table_type",
    "root_pool_index",
    "root_entry_id",
    "leaf_table_id",
    "leaf_entry_id",
    "leaf_kind",
    "item_id",
    "chain_depth",
    "selection_chain_json",
    "path_condition_types",
    "path_function_types",
    "root_entry_weight",
    "root_entry_quality",
    "leaf_weight",
    "leaf_quality",
    "root_pool_weight_share",
    "path_pool_shares_json",
    "path_pool_share_product",
    "path_explicit_weights_json",
    "path_explicit_weight_product",
    "set_count_min",
    "set_count_max",
    "unresolved_reason",
]

TABLE_ROLE_SUMMARY_FIELDNAMES = [
    "table_id",
    "category",
    "inbound_loot_ref_count",
    "outbound_loot_ref_count",
    "structure_ref_count",
    "data_assignment_ref_count",
    "raw_role",
    "effective_role",
    "count_as_direct",
    "evidence_sources",
    "notes",
]

TABLE_ROLE_EVIDENCE_FIELDNAMES = [
    "table_id",
    "evidence_type",
    "source_path",
    "source_object",
    "target_table_id",
]

ITEM_CLASSIFICATION_FIELDNAMES = [
    "item_id",
    "function",
    "value",
    "amount_class",
    "matched_rule_id",
    "matched_detail",
    "classification_status",
    "is_fallback_match",
    "classification_version",
]

ITEM_AFFINITIES_FIELDNAMES = [
    "item_id",
    "affinity",
    "classification_version",
]

CLASSIFICATION_COVERAGE_FIELDNAMES = [
    "item_id",
    "loot_root_table_count",
    "loot_leaf_row_count",
    "has_classification",
    "classification_status",
    "is_fallback_match",
    "function",
    "value",
    "amount_class",
    "matched_rule_id",
    "matched_detail",
    "classification_version",
]

GLM_MODIFIER_CHAIN_FIELDNAMES = [
    "glm_index",
    "modifier_id",
    "modifier_type",
    "modifier_pack_id",
    "target_table_id",
    "payload_table_id",
    "target_in_stage1_scope",
    "analysis_status",
    "modifier_source_path",
]

MODIFIER_ADDED_LEAF_FIELDNAMES = [
    "glm_index",
    "modifier_id",
    "modifier_type",
    "modifier_pack_id",
    "target_table_id",
    "payload_table_id",
    "payload_root_pool_index",
    "payload_root_entry_id",
    "leaf_table_id",
    "leaf_entry_id",
    "leaf_kind",
    "item_id",
    "chain_depth",
    "selection_chain_json",
    "path_condition_types",
    "path_function_types",
    "root_entry_weight",
    "root_entry_quality",
    "leaf_weight",
    "leaf_quality",
    "root_pool_weight_share",
    "path_pool_shares_json",
    "path_pool_share_product",
    "path_explicit_weights_json",
    "path_explicit_weight_product",
    "set_count_min",
    "set_count_max",
    "unresolved_reason",
    "analysis_status",
]

TARGET_TABLE_MODIFIER_SUMMARY_FIELDNAMES = [
    "target_table_id",
    "modifier_count",
    "supported_modifier_count",
    "unsupported_modifier_count",
    "added_leaf_row_count",
    "added_unique_item_count",
    "novel_item_count",
    "overlap_item_count",
    "modifier_pack_ids",
    "modifier_ids_json",
]

TARGET_TABLE_ADDED_ITEM_SUMMARY_FIELDNAMES = [
    "target_table_id",
    "item_id",
    "modifier_count",
    "added_path_count",
    "added_explicit_weight_sum",
    "is_novel_to_target",
    "modifier_ids_json",
]

STRUCTURE_SET_ENTRIES_FIELDNAMES = [
    "structure_set_id",
    "structure_id",
    "structure_weight_in_set",
    "structure_type",
    "structure_set_pack_id",
    "structure_pack_id",
    "structure_set_source_path",
    "structure_source_path",
    "dynamic_mapping_status",
]

STRUCTURE_SET_LOOT_LINKS_FIELDNAMES = [
    "structure_set_id",
    "structure_id",
    "loot_table_id",
    "is_in_stage1_loot_scope",
    "link_source",
    "link_method",
    "notes",
]

STRUCTURE_SET_LOOT_LINK_AUDIT_FIELDNAMES = [
    "structure_set_id",
    "structure_id",
    "loot_table_id",
    "candidate_source",
    "candidate_method",
    "resolution",
    "notes",
]

STRUCTURE_SET_BASE_ITEM_PRESENCE_FIELDNAMES = [
    "structure_set_id",
    "structure_id",
    "item_id",
    "source_loot_table_count",
    "source_loot_table_ids_json",
]

STRUCTURE_SET_EFFECTIVE_ITEM_PRESENCE_FIELDNAMES = [
    "structure_set_id",
    "structure_id",
    "item_id",
    "item_presence_kind",
    "base_loot_table_count",
    "base_loot_table_ids_json",
    "stage2_modifier_count",
    "stage2_modifier_ids_json",
]

STRUCTURE_SET_PROFILE_SUMMARY_FIELDNAMES = [
    "structure_set_id",
    "structure_id",
    "base_loot_table_count",
    "manual_active_link_count",
    "detected_active_link_count",
    "out_of_scope_loot_table_count",
    "base_unique_item_count",
    "effective_unique_item_count",
    "stage2_added_unique_item_count",
]


class PrecheckFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class ScopeSettings:
    allowed_loot_dirs: tuple[str, ...]
    deferred_loot_dirs: tuple[str, ...]
    source: str


@dataclass
class PackSource:
    pack_id: str
    root_path: Path
    kind: str
    role: str
    explicit: bool
    discovery_source: str
    resource_paths: list[str]

    def to_report_row(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "role": self.role,
            "kind": self.kind,
            "explicit": self.explicit,
            "discovery_source": self.discovery_source,
            "path": str(self.root_path),
            "resource_count": len(self.resource_paths),
        }


@dataclass
class ResourceContribution:
    resource_path: str
    pack: PackSource

    def to_report_row(self) -> dict[str, Any]:
        return {
            "resource_path": self.resource_path,
            "pack_id": self.pack.pack_id,
            "role": self.pack.role,
            "kind": self.pack.kind,
            "source_path": display_pack_resource_path(self.pack, self.resource_path),
        }


@dataclass
class EffectiveResource:
    resource_path: str
    pack: PackSource
    contributor_count: int
    is_override: bool

    def display_source_path(self) -> str:
        return display_pack_resource_path(self.pack, self.resource_path)


@dataclass(frozen=True)
class ClassificationRecord:
    item_id: str
    function: str
    affinities: tuple[str, ...]
    value: str
    amount_class: str
    matched_rule_id: str
    matched_detail: str
    classification_status: str
    is_fallback_match: bool
    classification_version: str


@dataclass
class TableRecord:
    table_id: str
    table_id_kind: str
    generated_from_entry_id: str
    namespace: str
    path: str
    category: str
    table_type: str
    random_sequence: str
    source_pack: str
    source_file: str
    resource_path: str
    is_override: bool
    display_source_path: str
    data: dict[str, Any]
    pool_ids: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_row(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "table_id_kind": self.table_id_kind,
            "generated_from_entry_id": self.generated_from_entry_id,
            "namespace": self.namespace,
            "path": self.path,
            "category": self.category,
            "table_type": self.table_type,
            "random_sequence": self.random_sequence,
            "source_pack": self.source_pack,
            "source_file": self.source_file,
            "resource_path": self.resource_path,
            "is_override": "true" if self.is_override else "false",
        }


@dataclass
class PoolRecord:
    pool_id: str
    table_id: str
    pool_index: int
    rolls_kind: str
    rolls_min: float | None
    rolls_max: float | None
    rolls_raw: str
    bonus_rolls_kind: str
    bonus_rolls_min: float | None
    bonus_rolls_max: float | None
    bonus_rolls_raw: str
    condition_types: list[str]
    conditions: list[Any]
    raw_pool: dict[str, Any]
    pool_total_effective_weight: int | float | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "table_id": self.table_id,
            "pool_index": self.pool_index,
            "rolls_kind": self.rolls_kind,
            "rolls_min": as_csv_value(self.rolls_min),
            "rolls_max": as_csv_value(self.rolls_max),
            "rolls_raw": self.rolls_raw,
            "bonus_rolls_kind": self.bonus_rolls_kind,
            "bonus_rolls_min": as_csv_value(self.bonus_rolls_min),
            "bonus_rolls_max": as_csv_value(self.bonus_rolls_max),
            "bonus_rolls_raw": self.bonus_rolls_raw,
            "condition_types": join_types(self.condition_types),
            "conditions_json": json_cell(self.conditions),
        }


@dataclass
class EntryRecord:
    entry_id: str
    pool_id: str
    table_id: str
    entry_path: str
    entry_type: str
    name: str
    value_kind: str
    ref_table_id: str
    inline_table_id: str
    weight: int | float | None
    quality: int | float | None
    effective_weight: int | float | None
    pool_total_effective_weight: int | float | None
    pool_weight_share: float | None
    condition_types: list[str]
    function_types: list[str]
    conditions: list[Any]
    functions: list[Any]
    raw_entry: dict[str, Any]

    def to_row(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "pool_id": self.pool_id,
            "table_id": self.table_id,
            "entry_path": self.entry_path,
            "entry_type": self.entry_type,
            "name": self.name,
            "value_kind": self.value_kind,
            "ref_table_id": self.ref_table_id,
            "inline_table_id": self.inline_table_id,
            "weight": as_csv_value(self.weight),
            "quality": as_csv_value(self.quality),
            "pool_weight_share": as_csv_value(self.pool_weight_share),
            "condition_types": join_types(self.condition_types),
            "function_types": join_types(self.function_types),
            "conditions_json": json_cell(self.conditions),
            "functions_json": json_cell(self.functions),
            "raw_entry_json": json_cell(self.raw_entry),
        }


@dataclass
class RoleEvidenceRecord:
    table_id: str
    evidence_type: str
    source_path: str
    source_object: str
    target_table_id: str

    def to_row(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "evidence_type": self.evidence_type,
            "source_path": self.source_path,
            "source_object": self.source_object,
            "target_table_id": self.target_table_id,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export layered loot-table data from the vanilla base pack plus selected mod packs."
    )
    parser.add_argument(
        "--scope-config",
        type=Path,
        default=DEFAULT_SCOPE_CONFIG,
        help="JSON scope config with allowed_loot_dirs and deferred_loot_dirs.",
    )
    parser.add_argument(
        "--pack-order-manifest",
        type=Path,
        default=None,
        help="Optional JSON pack-order manifest used to resolve mod-vs-mod overlaps.",
    )
    parser.add_argument(
        "--mods-root",
        type=Path,
        default=DEFAULT_MODS_ROOT,
        help="Directory scanned non-recursively for extracted mod packs that contain data/.",
    )
    parser.add_argument(
        "--ignore-root",
        type=Path,
        action="append",
        default=[DEFAULT_IGNORE_ROOT],
        help="Directory whose descendants are ignored during auto-discovery and archive-root scans.",
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        action="append",
        default=[],
        help="Directory scanned non-recursively for .zip and .jar pack archives.",
    )
    parser.add_argument(
        "--pack",
        type=Path,
        action="append",
        default=[],
        help="Explicit directory or archive pack to include.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write reports and CSV outputs to.",
    )
    parser.add_argument(
        "--classification-csv",
        type=Path,
        default=None,
        help="Optional resolved_loot_v*.csv classification source. Defaults to the latest file under docs/loot_docs.",
    )
    parser.add_argument(
        "--ambiguous-structure-resolution-config",
        type=Path,
        default=DEFAULT_AMBIGUOUS_STRUCTURE_RESOLUTION_CONFIG,
        help="Global YAML file for ambiguous structure_set loot-table candidate rows with autoresolve flags.",
    )
    parser.add_argument(
        "--manual-structure-resolution-config",
        type=Path,
        default=DEFAULT_MANUAL_STRUCTURE_RESOLUTION_CONFIG,
        help="Global YAML file for no-match structure_set loot-table manual resolutions.",
    )
    return parser.parse_args(argv)


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def join_types(values: list[str] | tuple[str, ...]) -> str:
    return "|".join(values)


def as_csv_value(value: Any) -> Any:
    return "" if value is None else value


def is_explicit_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def get_effective_weight(value: Any) -> int | float:
    if is_explicit_number(value):
        return value
    return 1


def parse_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def parse_affinity_cell(raw_value: str) -> tuple[str, ...]:
    if not raw_value:
        return ()
    try:
        parsed = ast.literal_eval(raw_value)
    except (SyntaxError, ValueError):
        return (raw_value,)
    if isinstance(parsed, str):
        return (parsed,)
    if isinstance(parsed, (list, tuple)):
        return tuple(str(value) for value in parsed)
    return (str(parsed),)


def infer_classification_version(path: Path) -> str:
    match = RESOLVED_LOOT_FILENAME_PATTERN.fullmatch(path.name)
    if match:
        return match.group("version")
    return ""


def find_latest_classification_csv(search_root: Path) -> Path | None:
    if not search_root.exists():
        return None
    candidates: list[tuple[int, Path]] = []
    for path in search_root.glob("resolved_loot_v*.csv"):
        match = RESOLVED_LOOT_FILENAME_PATTERN.fullmatch(path.name)
        if match:
            candidates.append((int(match.group("version")), path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1].name.lower()))
    return candidates[-1][1]


def load_classification_records(path: Path | None) -> dict[str, ClassificationRecord]:
    if path is None or not path.exists():
        return {}
    version = infer_classification_version(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        records: dict[str, ClassificationRecord] = {}
        for row in reader:
            item_id = (row.get("item_id") or "").strip()
            if not item_id:
                continue
            if item_id in records:
                raise ValueError(f"duplicate item_id in classification csv: {item_id}")
            row_version = (row.get("classification_version") or "").strip() or version
            classification_status = (row.get("classification_status") or "").strip()
            if not classification_status:
                classification_status = "fallback" if parse_boolish(row.get("is_fallback_match")) else "matched"
            is_fallback_match = parse_boolish(row.get("is_fallback_match")) or classification_status == "fallback"
            records[item_id] = ClassificationRecord(
                item_id=item_id,
                function=(row.get("function") or "").strip(),
                affinities=parse_affinity_cell((row.get("affinities") or "").strip()),
                value=(row.get("value") or "").strip(),
                amount_class=(row.get("amount_class") or "").strip(),
                matched_rule_id=(row.get("matched_rule_id") or "").strip(),
                matched_detail=(row.get("matched_detail") or "").strip(),
                classification_status=classification_status or "matched",
                is_fallback_match=is_fallback_match,
                classification_version=row_version,
            )
    return records


def ensure_list(value: Any, where: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{where} must be a list")
    return value


def ensure_dict(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be a dict")
    return value


def collect_condition_types(node: Any) -> list[str]:
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            condition = value.get("condition")
            if isinstance(condition, str) and condition:
                found.add(condition)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(node)
    return sorted(found)


def collect_function_types(functions: list[Any]) -> list[str]:
    found: set[str] = set()
    for function in functions:
        if isinstance(function, dict):
            function_id = function.get("function")
            if isinstance(function_id, str) and function_id:
                found.add(function_id)
    return sorted(found)


def parse_roll_spec(raw_value: Any) -> dict[str, Any]:
    if isinstance(raw_value, (int, float)):
        return {
            "kind": "literal",
            "min": float(raw_value),
            "max": float(raw_value),
            "raw": json_cell(raw_value),
        }
    if isinstance(raw_value, dict):
        kind = raw_value.get("type")
        if not isinstance(kind, str) or not kind:
            kind = "object"
        min_value = raw_value.get("min")
        max_value = raw_value.get("max")
        return {
            "kind": kind,
            "min": float(min_value) if isinstance(min_value, (int, float)) else None,
            "max": float(max_value) if isinstance(max_value, (int, float)) else None,
            "raw": json_cell(raw_value),
        }
    if raw_value is None:
        return {"kind": "", "min": None, "max": None, "raw": ""}
    return {"kind": type(raw_value).__name__, "min": None, "max": None, "raw": json_cell(raw_value)}


def extract_set_count_range(functions: list[Any]) -> tuple[float | None, float | None]:
    last_range: tuple[float | None, float | None] = (None, None)
    for function in functions:
        if not isinstance(function, dict):
            continue
        if function.get("function") != "minecraft:set_count":
            continue
        count_value = function.get("count")
        if isinstance(count_value, (int, float)):
            literal = float(count_value)
            last_range = (literal, literal)
            continue
        if not isinstance(count_value, dict):
            continue
        if count_value.get("type") != "minecraft:uniform":
            continue
        min_value = count_value.get("min")
        max_value = count_value.get("max")
        if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
            last_range = (float(min_value), float(max_value))
    return last_range


def normalize_pack_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
    return normalized or "pack"


def normalize_namespaced_id(value: str, default_namespace: str) -> str:
    return value if ":" in value else f"{default_namespace}:{value}"


def parse_mod_id_from_toml_text(text: str) -> str | None:
    match = re.search(r'(?m)^\s*modId\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def read_directory_text(root_path: Path, relative_path: str) -> str | None:
    file_path = root_path / PurePosixPath(relative_path)
    if not file_path.exists() or not file_path.is_file():
        return None
    return file_path.read_text(encoding="utf-8")


def read_archive_text(archive_path: Path, relative_path: str) -> str | None:
    with zipfile.ZipFile(archive_path) as handle:
        try:
            return handle.read(relative_path).decode("utf-8")
        except KeyError:
            return None


def list_directory_data_files(pack_root: Path) -> list[str]:
    data_root = pack_root / "data"
    return sorted(
        path.relative_to(data_root).as_posix()
        for path in data_root.rglob("*")
        if path.is_file()
    )


def list_archive_data_files(archive_path: Path) -> list[str]:
    with zipfile.ZipFile(archive_path) as handle:
        return sorted(
            name.removeprefix("data/")
            for name in handle.namelist()
            if name.startswith("data/") and not name.endswith("/")
        )


def display_pack_resource_path(pack: PackSource, resource_path: str) -> str:
    if pack.kind == "directory":
        return str((pack.root_path / "data" / PurePosixPath(resource_path)).resolve())
    return f"{pack.root_path.resolve()}!data/{resource_path}"


def read_pack_bytes(pack: PackSource, resource_path: str) -> bytes:
    if pack.kind == "directory":
        return (pack.root_path / "data" / PurePosixPath(resource_path)).read_bytes()
    with zipfile.ZipFile(pack.root_path) as handle:
        return handle.read(f"data/{resource_path}")


def read_pack_text(pack: PackSource, resource_path: str) -> str:
    return read_pack_bytes(pack, resource_path).decode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def split_resource_path(resource_path: str) -> tuple[str, ...]:
    return PurePosixPath(resource_path).parts


def get_resource_family(resource_path: str) -> str:
    parts = split_resource_path(resource_path)
    if len(parts) >= 3 and parts[1] == "worldgen" and parts[2] in {
        "processor_list",
        "structure",
        "structure_set",
        "template_pool",
    }:
        return f"worldgen/{parts[2]}"
    return parts[1] if len(parts) >= 2 else ""


def get_loot_resource_metadata(resource_path: str) -> dict[str, str] | None:
    parts = split_resource_path(resource_path)
    if len(parts) < 4 or parts[1] != "loot_table" or not resource_path.endswith(".json"):
        return None
    return {
        "namespace": parts[0],
        "loot_dir": parts[2],
        "path": PurePosixPath(*parts[2:]).with_suffix("").as_posix(),
        "source_file": PurePosixPath(*parts[2:]).as_posix(),
    }


def split_loot_table_id(table_id: str) -> tuple[str, str]:
    namespace, path = table_id.split(":", 1)
    return namespace, path


def loot_table_id_to_resource_path(table_id: str) -> str:
    namespace, path = split_loot_table_id(table_id)
    return f"{namespace}/loot_table/{path}.json"


def resource_id_to_resource_path(resource_id: str, family: str, suffix: str) -> str:
    namespace, path = split_loot_table_id(resource_id)
    return f"{namespace}/{family}/{path}{suffix}"


def structure_id_to_resource_path(structure_id: str) -> str:
    return resource_id_to_resource_path(structure_id, "worldgen/structure", ".json")


def structure_set_id_to_resource_path(structure_set_id: str) -> str:
    return resource_id_to_resource_path(structure_set_id, "worldgen/structure_set", ".json")


def template_pool_id_to_resource_path(pool_id: str) -> str:
    return resource_id_to_resource_path(pool_id, "worldgen/template_pool", ".json")


def processor_list_id_to_resource_path(processor_list_id: str) -> str:
    return resource_id_to_resource_path(processor_list_id, "worldgen/processor_list", ".json")


def structure_template_id_to_resource_path(template_id: str) -> str:
    return resource_id_to_resource_path(template_id, "structure", ".nbt")


def resource_path_to_resource_id(resource_path: str, family: str, suffix: str) -> str | None:
    parts = split_resource_path(resource_path)
    family_parts = tuple(PurePosixPath(family).parts)
    if len(parts) < len(family_parts) + 2:
        return None
    if tuple(parts[1 : 1 + len(family_parts)]) != family_parts:
        return None
    if not resource_path.endswith(suffix):
        return None
    namespace = parts[0]
    relative_parts = parts[1 + len(family_parts) :]
    path = PurePosixPath(*relative_parts).with_suffix("").as_posix()
    return f"{namespace}:{path}"


def get_structure_source_object(resource_path: str) -> str:
    parts = split_resource_path(resource_path)
    if len(parts) < 4:
        return resource_path
    return PurePosixPath(*parts[2:]).with_suffix("").as_posix()


def get_structure_family_from_source_object(source_object: str) -> str:
    normalized = source_object.strip().replace("\\", "/")
    if not normalized:
        return ""
    return normalized.split("/", 1)[0]


def write_yaml_with_header(path: Path, *, header_lines: list[str], payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    if not yaml_text.endswith("\n"):
        yaml_text += "\n"
    header_text = "\n".join(header_lines).rstrip()
    if header_text:
        header_text += "\n"
    path.write_text(f"{header_text}{yaml_text}", encoding="utf-8")


def load_scope_settings(
    scope_config_path: Path | str | None = None,
    scope_override: dict[str, Any] | None = None,
) -> ScopeSettings:
    if scope_override is not None:
        raw_data = ensure_dict(scope_override, "scope override")
        source = "<in-memory scope override>"
    else:
        if scope_config_path is None:
            raise ValueError("scope config path is required")
        scope_path = Path(scope_config_path)
        raw_data = ensure_dict(
            json.loads(scope_path.read_text(encoding="utf-8")),
            f"scope config {scope_path}",
        )
        source = str(scope_path)

    allowed = tuple(
        item.strip()
        for item in ensure_list(raw_data.get("allowed_loot_dirs"), "allowed_loot_dirs")
        if isinstance(item, str) and item.strip()
    )
    deferred = tuple(
        item.strip()
        for item in ensure_list(raw_data.get("deferred_loot_dirs"), "deferred_loot_dirs")
        if isinstance(item, str) and item.strip()
    )
    overlap = sorted(set(allowed) & set(deferred))
    if overlap:
        raise ValueError(f"scope config has dirs in both allowed and deferred sets: {', '.join(overlap)}")
    if not allowed:
        raise ValueError("scope config must declare at least one allowed_loot_dir")
    return ScopeSettings(
        allowed_loot_dirs=allowed,
        deferred_loot_dirs=deferred,
        source=source,
    )


def load_pack_order_manifest(path: Path | str | None) -> tuple[list[str], str | None]:
    if path is None:
        return [], None

    manifest_path = Path(path)
    raw_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(raw_data, list):
        pack_ids = raw_data
    elif isinstance(raw_data, dict):
        if "ordered_pack_ids" in raw_data:
            pack_ids = raw_data["ordered_pack_ids"]
        elif "pack_ids" in raw_data:
            pack_ids = raw_data["pack_ids"]
        else:
            raise ValueError(f"pack order manifest {manifest_path} must be a list or contain ordered_pack_ids")
    else:
        raise ValueError(f"pack order manifest {manifest_path} must be a list or object")

    ordered: list[str] = []
    seen: set[str] = set()
    for item in ensure_list(pack_ids, f"{manifest_path}.pack_ids"):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"pack order manifest {manifest_path} contains a non-string pack id")
        pack_id = item.strip()
        if pack_id in seen:
            raise ValueError(f"pack order manifest {manifest_path} lists {pack_id} more than once")
        seen.add(pack_id)
        ordered.append(pack_id)
    return ordered, str(manifest_path)


def build_pack_source(path: Path, role: str, explicit: bool, discovery_source: str, pack_id_override: str | None = None) -> PackSource:
    if path.is_dir():
        if not (path / "data").exists():
            raise ValueError(f"pack directory is missing data/: {path}")
        resource_paths = list_directory_data_files(path)
        mods_toml = read_directory_text(path, "META-INF/neoforge.mods.toml")
        kind = "directory"
    elif path.is_file() and path.suffix.lower() in {".zip", ".jar"}:
        resource_paths = list_archive_data_files(path)
        if not resource_paths:
            raise ValueError(f"pack archive is missing data/: {path}")
        mods_toml = read_archive_text(path, "META-INF/neoforge.mods.toml")
        kind = "archive"
    else:
        raise ValueError(f"unsupported pack source: {path}")

    pack_id = pack_id_override or parse_mod_id_from_toml_text(mods_toml or "") or normalize_pack_id(path.stem)
    return PackSource(
        pack_id=pack_id,
        root_path=path,
        kind=kind,
        role=role,
        explicit=explicit,
        discovery_source=discovery_source,
        resource_paths=resource_paths,
    )


class LootStackExporter:
    def __init__(
        self,
        *,
        base_pack_root: Path,
        mods_root: Path,
        ignore_roots: list[Path],
        archive_roots: list[Path],
        explicit_packs: list[Path],
        output_dir: Path,
        scope_settings: ScopeSettings,
        pack_order_ids: list[str],
        pack_order_source: str | None,
        auto_discover_mod_dirs: bool,
        classification_csv_path: Path | None,
        ambiguous_resolution_config_path: Path,
        manual_resolution_config_path: Path,
    ) -> None:
        self.base_pack_root = base_pack_root
        self.mods_root = mods_root
        self.ignore_roots = ignore_roots
        self.archive_roots = archive_roots
        self.explicit_packs = explicit_packs
        self.output_dir = output_dir
        self.scope_settings = scope_settings
        self.pack_order_ids = pack_order_ids
        self.pack_order_source = pack_order_source
        self.auto_discover_mod_dirs = auto_discover_mod_dirs
        self.classification_csv_path = classification_csv_path
        self.ambiguous_resolution_config_path = ambiguous_resolution_config_path
        self.manual_resolution_config_path = manual_resolution_config_path

        self.tables: dict[str, TableRecord] = {}
        self.pools: dict[str, PoolRecord] = {}
        self.entries: dict[str, EntryRecord] = {}
        self.entry_id_by_key: dict[tuple[str, int, str], str] = {}
        self.entry_ids_by_pool: dict[str, list[str]] = defaultdict(list)
        self.named_table_ids: list[str] = []
        self.leaf_rows: list[dict[str, Any]] = []
        self.table_role_summary_rows: list[dict[str, Any]] = []
        self.table_role_evidence_rows: list[dict[str, Any]] = []
        self.glm_modifier_chain_rows: list[dict[str, Any]] = []
        self.modifier_added_leaf_rows: list[dict[str, Any]] = []
        self.target_table_modifier_summary_rows: list[dict[str, Any]] = []
        self.target_table_added_item_summary_rows: list[dict[str, Any]] = []
        self.stage2_report: dict[str, Any] = {}
        self.stage2_payload_leaf_cache: dict[str, list[dict[str, Any]]] = {}
        self.item_classification_rows: list[dict[str, Any]] = []
        self.item_affinity_rows: list[dict[str, Any]] = []
        self.classification_coverage_rows: list[dict[str, Any]] = []
        self.structure_set_entry_rows: list[dict[str, Any]] = []
        self.structure_set_loot_link_rows: list[dict[str, Any]] = []
        self.structure_set_loot_link_audit_rows: list[dict[str, Any]] = []
        self.structure_set_base_item_presence_rows: list[dict[str, Any]] = []
        self.structure_set_effective_item_presence_rows: list[dict[str, Any]] = []
        self.structure_set_profile_summary_rows: list[dict[str, Any]] = []
        self.structure_loot_resolution_report: dict[str, Any] = {}
        self.raw_role_counts: Counter[str] = Counter()
        self.effective_role_counts: Counter[str] = Counter()
        self.classification_records: dict[str, ClassificationRecord] = {}
        self.classification_version: str = ""

        self.named_reference_count = 0
        self.inline_reference_count = 0

        self.discovered_packs: list[PackSource] = []
        self.selected_packs_by_id: dict[str, PackSource] = {}
        self.ordered_packs: list[PackSource] = []
        self.resource_contributions: dict[str, list[ResourceContribution]] = {}
        self.effective_resources: dict[str, EffectiveResource] = {}
        self.precheck_report: dict[str, Any] = {}

    def _normalized_ignore_roots(self) -> list[Path]:
        roots: list[Path] = []
        seen: set[Path] = set()
        for root in self.ignore_roots:
            resolved = root.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            roots.append(resolved)
        return roots

    def _is_ignored_path(self, path: Path, ignore_roots: list[Path]) -> bool:
        resolved = path.resolve()
        for ignore_root in ignore_roots:
            try:
                resolved.relative_to(ignore_root)
                return True
            except ValueError:
                continue
        return False

    def export(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        precheck_report = self._run_precheck()
        write_json(self.output_dir / DEFAULT_PRECHECK_FILENAME, precheck_report)
        fatal_errors = precheck_report.get("fatal_errors", [])
        if fatal_errors:
            raise PrecheckFailed("\n".join(fatal_errors))

        self._build_effective_resources()
        scope_report = self._discover_scope_report()
        self._parse_named_tables()
        self._validate_references()
        self._compute_pool_weight_metrics()
        self._build_leaf_rows()
        self._build_table_roles()
        self._build_stage2_outputs()
        self._build_structure_set_profiles()
        self._build_item_classification_outputs()
        manifest = self._build_manifest()
        self._write_output_bundle(scope_report, manifest, precheck_report)
        return {
            "precheck_report": precheck_report,
            "scope_report": scope_report,
            "manifest": manifest,
            "output_dir": str(self.output_dir),
        }

    def _run_precheck(self) -> dict[str, Any]:
        discovered_packs: list[PackSource] = []
        duplicate_source_issues: list[str] = []
        fatal_errors: list[str] = []
        replacements: list[dict[str, Any]] = []
        ignored_sources: list[str] = []
        ignore_roots = self._normalized_ignore_roots()

        try:
            base_pack = build_pack_source(
                self.base_pack_root,
                role="base",
                explicit=False,
                discovery_source="implicit_base",
                pack_id_override="base",
            )
        except Exception as exc:
            report = {
                "scope_config_source": self.scope_settings.source,
                "pack_order_source": self.pack_order_source,
                "ignore_roots": [str(path) for path in ignore_roots],
                "ignored_sources": ignored_sources,
                "discovered_packs": [],
                "selected_packs": [],
                "effective_order": [],
                "duplicate_source_issues": [],
                "replacements": [],
                "overlap_groups": [],
                "resolved_overlaps": [],
                "fatal_errors": [f"failed to load base pack: {exc}"],
            }
            self.precheck_report = report
            return report

        discovered_packs.append(base_pack)
        mod_candidates: list[PackSource] = []

        def add_pack_candidate(path: Path, explicit: bool, discovery_source: str) -> None:
            try:
                mod_candidates.append(
                    build_pack_source(
                        path=path,
                        role="mod",
                        explicit=explicit,
                        discovery_source=discovery_source,
                    )
                )
            except Exception as exc:
                fatal_errors.append(f"failed to load pack {path}: {exc}")

        if self.auto_discover_mod_dirs and self.mods_root.exists():
            base_resolved = self.base_pack_root.resolve()
            for child in sorted(self.mods_root.iterdir(), key=lambda item: item.name.lower()):
                if not child.is_dir():
                    continue
                if child.resolve() == base_resolved:
                    continue
                if self._is_ignored_path(child, ignore_roots):
                    ignored_sources.append(str(child))
                    continue
                if not (child / "data").exists():
                    continue
                add_pack_candidate(child, explicit=False, discovery_source=f"auto_dir:{self.mods_root}")

        for archive_root in self.archive_roots:
            if not archive_root.exists():
                fatal_errors.append(f"archive root does not exist: {archive_root}")
                continue
            if self._is_ignored_path(archive_root, ignore_roots):
                ignored_sources.append(str(archive_root))
                continue
            for child in sorted(archive_root.iterdir(), key=lambda item: item.name.lower()):
                if child.is_file() and child.suffix.lower() in {".zip", ".jar"}:
                    if self._is_ignored_path(child, ignore_roots):
                        ignored_sources.append(str(child))
                        continue
                    add_pack_candidate(child, explicit=True, discovery_source=f"archive_root:{archive_root}")

        for pack_path in self.explicit_packs:
            add_pack_candidate(pack_path, explicit=True, discovery_source="explicit_pack")

        discovered_packs.extend(sorted(mod_candidates, key=lambda pack: (pack.pack_id, str(pack.root_path))))

        grouped_mod_candidates: dict[str, list[PackSource]] = defaultdict(list)
        for pack in mod_candidates:
            grouped_mod_candidates[pack.pack_id].append(pack)

        selected_packs_by_id: dict[str, PackSource] = {"base": base_pack}
        for pack_id in sorted(grouped_mod_candidates):
            candidates = grouped_mod_candidates[pack_id]
            explicit_candidates = [pack for pack in candidates if pack.explicit]
            auto_candidates = [pack for pack in candidates if not pack.explicit]
            if len(explicit_candidates) > 1:
                duplicate_source_issues.append(
                    f"pack_id {pack_id} has multiple explicit sources: "
                    + ", ".join(str(pack.root_path) for pack in explicit_candidates)
                )
                continue
            if explicit_candidates:
                selected_packs_by_id[pack_id] = explicit_candidates[0]
                for auto_pack in auto_candidates:
                    replacements.append(
                        {
                            "pack_id": pack_id,
                            "selected_source": str(explicit_candidates[0].root_path),
                            "replaced_source": str(auto_pack.root_path),
                        }
                    )
                continue
            if len(auto_candidates) > 1:
                duplicate_source_issues.append(
                    f"pack_id {pack_id} was auto-discovered from multiple directories: "
                    + ", ".join(str(pack.root_path) for pack in auto_candidates)
                )
                continue
            if auto_candidates:
                selected_packs_by_id[pack_id] = auto_candidates[0]

        if duplicate_source_issues:
            fatal_errors.extend(duplicate_source_issues)

        selected_mod_ids = sorted(pack_id for pack_id in selected_packs_by_id if pack_id != "base")
        unknown_manifest_ids = [pack_id for pack_id in self.pack_order_ids if pack_id not in selected_mod_ids]
        if unknown_manifest_ids:
            fatal_errors.append(
                "pack order manifest references unknown pack ids: " + ", ".join(unknown_manifest_ids)
            )

        if self.pack_order_ids:
            ordered_mod_ids = [pack_id for pack_id in self.pack_order_ids if pack_id in selected_mod_ids]
            ordered_mod_ids.extend(sorted(pack_id for pack_id in selected_mod_ids if pack_id not in self.pack_order_ids))
        else:
            ordered_mod_ids = sorted(selected_mod_ids)

        effective_order = ["base", *ordered_mod_ids]

        overlap_groups: list[dict[str, Any]] = []
        resolved_overlaps: list[dict[str, Any]] = []
        resource_to_mod_packs: dict[str, list[str]] = defaultdict(list)
        for pack_id in ordered_mod_ids:
            pack = selected_packs_by_id[pack_id]
            for resource_path in pack.resource_paths:
                resource_to_mod_packs[resource_path].append(pack_id)

        for resource_path in sorted(resource_to_mod_packs):
            pack_ids = resource_to_mod_packs[resource_path]
            unique_pack_ids = [pack_id for pack_id in ordered_mod_ids if pack_id in set(pack_ids)]
            if len(unique_pack_ids) <= 1:
                continue
            group = {
                "resource_path": resource_path,
                "pack_ids": unique_pack_ids,
                "source_paths": {
                    pack_id: display_pack_resource_path(selected_packs_by_id[pack_id], resource_path)
                    for pack_id in unique_pack_ids
                },
            }
            overlap_groups.append(group)
            if resource_path == GLM_REGISTRY_RESOURCE_PATH:
                resolved_overlaps.append({**group, "winner_pack_id": unique_pack_ids[-1], "merge_mode": "glm_registry"})
                continue
            if self.pack_order_ids:
                resolved_overlaps.append({**group, "winner_pack_id": unique_pack_ids[-1]})
            else:
                fatal_errors.append(
                    "mod-vs-mod same-file overlap without pack-order manifest: "
                    f"{resource_path} ({', '.join(unique_pack_ids)})"
                )

        self.discovered_packs = discovered_packs
        self.selected_packs_by_id = selected_packs_by_id
        self.ordered_packs = [selected_packs_by_id[pack_id] for pack_id in effective_order if pack_id in selected_packs_by_id]
        report = {
            "scope_config_source": self.scope_settings.source,
            "pack_order_source": self.pack_order_source,
            "ignore_roots": [str(path) for path in ignore_roots],
            "ignored_sources": ignored_sources,
            "discovered_packs": [pack.to_report_row() for pack in discovered_packs],
            "selected_packs": [
                {
                    **selected_packs_by_id[pack_id].to_report_row(),
                    "order_index": index,
                }
                for index, pack_id in enumerate(effective_order)
                if pack_id in selected_packs_by_id
            ],
            "effective_order": effective_order,
            "duplicate_source_issues": duplicate_source_issues,
            "replacements": replacements,
            "overlap_groups": overlap_groups,
            "resolved_overlaps": resolved_overlaps,
            "fatal_errors": fatal_errors,
        }
        self.precheck_report = report
        return report

    def _build_effective_resources(self) -> None:
        contributions: dict[str, list[ResourceContribution]] = defaultdict(list)
        for pack in self.ordered_packs:
            for resource_path in pack.resource_paths:
                contributions[resource_path].append(ResourceContribution(resource_path=resource_path, pack=pack))

        self.resource_contributions = dict(contributions)
        self.effective_resources = {
            resource_path: EffectiveResource(
                resource_path=resource_path,
                pack=rows[-1].pack,
                contributor_count=len(rows),
                is_override=len(rows) > 1,
            )
            for resource_path, rows in sorted(contributions.items())
        }

    def _discover_scope_report(self) -> dict[str, Any]:
        base_pack = self.selected_packs_by_id["base"]
        base_dir_counts = self._count_loot_dirs_for_resource_paths(base_pack.resource_paths)
        stack_dir_counts = self._count_loot_dirs_for_resource_paths(self.resource_contributions.keys())

        included = [
            {"name": name, "file_count": stack_dir_counts[name]}
            for name in sorted(stack_dir_counts)
            if name in self.scope_settings.allowed_loot_dirs
        ]
        deferred = [
            {"name": name, "file_count": stack_dir_counts[name]}
            for name in sorted(stack_dir_counts)
            if name in self.scope_settings.deferred_loot_dirs
        ]
        excluded = [
            {"name": name, "file_count": stack_dir_counts[name]}
            for name in sorted(stack_dir_counts)
            if name not in self.scope_settings.allowed_loot_dirs and name not in self.scope_settings.deferred_loot_dirs
        ]

        base_encountered = [{"name": name, "file_count": base_dir_counts[name]} for name in sorted(base_dir_counts)]
        stack_encountered = [{"name": name, "file_count": stack_dir_counts[name]} for name in sorted(stack_dir_counts)]

        base_dir_set = set(base_dir_counts)
        mod_dir_counts_by_pack: dict[str, Counter[str]] = {}
        for pack_id, pack in sorted(self.selected_packs_by_id.items()):
            if pack.role != "mod":
                continue
            mod_dir_counts_by_pack[pack_id] = self._count_loot_dirs_for_resource_paths(pack.resource_paths)

        new_excluded_dirs: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        all_mod_dirs = sorted({name for counts in mod_dir_counts_by_pack.values() for name in counts})
        for dir_name in all_mod_dirs:
            if dir_name in self.scope_settings.allowed_loot_dirs or dir_name in self.scope_settings.deferred_loot_dirs:
                continue
            if dir_name in base_dir_set:
                continue
            file_counts_by_pack = {
                pack_id: counts[dir_name]
                for pack_id, counts in sorted(mod_dir_counts_by_pack.items())
                if counts.get(dir_name)
            }
            if not file_counts_by_pack:
                continue
            record = {
                "name": dir_name,
                "pack_ids": sorted(file_counts_by_pack),
                "file_counts_by_pack": file_counts_by_pack,
            }
            new_excluded_dirs.append(record)
            warnings.append(
                {
                    "type": "new_excluded_loot_dir_from_mod",
                    "name": dir_name,
                    "pack_ids": record["pack_ids"],
                    "message": f"Mod-introduced excluded loot_table dir `{dir_name}` was not present in the base pack.",
                }
            )

        return {
            "scope_config_source": self.scope_settings.source,
            "allowed_loot_dirs": list(self.scope_settings.allowed_loot_dirs),
            "deferred_loot_dirs": list(self.scope_settings.deferred_loot_dirs),
            "base_source_root": str((base_pack.root_path / "data").resolve()),
            "included_dirs": included,
            "excluded_dirs": excluded,
            "deferred_dirs": deferred,
            "base_encountered_loot_dirs": base_encountered,
            "stack_encountered_loot_dirs": stack_encountered,
            "included_table_total": sum(item["file_count"] for item in included),
            "excluded_table_total": sum(item["file_count"] for item in excluded),
            "deferred_table_total": sum(item["file_count"] for item in deferred),
            "new_excluded_loot_dirs_from_mods": new_excluded_dirs,
            "warnings": warnings,
        }

    def _count_loot_dirs_for_resource_paths(self, resource_paths: Any) -> Counter[str]:
        counts: Counter[str] = Counter()
        seen: set[str] = set()
        for resource_path in resource_paths:
            metadata = get_loot_resource_metadata(resource_path)
            if metadata is None or resource_path in seen:
                continue
            seen.add(resource_path)
            counts[metadata["loot_dir"]] += 1
        return counts

    def _parse_named_tables(self) -> None:
        for resource_path in sorted(self.effective_resources):
            metadata = get_loot_resource_metadata(resource_path)
            if metadata is None:
                continue
            category = metadata["loot_dir"]
            if category not in self.scope_settings.allowed_loot_dirs:
                continue
            effective = self.effective_resources[resource_path]
            raw_table = ensure_dict(
                json.loads(read_pack_text(effective.pack, resource_path)),
                f"loot table resource {resource_path}",
            )
            table_id = f"{metadata['namespace']}:{metadata['path']}"
            table = self._register_table(
                table_id=table_id,
                table_id_kind="named",
                generated_from_entry_id="",
                namespace=metadata["namespace"],
                path=metadata["path"],
                category=category,
                table_type=self._string_or_blank(raw_table.get("type")),
                random_sequence=self._string_or_blank(raw_table.get("random_sequence")),
                source_pack=effective.pack.pack_id,
                source_file=metadata["source_file"],
                resource_path=resource_path,
                is_override=effective.is_override,
                display_source_path=effective.display_source_path(),
                raw_table=raw_table,
            )
            self.named_table_ids.append(table.table_id)
            self._parse_table_contents(table)

    def _register_table(
        self,
        *,
        table_id: str,
        table_id_kind: str,
        generated_from_entry_id: str,
        namespace: str,
        path: str,
        category: str,
        table_type: str,
        random_sequence: str,
        source_pack: str,
        source_file: str,
        resource_path: str,
        is_override: bool,
        display_source_path: str,
        raw_table: dict[str, Any],
    ) -> TableRecord:
        if table_id in self.tables:
            raise ValueError(f"duplicate table_id: {table_id}")
        table = TableRecord(
            table_id=table_id,
            table_id_kind=table_id_kind,
            generated_from_entry_id=generated_from_entry_id,
            namespace=namespace,
            path=path,
            category=category,
            table_type=table_type,
            random_sequence=random_sequence,
            source_pack=source_pack,
            source_file=source_file,
            resource_path=resource_path,
            is_override=is_override,
            display_source_path=display_source_path,
            data=raw_table,
        )
        self.tables[table_id] = table
        return table

    def _parse_table_contents(self, table: TableRecord) -> None:
        pools = ensure_list(table.data.get("pools"), f"{table.table_id}.pools")
        for pool_index, raw_pool in enumerate(pools):
            pool = ensure_dict(raw_pool, f"{table.table_id}.pools[{pool_index}]")
            pool_id = f"{table.table_id}#pool:{pool_index}"
            if pool_id in self.pools:
                raise ValueError(f"duplicate pool_id: {pool_id}")

            rolls = parse_roll_spec(pool.get("rolls"))
            bonus_rolls = parse_roll_spec(pool.get("bonus_rolls"))
            pool_conditions = ensure_list(pool.get("conditions"), f"{pool_id}.conditions")
            pool_record = PoolRecord(
                pool_id=pool_id,
                table_id=table.table_id,
                pool_index=pool_index,
                rolls_kind=rolls["kind"],
                rolls_min=rolls["min"],
                rolls_max=rolls["max"],
                rolls_raw=rolls["raw"],
                bonus_rolls_kind=bonus_rolls["kind"],
                bonus_rolls_min=bonus_rolls["min"],
                bonus_rolls_max=bonus_rolls["max"],
                bonus_rolls_raw=bonus_rolls["raw"],
                condition_types=collect_condition_types(pool_conditions),
                conditions=pool_conditions,
                raw_pool=pool,
            )
            self.pools[pool_id] = pool_record
            table.pool_ids.append(pool_id)

            entries = ensure_list(pool.get("entries"), f"{pool_id}.entries")
            for entry_index, raw_entry in enumerate(entries):
                self._parse_entry(
                    table=table,
                    pool=pool_record,
                    raw_entry=raw_entry,
                    entry_path=str(entry_index),
                )

    def _parse_entry(
        self,
        *,
        table: TableRecord,
        pool: PoolRecord,
        raw_entry: Any,
        entry_path: str,
    ) -> None:
        entry = ensure_dict(raw_entry, f"{pool.pool_id}.entry[{entry_path}]")
        entry_id = f"{pool.pool_id}#entry:{entry_path}"
        if entry_id in self.entries:
            raise ValueError(f"duplicate entry_id: {entry_id}")

        conditions = ensure_list(entry.get("conditions"), f"{entry_id}.conditions")
        functions = ensure_list(entry.get("functions"), f"{entry_id}.functions")
        entry_type = self._string_or_blank(entry.get("type"))
        name = self._string_or_blank(entry.get("name"))

        ref_table_id = ""
        inline_table_id = ""
        value_kind = "none"
        if entry_type == "minecraft:loot_table":
            value = entry.get("value")
            if isinstance(value, str):
                value_kind = "string_ref"
                ref_table_id = normalize_namespaced_id(value, table.namespace)
                table.references.append(ref_table_id)
                self.named_reference_count += 1
            elif isinstance(value, dict):
                value_kind = "inline_table"
                inline_table_id = f"inline:{entry_id}"
                table.references.append(inline_table_id)
                self.inline_reference_count += 1
            elif value is None:
                value_kind = "missing"
            else:
                value_kind = type(value).__name__

        entry_record = EntryRecord(
            entry_id=entry_id,
            pool_id=pool.pool_id,
            table_id=table.table_id,
            entry_path=entry_path,
            entry_type=entry_type,
            name=name,
            value_kind=value_kind,
            ref_table_id=ref_table_id,
            inline_table_id=inline_table_id,
            weight=entry.get("weight"),
            quality=entry.get("quality"),
            effective_weight=None,
            pool_total_effective_weight=None,
            pool_weight_share=None,
            condition_types=collect_condition_types(conditions),
            function_types=collect_function_types(functions),
            conditions=conditions,
            functions=functions,
            raw_entry=entry,
        )
        self.entries[entry_id] = entry_record
        self.entry_id_by_key[(table.table_id, pool.pool_index, entry_path)] = entry_id
        self.entry_ids_by_pool[pool.pool_id].append(entry_id)

        children = entry.get("children")
        if isinstance(children, list):
            for child_index, child_entry in enumerate(children):
                self._parse_entry(
                    table=table,
                    pool=pool,
                    raw_entry=child_entry,
                    entry_path=f"{entry_path}.{child_index}",
                )

        if inline_table_id:
            inline_value = ensure_dict(entry.get("value"), f"{entry_id}.value")
            inline_table = self._register_table(
                table_id=inline_table_id,
                table_id_kind="inline",
                generated_from_entry_id=entry_id,
                namespace=table.namespace,
                path=table.path,
                category=table.category,
                table_type=self._string_or_blank(inline_value.get("type")),
                random_sequence=self._string_or_blank(inline_value.get("random_sequence")),
                source_pack=table.source_pack,
                source_file=table.source_file,
                resource_path=table.resource_path,
                is_override=table.is_override,
                display_source_path=table.display_source_path,
                raw_table=inline_value,
            )
            self._parse_table_contents(inline_table)

    def _compute_pool_weight_metrics(self) -> None:
        for pool_id, pool in self.pools.items():
            entry_ids = self.entry_ids_by_pool.get(pool_id, [])
            effective_weights: dict[str, int | float] = {}
            total_effective_weight: int | float = 0

            for entry_id in entry_ids:
                entry = self.entries[entry_id]
                effective_weight = get_effective_weight(entry.weight)
                effective_weights[entry_id] = effective_weight
                total_effective_weight += effective_weight
                entry.effective_weight = effective_weight

            pool.pool_total_effective_weight = total_effective_weight

            for entry_id in entry_ids:
                entry = self.entries[entry_id]
                entry.pool_total_effective_weight = total_effective_weight
                effective_weight = effective_weights[entry_id]
                if total_effective_weight:
                    entry.pool_weight_share = effective_weight / total_effective_weight
                else:
                    entry.pool_weight_share = None

    def _validate_references(self) -> None:
        missing_inline_tables = sorted(
            inline_table_id
            for inline_table_id in {entry.inline_table_id for entry in self.entries.values() if entry.inline_table_id}
            if inline_table_id not in self.tables
        )
        if missing_inline_tables:
            raise ValueError("missing inline tables: " + ", ".join(missing_inline_tables))

    def _build_leaf_rows(self) -> None:
        leaf_rows: list[dict[str, Any]] = []
        for table_id in sorted(self.named_table_ids):
            root_table = self.tables[table_id]
            for pool_id in root_table.pool_ids:
                pool = self.pools[pool_id]
                for entry_id in self.entry_ids_by_pool[pool_id]:
                    entry = self.entries[entry_id]
                    self._resolve_entry(
                        leaf_rows=leaf_rows,
                        root_table=root_table,
                        root_pool=pool,
                        root_entry=entry,
                        current_pool=pool,
                        current_entry=entry,
                        chain=[],
                        path_condition_types=set(),
                        path_function_types=set(),
                        active_table_ids={root_table.table_id},
                    )
        self.leaf_rows = leaf_rows

    def _resolve_entry(
        self,
        *,
        leaf_rows: list[dict[str, Any]],
        root_table: TableRecord,
        root_pool: PoolRecord,
        root_entry: EntryRecord,
        current_pool: PoolRecord,
        current_entry: EntryRecord,
        chain: list[dict[str, Any]],
        path_condition_types: set[str],
        path_function_types: set[str],
        active_table_ids: set[str],
    ) -> None:
        chain_step = self._build_chain_step(current_pool, current_entry)
        next_chain = [*chain, chain_step]
        next_condition_types = set(path_condition_types)
        next_condition_types.update(current_pool.condition_types)
        next_condition_types.update(current_entry.condition_types)
        next_function_types = set(path_function_types)
        next_function_types.update(current_entry.function_types)

        if current_entry.entry_type == "minecraft:loot_table":
            target_table_id = current_entry.inline_table_id or current_entry.ref_table_id
            if not target_table_id:
                self._append_leaf_row(
                    leaf_rows=leaf_rows,
                    root_table=root_table,
                    root_pool=root_pool,
                    root_entry=root_entry,
                    leaf_table_id=current_entry.table_id,
                    leaf_entry=current_entry,
                    chain=next_chain,
                    path_condition_types=next_condition_types,
                    path_function_types=next_function_types,
                    unresolved_reason="missing_loot_table_target",
                )
                return
            if target_table_id in active_table_ids:
                self._append_leaf_row(
                    leaf_rows=leaf_rows,
                    root_table=root_table,
                    root_pool=root_pool,
                    root_entry=root_entry,
                    leaf_table_id=target_table_id,
                    leaf_entry=current_entry,
                    chain=next_chain,
                    path_condition_types=next_condition_types,
                    path_function_types=next_function_types,
                    unresolved_reason="cycle_detected",
                )
                return
            target_table = self.tables.get(target_table_id)
            if target_table is None:
                self._append_leaf_row(
                    leaf_rows=leaf_rows,
                    root_table=root_table,
                    root_pool=root_pool,
                    root_entry=root_entry,
                    leaf_table_id=target_table_id,
                    leaf_entry=current_entry,
                    chain=next_chain,
                    path_condition_types=next_condition_types,
                    path_function_types=next_function_types,
                    unresolved_reason="missing_ref_table",
                )
                return
            if not target_table.pool_ids:
                self._append_leaf_row(
                    leaf_rows=leaf_rows,
                    root_table=root_table,
                    root_pool=root_pool,
                    root_entry=root_entry,
                    leaf_table_id=target_table.table_id,
                    leaf_entry=current_entry,
                    chain=next_chain,
                    path_condition_types=next_condition_types,
                    path_function_types=next_function_types,
                    unresolved_reason="referenced_table_has_no_pools",
                )
                return

            next_active = set(active_table_ids)
            next_active.add(target_table_id)
            for target_pool_id in target_table.pool_ids:
                target_pool = self.pools[target_pool_id]
                for target_entry_id in self.entry_ids_by_pool[target_pool_id]:
                    self._resolve_entry(
                        leaf_rows=leaf_rows,
                        root_table=root_table,
                        root_pool=root_pool,
                        root_entry=root_entry,
                        current_pool=target_pool,
                        current_entry=self.entries[target_entry_id],
                        chain=next_chain,
                        path_condition_types=next_condition_types,
                        path_function_types=next_function_types,
                        active_table_ids=next_active,
                    )
            return

        if current_entry.entry_type in {"minecraft:item", "minecraft:empty"}:
            self._append_leaf_row(
                leaf_rows=leaf_rows,
                root_table=root_table,
                root_pool=root_pool,
                root_entry=root_entry,
                leaf_table_id=current_entry.table_id,
                leaf_entry=current_entry,
                chain=next_chain,
                path_condition_types=next_condition_types,
                path_function_types=next_function_types,
                unresolved_reason="",
            )
            return

        self._append_leaf_row(
            leaf_rows=leaf_rows,
            root_table=root_table,
            root_pool=root_pool,
            root_entry=root_entry,
            leaf_table_id=current_entry.table_id,
            leaf_entry=current_entry,
            chain=next_chain,
            path_condition_types=next_condition_types,
            path_function_types=next_function_types,
            unresolved_reason=f"unsupported_terminal_entry_type:{current_entry.entry_type or 'missing'}",
        )

    def _append_leaf_row(
        self,
        *,
        leaf_rows: list[dict[str, Any]],
        root_table: TableRecord,
        root_pool: PoolRecord,
        root_entry: EntryRecord,
        leaf_table_id: str,
        leaf_entry: EntryRecord,
        chain: list[dict[str, Any]],
        path_condition_types: set[str],
        path_function_types: set[str],
        unresolved_reason: str,
    ) -> None:
        set_count_min, set_count_max = extract_set_count_range(leaf_entry.functions)
        root_chain_step = chain[0]
        explicit_weights = [step["weight"] for step in chain if is_explicit_number(step.get("weight"))]
        path_pool_shares = [step["pool_weight_share"] for step in chain if is_explicit_number(step.get("pool_weight_share"))]
        path_weight_product: int | float | None = None
        if explicit_weights:
            product: int | float = 1
            for value in explicit_weights:
                product *= value
            path_weight_product = product
        path_pool_share_product: float | None = None
        if len(path_pool_shares) == len(chain) and path_pool_shares:
            share_product = 1.0
            for value in path_pool_shares:
                share_product *= float(value)
            path_pool_share_product = share_product
        leaf_rows.append(
            {
                "root_table_id": root_table.table_id,
                "root_category": root_table.category,
                "root_table_type": root_table.table_type,
                "root_pool_index": root_pool.pool_index,
                "root_entry_id": root_entry.entry_id,
                "leaf_table_id": leaf_table_id,
                "leaf_entry_id": leaf_entry.entry_id,
                "leaf_kind": leaf_entry.entry_type,
                "item_id": leaf_entry.name if leaf_entry.entry_type == "minecraft:item" else "",
                "chain_depth": len(chain),
                "selection_chain_json": json_cell(chain),
                "path_condition_types": join_types(sorted(path_condition_types)),
                "path_function_types": join_types(sorted(path_function_types)),
                "root_entry_weight": as_csv_value(root_chain_step.get("weight")),
                "root_entry_quality": as_csv_value(root_chain_step.get("quality")),
                "leaf_weight": as_csv_value(leaf_entry.weight),
                "leaf_quality": as_csv_value(leaf_entry.quality),
                "root_pool_weight_share": as_csv_value(root_chain_step.get("pool_weight_share")),
                "path_pool_shares_json": json_cell(path_pool_shares),
                "path_pool_share_product": as_csv_value(path_pool_share_product),
                "path_explicit_weights_json": json_cell(explicit_weights),
                "path_explicit_weight_product": as_csv_value(path_weight_product),
                "set_count_min": as_csv_value(set_count_min),
                "set_count_max": as_csv_value(set_count_max),
                "unresolved_reason": unresolved_reason,
            }
        )

    def _build_chain_step(self, pool: PoolRecord, entry: EntryRecord) -> dict[str, Any]:
        return {
            "table_id": entry.table_id,
            "pool_id": pool.pool_id,
            "pool_index": pool.pool_index,
            "pool_condition_types": pool.condition_types,
            "entry_id": entry.entry_id,
            "entry_path": entry.entry_path,
            "entry_type": entry.entry_type,
            "name": entry.name,
            "value_kind": entry.value_kind,
            "ref_table_id": entry.ref_table_id,
            "inline_table_id": entry.inline_table_id,
            "weight": entry.weight,
            "quality": entry.quality,
            "pool_weight_share": entry.pool_weight_share,
            "condition_types": entry.condition_types,
            "function_types": entry.function_types,
        }

    def _build_table_roles(self) -> None:
        named_table_set = set(self.named_table_ids)
        inbound_counts: dict[str, int] = {table_id: 0 for table_id in self.named_table_ids}
        outbound_counts: dict[str, int] = {table_id: 0 for table_id in self.named_table_ids}
        structure_counts: dict[str, int] = {table_id: 0 for table_id in self.named_table_ids}
        data_assignment_counts: dict[str, int] = {table_id: 0 for table_id in self.named_table_ids}
        evidence_sources: dict[str, set[str]] = defaultdict(set)
        evidence_rows: list[RoleEvidenceRecord] = []

        for entry in sorted(self.entries.values(), key=lambda record: record.entry_id):
            target_table_id = entry.ref_table_id
            if not target_table_id or target_table_id not in named_table_set:
                continue
            inbound_counts[target_table_id] += 1
            source_table = self.tables[entry.table_id]
            if source_table.table_id_kind == "named":
                outbound_counts[source_table.table_id] += 1
            evidence_sources[target_table_id].add(LOOT_REF_EVIDENCE_TYPE)
            evidence_rows.append(
                RoleEvidenceRecord(
                    table_id=target_table_id,
                    evidence_type=LOOT_REF_EVIDENCE_TYPE,
                    source_path=source_table.display_source_path,
                    source_object=entry.entry_id,
                    target_table_id=target_table_id,
                )
            )

        for record in self._scan_structure_evidence():
            evidence_rows.append(record)
            structure_counts[record.table_id] += 1
            evidence_sources[record.table_id].add(record.evidence_type)

        for record in self._scan_direct_assignment_evidence():
            evidence_rows.append(record)
            data_assignment_counts[record.table_id] += 1
            evidence_sources[record.table_id].add(record.evidence_type)

        summary_rows: list[dict[str, Any]] = []
        raw_role_counts: Counter[str] = Counter()
        effective_role_counts: Counter[str] = Counter()

        for table_id in sorted(self.named_table_ids):
            table = self.tables[table_id]
            inbound = inbound_counts[table_id]
            outbound = outbound_counts[table_id]
            structure_refs = structure_counts[table_id]
            data_assignment_refs = data_assignment_counts[table_id]
            direct_evidence_count = structure_refs + data_assignment_refs

            if direct_evidence_count and inbound:
                raw_role = "both_direct_and_helper"
            elif direct_evidence_count:
                raw_role = "direct_from_data"
            elif inbound:
                raw_role = "helper_from_data"
            else:
                raw_role = "unknown_directness"

            effective_role = "assumed_direct_for_tableau" if raw_role == "unknown_directness" else raw_role
            count_as_direct = raw_role != "helper_from_data"

            raw_role_counts[raw_role] += 1
            effective_role_counts[effective_role] += 1

            summary_rows.append(
                {
                    "table_id": table_id,
                    "category": table.category,
                    "inbound_loot_ref_count": inbound,
                    "outbound_loot_ref_count": outbound,
                    "structure_ref_count": structure_refs,
                    "data_assignment_ref_count": data_assignment_refs,
                    "raw_role": raw_role,
                    "effective_role": effective_role,
                    "count_as_direct": "true" if count_as_direct else "false",
                    "evidence_sources": join_types(sorted(evidence_sources[table_id])),
                    "notes": self._build_role_note(raw_role),
                }
            )

        self.table_role_summary_rows = summary_rows
        self.table_role_evidence_rows = [
            record.to_row()
            for record in sorted(
                evidence_rows,
                key=lambda record: (
                    record.table_id,
                    record.evidence_type,
                    record.source_path,
                    record.source_object,
                    record.target_table_id,
                ),
            )
        ]
        self.raw_role_counts = raw_role_counts
        self.effective_role_counts = effective_role_counts

    def _build_stage2_outputs(self) -> None:
        warnings: list[str] = []
        merged_modifier_ids = self._merge_glm_registry_entries(warnings)
        named_table_set = set(self.named_table_ids)
        base_item_ids_by_target: dict[str, set[str]] = defaultdict(set)
        for row in self.leaf_rows:
            if row["item_id"]:
                base_item_ids_by_target[row["root_table_id"]].add(row["item_id"])

        recognized_statuses = {"recognized_inject_semantics", "recognized_inject_target_out_of_scope"}
        chain_rows: list[dict[str, Any]] = []
        added_rows: list[dict[str, Any]] = []
        target_summary_state: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "modifier_count": 0,
                "supported_modifier_count": 0,
                "unsupported_modifier_count": 0,
                "added_leaf_row_count": 0,
                "added_item_ids": set(),
                "novel_item_ids": set(),
                "overlap_item_ids": set(),
                "modifier_pack_ids": set(),
                "modifier_ids": set(),
            }
        )
        target_item_state: dict[tuple[str, str], dict[str, Any]] = {}

        for glm_index, modifier_id in enumerate(merged_modifier_ids):
            chain_row, modifier_leaf_rows = self._analyze_glm_modifier(glm_index, modifier_id, named_table_set, warnings)
            chain_rows.append(chain_row)

            target_table_id = chain_row["target_table_id"]
            if target_table_id:
                summary = target_summary_state[target_table_id]
                summary["modifier_count"] += 1
                if chain_row["analysis_status"] in recognized_statuses:
                    summary["supported_modifier_count"] += 1
                else:
                    summary["unsupported_modifier_count"] += 1
                if chain_row["modifier_pack_id"]:
                    summary["modifier_pack_ids"].add(chain_row["modifier_pack_id"])
                if chain_row["modifier_id"]:
                    summary["modifier_ids"].add(chain_row["modifier_id"])

            for added_row in modifier_leaf_rows:
                added_rows.append(added_row)
                item_id = added_row["item_id"]
                target_table_id = added_row["target_table_id"]
                if not target_table_id:
                    continue
                summary = target_summary_state[target_table_id]
                summary["added_leaf_row_count"] += 1
                if item_id:
                    summary["added_item_ids"].add(item_id)
                    if item_id in base_item_ids_by_target.get(target_table_id, set()):
                        summary["overlap_item_ids"].add(item_id)
                    else:
                        summary["novel_item_ids"].add(item_id)

                    key = (target_table_id, item_id)
                    item_summary = target_item_state.setdefault(
                        key,
                        {
                            "modifier_ids": set(),
                            "added_path_count": 0,
                            "added_explicit_weight_sum": 0.0,
                            "has_explicit_weight_sum": False,
                            "is_novel_to_target": item_id not in base_item_ids_by_target.get(target_table_id, set()),
                        },
                    )
                    item_summary["added_path_count"] += 1
                    item_summary["modifier_ids"].add(added_row["modifier_id"])
                    explicit_weight_value = added_row["path_explicit_weight_product"]
                    if explicit_weight_value != "":
                        item_summary["added_explicit_weight_sum"] += float(explicit_weight_value)
                        item_summary["has_explicit_weight_sum"] = True

        self.glm_modifier_chain_rows = chain_rows
        self.modifier_added_leaf_rows = added_rows
        self.target_table_modifier_summary_rows = [
            {
                "target_table_id": target_table_id,
                "modifier_count": state["modifier_count"],
                "supported_modifier_count": state["supported_modifier_count"],
                "unsupported_modifier_count": state["unsupported_modifier_count"],
                "added_leaf_row_count": state["added_leaf_row_count"],
                "added_unique_item_count": len(state["added_item_ids"]),
                "novel_item_count": len(state["novel_item_ids"]),
                "overlap_item_count": len(state["overlap_item_ids"]),
                "modifier_pack_ids": join_types(sorted(state["modifier_pack_ids"])),
                "modifier_ids_json": json_cell(sorted(state["modifier_ids"])),
            }
            for target_table_id, state in sorted(target_summary_state.items())
        ]
        self.target_table_added_item_summary_rows = [
            {
                "target_table_id": target_table_id,
                "item_id": item_id,
                "modifier_count": len(state["modifier_ids"]),
                "added_path_count": state["added_path_count"],
                "added_explicit_weight_sum": (
                    as_csv_value(state["added_explicit_weight_sum"])
                    if state["has_explicit_weight_sum"]
                    else ""
                ),
                "is_novel_to_target": "true" if state["is_novel_to_target"] else "false",
                "modifier_ids_json": json_cell(sorted(state["modifier_ids"])),
            }
            for (target_table_id, item_id), state in sorted(target_item_state.items())
        ]
        self.stage2_report = {
            "glm_chain_length": len(chain_rows),
            "recognized_modifier_count": sum(
                1 for row in chain_rows if row["analysis_status"] in recognized_statuses
            ),
            "unsupported_modifier_count": sum(
                1 for row in chain_rows if row["analysis_status"] not in recognized_statuses
            ),
            "analyzed_target_count": len(
                {
                    row["target_table_id"]
                    for row in chain_rows
                    if row["analysis_status"] == "recognized_inject_semantics" and row["target_table_id"]
                }
            ),
            "out_of_scope_target_count": len(
                {
                    row["target_table_id"]
                    for row in chain_rows
                    if row["analysis_status"] == "recognized_inject_target_out_of_scope" and row["target_table_id"]
                }
            ),
            "warnings": warnings,
        }

    def _merge_glm_registry_entries(self, warnings: list[str]) -> list[str]:
        merged_entries: list[str] = []
        for contribution in self.resource_contributions.get(GLM_REGISTRY_RESOURCE_PATH, []):
            try:
                raw_registry = ensure_dict(
                    json.loads(read_pack_text(contribution.pack, GLM_REGISTRY_RESOURCE_PATH)),
                    f"{contribution.pack.pack_id}:{GLM_REGISTRY_RESOURCE_PATH}",
                )
            except Exception as exc:
                warnings.append(
                    f"failed to parse {display_pack_resource_path(contribution.pack, GLM_REGISTRY_RESOURCE_PATH)}: {exc}"
                )
                continue
            if parse_boolish(raw_registry.get("replace")):
                merged_entries = []
            for entry_index, raw_entry in enumerate(
                ensure_list(raw_registry.get("entries"), f"{contribution.pack.pack_id}:{GLM_REGISTRY_RESOURCE_PATH}.entries")
            ):
                if not isinstance(raw_entry, str) or not raw_entry.strip():
                    warnings.append(
                        f"ignored non-string GLM registry entry at {display_pack_resource_path(contribution.pack, GLM_REGISTRY_RESOURCE_PATH)}[{entry_index}]"
                    )
                    continue
                merged_entries.append(normalize_namespaced_id(raw_entry.strip(), contribution.pack.pack_id))
        return merged_entries

    def _find_loot_table_id_conditions(self, node: Any) -> list[str]:
        matches: list[str] = []
        if isinstance(node, dict):
            condition_id = node.get("condition")
            table_id = node.get("loot_table_id")
            if condition_id == "neoforge:loot_table_id" and isinstance(table_id, str) and table_id.strip():
                matches.append(table_id.strip())
            for value in node.values():
                matches.extend(self._find_loot_table_id_conditions(value))
        elif isinstance(node, list):
            for value in node:
                matches.extend(self._find_loot_table_id_conditions(value))
        return matches

    def _extract_payload_table_id(self, modifier_type: str, raw_modifier: dict[str, Any], default_namespace: str) -> str:
        if modifier_type == "neoforge:add_table":
            value = raw_modifier.get("table")
        elif modifier_type == "sophisticatedbackpacks:inject_loot":
            value = raw_modifier.get("loot_table")
        else:
            return ""
        if isinstance(value, str) and value.strip():
            return normalize_namespaced_id(value.strip(), default_namespace)
        return ""

    def _analyze_glm_modifier(
        self,
        glm_index: int,
        modifier_id: str,
        named_table_set: set[str],
        warnings: list[str],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        modifier_resource_path = loot_table_id_to_resource_path(modifier_id).replace("/loot_table/", "/loot_modifiers/")
        effective = self.effective_resources.get(modifier_resource_path)
        modifier_namespace, _ = split_loot_table_id(modifier_id)
        row = {
            "glm_index": glm_index,
            "modifier_id": modifier_id,
            "modifier_type": "",
            "modifier_pack_id": "",
            "target_table_id": "",
            "payload_table_id": "",
            "target_in_stage1_scope": "false",
            "analysis_status": "missing_modifier_json",
            "modifier_source_path": "",
        }
        if effective is None:
            return row, []

        raw_modifier = ensure_dict(
            json.loads(read_pack_text(effective.pack, modifier_resource_path)),
            f"modifier resource {modifier_resource_path}",
        )
        modifier_type = self._string_or_blank(raw_modifier.get("type"))
        target_table_ids = sorted(
            {
                normalize_namespaced_id(table_id, modifier_namespace)
                for table_id in self._find_loot_table_id_conditions(raw_modifier.get("conditions"))
            }
        )
        direct_target_value = raw_modifier.get("loot_table_to_inject_into")
        if isinstance(direct_target_value, str) and direct_target_value.strip():
            direct_target_id = normalize_namespaced_id(direct_target_value.strip(), modifier_namespace)
            if not target_table_ids:
                target_table_ids = [direct_target_id]
            elif direct_target_id not in target_table_ids:
                warnings.append(
                    f"{modifier_id} declares mismatched target ids between conditions and loot_table_to_inject_into"
                )

        target_table_id = target_table_ids[0] if len(target_table_ids) == 1 else ""
        payload_table_id = self._extract_payload_table_id(modifier_type, raw_modifier, modifier_namespace)
        target_in_scope = target_table_id in named_table_set if target_table_id else False

        row.update(
            {
                "modifier_type": modifier_type,
                "modifier_pack_id": effective.pack.pack_id,
                "target_table_id": target_table_id,
                "payload_table_id": payload_table_id,
                "target_in_stage1_scope": "true" if target_in_scope else "false",
                "modifier_source_path": effective.display_source_path(),
            }
        )

        recognized_type = modifier_type in {"neoforge:add_table", "sophisticatedbackpacks:inject_loot"}
        if not recognized_type:
            row["analysis_status"] = "unsupported_modifier_type"
            return row, []
        if not target_table_ids:
            row["analysis_status"] = "missing_target_table"
            return row, []
        if len(target_table_ids) > 1:
            row["analysis_status"] = "multiple_target_tables"
            return row, []
        if not payload_table_id:
            row["analysis_status"] = "missing_payload_table_id"
            return row, []
        if not target_in_scope:
            row["analysis_status"] = "recognized_inject_target_out_of_scope"
            return row, []

        payload_leaf_rows = self._get_stage2_payload_leaf_rows(payload_table_id, warnings)
        if payload_leaf_rows is None:
            row["analysis_status"] = "missing_payload_table"
            return row, []

        row["analysis_status"] = "recognized_inject_semantics"
        added_rows = [
            {
                "glm_index": glm_index,
                "modifier_id": modifier_id,
                "modifier_type": modifier_type,
                "modifier_pack_id": effective.pack.pack_id,
                "target_table_id": target_table_id,
                "payload_table_id": payload_table_id,
                "payload_root_pool_index": payload_row["root_pool_index"],
                "payload_root_entry_id": payload_row["root_entry_id"],
                "leaf_table_id": payload_row["leaf_table_id"],
                "leaf_entry_id": payload_row["leaf_entry_id"],
                "leaf_kind": payload_row["leaf_kind"],
                "item_id": payload_row["item_id"],
                "chain_depth": payload_row["chain_depth"],
                "selection_chain_json": payload_row["selection_chain_json"],
                "path_condition_types": payload_row["path_condition_types"],
                "path_function_types": payload_row["path_function_types"],
                "root_entry_weight": payload_row["root_entry_weight"],
                "root_entry_quality": payload_row["root_entry_quality"],
                "leaf_weight": payload_row["leaf_weight"],
                "leaf_quality": payload_row["leaf_quality"],
                "root_pool_weight_share": payload_row["root_pool_weight_share"],
                "path_pool_shares_json": payload_row["path_pool_shares_json"],
                "path_pool_share_product": payload_row["path_pool_share_product"],
                "path_explicit_weights_json": payload_row["path_explicit_weights_json"],
                "path_explicit_weight_product": payload_row["path_explicit_weight_product"],
                "set_count_min": payload_row["set_count_min"],
                "set_count_max": payload_row["set_count_max"],
                "unresolved_reason": payload_row["unresolved_reason"],
                "analysis_status": row["analysis_status"],
            }
            for payload_row in payload_leaf_rows
        ]
        return row, added_rows

    def _get_stage2_payload_leaf_rows(self, table_id: str, warnings: list[str]) -> list[dict[str, Any]] | None:
        if table_id in self.stage2_payload_leaf_cache:
            return self.stage2_payload_leaf_cache[table_id]
        if table_id in self.named_table_ids:
            rows = [dict(row) for row in self.leaf_rows if row["root_table_id"] == table_id]
            self.stage2_payload_leaf_cache[table_id] = rows
            return rows

        root_resource_path = loot_table_id_to_resource_path(table_id)
        if root_resource_path not in self.effective_resources:
            warnings.append(f"missing payload loot table resource for {table_id}")
            return None

        aux_tables: dict[str, TableRecord] = {}
        aux_pools: dict[str, PoolRecord] = {}
        aux_entries: dict[str, EntryRecord] = {}
        aux_entry_ids_by_pool: dict[str, list[str]] = defaultdict(list)
        loading_table_ids: set[str] = set()

        def register_table(
            *,
            table_id: str,
            table_id_kind: str,
            generated_from_entry_id: str,
            namespace: str,
            path: str,
            category: str,
            table_type: str,
            random_sequence: str,
            source_pack: str,
            source_file: str,
            resource_path: str,
            is_override: bool,
            display_source_path: str,
            raw_table: dict[str, Any],
        ) -> TableRecord:
            table = TableRecord(
                table_id=table_id,
                table_id_kind=table_id_kind,
                generated_from_entry_id=generated_from_entry_id,
                namespace=namespace,
                path=path,
                category=category,
                table_type=table_type,
                random_sequence=random_sequence,
                source_pack=source_pack,
                source_file=source_file,
                resource_path=resource_path,
                is_override=is_override,
                display_source_path=display_source_path,
                data=raw_table,
            )
            aux_tables[table_id] = table
            return table

        def parse_entry(table: TableRecord, pool: PoolRecord, raw_entry: Any, entry_path: str) -> None:
            entry = ensure_dict(raw_entry, f"{pool.pool_id}.entry[{entry_path}]")
            entry_id = f"{pool.pool_id}#entry:{entry_path}"
            conditions = ensure_list(entry.get("conditions"), f"{entry_id}.conditions")
            functions = ensure_list(entry.get("functions"), f"{entry_id}.functions")
            entry_type = self._string_or_blank(entry.get("type"))
            name = self._string_or_blank(entry.get("name"))

            ref_table_id = ""
            inline_table_id = ""
            value_kind = "none"
            if entry_type == "minecraft:loot_table":
                value = entry.get("value")
                if isinstance(value, str):
                    value_kind = "string_ref"
                    ref_table_id = normalize_namespaced_id(value, table.namespace)
                    table.references.append(ref_table_id)
                elif isinstance(value, dict):
                    value_kind = "inline_table"
                    inline_table_id = f"inline:{entry_id}"
                    table.references.append(inline_table_id)
                elif value is None:
                    value_kind = "missing"
                else:
                    value_kind = type(value).__name__

            entry_record = EntryRecord(
                entry_id=entry_id,
                pool_id=pool.pool_id,
                table_id=table.table_id,
                entry_path=entry_path,
                entry_type=entry_type,
                name=name,
                value_kind=value_kind,
                ref_table_id=ref_table_id,
                inline_table_id=inline_table_id,
                weight=entry.get("weight"),
                quality=entry.get("quality"),
                effective_weight=None,
                pool_total_effective_weight=None,
                pool_weight_share=None,
                condition_types=collect_condition_types(conditions),
                function_types=collect_function_types(functions),
                conditions=conditions,
                functions=functions,
                raw_entry=entry,
            )
            aux_entries[entry_id] = entry_record
            aux_entry_ids_by_pool[pool.pool_id].append(entry_id)

            children = entry.get("children")
            if isinstance(children, list):
                for child_index, child_entry in enumerate(children):
                    parse_entry(table, pool, child_entry, f"{entry_path}.{child_index}")

            if inline_table_id:
                inline_value = ensure_dict(entry.get("value"), f"{entry_id}.value")
                inline_table = register_table(
                    table_id=inline_table_id,
                    table_id_kind="inline",
                    generated_from_entry_id=entry_id,
                    namespace=table.namespace,
                    path=table.path,
                    category=table.category,
                    table_type=self._string_or_blank(inline_value.get("type")),
                    random_sequence=self._string_or_blank(inline_value.get("random_sequence")),
                    source_pack=table.source_pack,
                    source_file=table.source_file,
                    resource_path=table.resource_path,
                    is_override=table.is_override,
                    display_source_path=table.display_source_path,
                    raw_table=inline_value,
                )
                parse_table_contents(inline_table)
                for referenced_table_id in sorted(
                    ref_id for ref_id in inline_table.references if ref_id and not ref_id.startswith("inline:")
                ):
                    parse_named_table(referenced_table_id)

        def parse_table_contents(table: TableRecord) -> None:
            pools = ensure_list(table.data.get("pools"), f"{table.table_id}.pools")
            for pool_index, raw_pool in enumerate(pools):
                pool = ensure_dict(raw_pool, f"{table.table_id}.pools[{pool_index}]")
                pool_id = f"{table.table_id}#pool:{pool_index}"
                rolls = parse_roll_spec(pool.get("rolls"))
                bonus_rolls = parse_roll_spec(pool.get("bonus_rolls"))
                pool_conditions = ensure_list(pool.get("conditions"), f"{pool_id}.conditions")
                pool_record = PoolRecord(
                    pool_id=pool_id,
                    table_id=table.table_id,
                    pool_index=pool_index,
                    rolls_kind=rolls["kind"],
                    rolls_min=rolls["min"],
                    rolls_max=rolls["max"],
                    rolls_raw=rolls["raw"],
                    bonus_rolls_kind=bonus_rolls["kind"],
                    bonus_rolls_min=bonus_rolls["min"],
                    bonus_rolls_max=bonus_rolls["max"],
                    bonus_rolls_raw=bonus_rolls["raw"],
                    condition_types=collect_condition_types(pool_conditions),
                    conditions=pool_conditions,
                    raw_pool=pool,
                )
                aux_pools[pool_id] = pool_record
                table.pool_ids.append(pool_id)
                entries = ensure_list(pool.get("entries"), f"{pool_id}.entries")
                for entry_index, raw_entry in enumerate(entries):
                    parse_entry(table, pool_record, raw_entry, str(entry_index))

        def parse_named_table(table_id_to_parse: str) -> TableRecord | None:
            if table_id_to_parse in aux_tables or table_id_to_parse in loading_table_ids:
                return aux_tables.get(table_id_to_parse)
            resource_path = loot_table_id_to_resource_path(table_id_to_parse)
            effective = self.effective_resources.get(resource_path)
            if effective is None:
                return None
            loading_table_ids.add(table_id_to_parse)
            raw_table = ensure_dict(
                json.loads(read_pack_text(effective.pack, resource_path)),
                f"payload loot table {resource_path}",
            )
            namespace, path = split_loot_table_id(table_id_to_parse)
            source_file = PurePosixPath("loot_table", *PurePosixPath(path).parts).with_suffix(".json").as_posix()
            category = PurePosixPath(path).parts[0] if PurePosixPath(path).parts else ""
            table = register_table(
                table_id=table_id_to_parse,
                table_id_kind="named",
                generated_from_entry_id="",
                namespace=namespace,
                path=path,
                category=category,
                table_type=self._string_or_blank(raw_table.get("type")),
                random_sequence=self._string_or_blank(raw_table.get("random_sequence")),
                source_pack=effective.pack.pack_id,
                source_file=source_file,
                resource_path=resource_path,
                is_override=effective.is_override,
                display_source_path=effective.display_source_path(),
                raw_table=raw_table,
            )
            parse_table_contents(table)
            loading_table_ids.remove(table_id_to_parse)
            for referenced_table_id in sorted(
                ref_id for ref_id in table.references if ref_id and not ref_id.startswith("inline:")
            ):
                parse_named_table(referenced_table_id)
            return table

        root_table = parse_named_table(table_id)
        if root_table is None:
            warnings.append(f"missing payload table resource for {table_id}")
            return None

        for pool_id, pool in aux_pools.items():
            entry_ids = aux_entry_ids_by_pool.get(pool_id, [])
            total_effective_weight: int | float = 0
            effective_weights: dict[str, int | float] = {}
            for entry_id in entry_ids:
                entry = aux_entries[entry_id]
                effective_weight = get_effective_weight(entry.weight)
                effective_weights[entry_id] = effective_weight
                total_effective_weight += effective_weight
                entry.effective_weight = effective_weight
            pool.pool_total_effective_weight = total_effective_weight
            for entry_id in entry_ids:
                entry = aux_entries[entry_id]
                entry.pool_total_effective_weight = total_effective_weight
                effective_weight = effective_weights[entry_id]
                entry.pool_weight_share = effective_weight / total_effective_weight if total_effective_weight else None

        payload_leaf_rows: list[dict[str, Any]] = []

        def build_chain_step(pool: PoolRecord, entry: EntryRecord) -> dict[str, Any]:
            return {
                "table_id": entry.table_id,
                "pool_id": pool.pool_id,
                "pool_index": pool.pool_index,
                "pool_condition_types": pool.condition_types,
                "entry_id": entry.entry_id,
                "entry_path": entry.entry_path,
                "entry_type": entry.entry_type,
                "name": entry.name,
                "value_kind": entry.value_kind,
                "ref_table_id": entry.ref_table_id,
                "inline_table_id": entry.inline_table_id,
                "weight": entry.weight,
                "quality": entry.quality,
                "pool_weight_share": entry.pool_weight_share,
                "condition_types": entry.condition_types,
                "function_types": entry.function_types,
            }

        def append_leaf_row(
            *,
            root_table_record: TableRecord,
            root_pool: PoolRecord,
            root_entry: EntryRecord,
            leaf_table_id: str,
            leaf_entry: EntryRecord,
            chain: list[dict[str, Any]],
            path_condition_types: set[str],
            path_function_types: set[str],
            unresolved_reason: str,
        ) -> None:
            set_count_min, set_count_max = extract_set_count_range(leaf_entry.functions)
            root_chain_step = chain[0]
            explicit_weights = [step["weight"] for step in chain if is_explicit_number(step.get("weight"))]
            path_pool_shares = [step["pool_weight_share"] for step in chain if is_explicit_number(step.get("pool_weight_share"))]
            path_weight_product: int | float | None = None
            if explicit_weights:
                product: int | float = 1
                for value in explicit_weights:
                    product *= value
                path_weight_product = product
            path_pool_share_product: float | None = None
            if len(path_pool_shares) == len(chain) and path_pool_shares:
                share_product = 1.0
                for value in path_pool_shares:
                    share_product *= float(value)
                path_pool_share_product = share_product
            payload_leaf_rows.append(
                {
                    "root_table_id": root_table_record.table_id,
                    "root_category": root_table_record.category,
                    "root_table_type": root_table_record.table_type,
                    "root_pool_index": root_pool.pool_index,
                    "root_entry_id": root_entry.entry_id,
                    "leaf_table_id": leaf_table_id,
                    "leaf_entry_id": leaf_entry.entry_id,
                    "leaf_kind": leaf_entry.entry_type,
                    "item_id": leaf_entry.name if leaf_entry.entry_type == "minecraft:item" else "",
                    "chain_depth": len(chain),
                    "selection_chain_json": json_cell(chain),
                    "path_condition_types": join_types(sorted(path_condition_types)),
                    "path_function_types": join_types(sorted(path_function_types)),
                    "root_entry_weight": as_csv_value(root_chain_step.get("weight")),
                    "root_entry_quality": as_csv_value(root_chain_step.get("quality")),
                    "leaf_weight": as_csv_value(leaf_entry.weight),
                    "leaf_quality": as_csv_value(leaf_entry.quality),
                    "root_pool_weight_share": as_csv_value(root_chain_step.get("pool_weight_share")),
                    "path_pool_shares_json": json_cell(path_pool_shares),
                    "path_pool_share_product": as_csv_value(path_pool_share_product),
                    "path_explicit_weights_json": json_cell(explicit_weights),
                    "path_explicit_weight_product": as_csv_value(path_weight_product),
                    "set_count_min": as_csv_value(set_count_min),
                    "set_count_max": as_csv_value(set_count_max),
                    "unresolved_reason": unresolved_reason,
                }
            )

        def resolve_entry(
            *,
            root_table_record: TableRecord,
            root_pool: PoolRecord,
            root_entry: EntryRecord,
            current_pool: PoolRecord,
            current_entry: EntryRecord,
            chain: list[dict[str, Any]],
            path_condition_types: set[str],
            path_function_types: set[str],
            active_table_ids: set[str],
        ) -> None:
            chain_step = build_chain_step(current_pool, current_entry)
            next_chain = [*chain, chain_step]
            next_condition_types = set(path_condition_types)
            next_condition_types.update(current_pool.condition_types)
            next_condition_types.update(current_entry.condition_types)
            next_function_types = set(path_function_types)
            next_function_types.update(current_entry.function_types)

            if current_entry.entry_type == "minecraft:loot_table":
                target_table_id = current_entry.inline_table_id or current_entry.ref_table_id
                if not target_table_id:
                    append_leaf_row(
                        root_table_record=root_table_record,
                        root_pool=root_pool,
                        root_entry=root_entry,
                        leaf_table_id=current_entry.table_id,
                        leaf_entry=current_entry,
                        chain=next_chain,
                        path_condition_types=next_condition_types,
                        path_function_types=next_function_types,
                        unresolved_reason="missing_loot_table_target",
                    )
                    return
                if target_table_id in active_table_ids:
                    append_leaf_row(
                        root_table_record=root_table_record,
                        root_pool=root_pool,
                        root_entry=root_entry,
                        leaf_table_id=target_table_id,
                        leaf_entry=current_entry,
                        chain=next_chain,
                        path_condition_types=next_condition_types,
                        path_function_types=next_function_types,
                        unresolved_reason="cycle_detected",
                    )
                    return
                target_table = aux_tables.get(target_table_id)
                if target_table is None:
                    append_leaf_row(
                        root_table_record=root_table_record,
                        root_pool=root_pool,
                        root_entry=root_entry,
                        leaf_table_id=target_table_id,
                        leaf_entry=current_entry,
                        chain=next_chain,
                        path_condition_types=next_condition_types,
                        path_function_types=next_function_types,
                        unresolved_reason="missing_ref_table",
                    )
                    return
                if not target_table.pool_ids:
                    append_leaf_row(
                        root_table_record=root_table_record,
                        root_pool=root_pool,
                        root_entry=root_entry,
                        leaf_table_id=target_table.table_id,
                        leaf_entry=current_entry,
                        chain=next_chain,
                        path_condition_types=next_condition_types,
                        path_function_types=next_function_types,
                        unresolved_reason="referenced_table_has_no_pools",
                    )
                    return
                next_active = set(active_table_ids)
                next_active.add(target_table_id)
                for target_pool_id in target_table.pool_ids:
                    target_pool = aux_pools[target_pool_id]
                    for target_entry_id in aux_entry_ids_by_pool[target_pool_id]:
                        resolve_entry(
                            root_table_record=root_table_record,
                            root_pool=root_pool,
                            root_entry=root_entry,
                            current_pool=target_pool,
                            current_entry=aux_entries[target_entry_id],
                            chain=next_chain,
                            path_condition_types=next_condition_types,
                            path_function_types=next_function_types,
                            active_table_ids=next_active,
                        )
                return

            if current_entry.entry_type in {"minecraft:item", "minecraft:empty"}:
                append_leaf_row(
                    root_table_record=root_table_record,
                    root_pool=root_pool,
                    root_entry=root_entry,
                    leaf_table_id=current_entry.table_id,
                    leaf_entry=current_entry,
                    chain=next_chain,
                    path_condition_types=next_condition_types,
                    path_function_types=next_function_types,
                    unresolved_reason="",
                )
                return

            append_leaf_row(
                root_table_record=root_table_record,
                root_pool=root_pool,
                root_entry=root_entry,
                leaf_table_id=current_entry.table_id,
                leaf_entry=current_entry,
                chain=next_chain,
                path_condition_types=next_condition_types,
                path_function_types=next_function_types,
                unresolved_reason=f"unsupported_terminal_entry_type:{current_entry.entry_type or 'missing'}",
            )

        for pool_id in root_table.pool_ids:
            pool = aux_pools[pool_id]
            for entry_id in aux_entry_ids_by_pool[pool_id]:
                entry = aux_entries[entry_id]
                resolve_entry(
                    root_table_record=root_table,
                    root_pool=pool,
                    root_entry=entry,
                    current_pool=pool,
                    current_entry=entry,
                    chain=[],
                    path_condition_types=set(),
                    path_function_types=set(),
                    active_table_ids={root_table.table_id},
                )

        self.stage2_payload_leaf_cache[table_id] = payload_leaf_rows
        return payload_leaf_rows

    def _build_structure_set_profiles(self) -> None:
        all_loot_table_ids = self._collect_effective_resource_ids("loot_table", ".json")
        all_template_pool_ids = self._collect_effective_resource_ids("worldgen/template_pool", ".json")
        stage1_table_ids = set(self.named_table_ids)
        base_items_by_table: dict[str, set[str]] = defaultdict(set)
        for row in self.leaf_rows:
            if row["item_id"]:
                base_items_by_table[row["root_table_id"]].add(row["item_id"])

        modifier_items_by_target: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for row in self.modifier_added_leaf_rows:
            if row["item_id"] and row["target_table_id"] and row["modifier_id"]:
                modifier_items_by_target[row["target_table_id"]][row["item_id"]].add(row["modifier_id"])

        structure_entry_rows: list[dict[str, Any]] = []
        structure_entry_lookup: dict[tuple[str, str], dict[str, Any]] = {}
        detected_links_by_pair: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
        base_presence_state: dict[tuple[str, str, str], dict[str, Any]] = {}
        effective_presence_state: dict[tuple[str, str, str], dict[str, Any]] = {}
        profile_state: dict[tuple[str, str], dict[str, Any]] = {}

        for resource_path in sorted(self.effective_resources):
            if get_resource_family(resource_path) != "worldgen/structure_set" or not resource_path.endswith(".json"):
                continue
            effective_set = self.effective_resources[resource_path]
            structure_set_id = resource_path_to_resource_id(resource_path, "worldgen/structure_set", ".json")
            if structure_set_id is None:
                continue
            raw_set = ensure_dict(
                json.loads(read_pack_text(effective_set.pack, resource_path)),
                effective_set.display_source_path(),
            )
            default_namespace = structure_set_id.split(":", 1)[0]
            for raw_entry in ensure_list(raw_set.get("structures"), f"{structure_set_id}.structures"):
                if not isinstance(raw_entry, dict):
                    continue
                structure_value = raw_entry.get("structure")
                if not isinstance(structure_value, str) or not structure_value.strip():
                    continue
                structure_id = normalize_namespaced_id(structure_value.strip(), default_namespace)
                structure_resource_path = structure_id_to_resource_path(structure_id)
                structure_effective = self.effective_resources.get(structure_resource_path)
                structure_type = ""
                structure_source_path = ""
                if structure_effective is not None:
                    structure_source_path = structure_effective.display_source_path()
                    try:
                        raw_structure = ensure_dict(
                            json.loads(read_pack_text(structure_effective.pack, structure_resource_path)),
                            structure_source_path,
                        )
                        structure_type = self._string_or_blank(raw_structure.get("type"))
                    except Exception:
                        structure_type = ""

                dynamic_status, detected_links = self._detect_structure_links_for_entry(
                    structure_id=structure_id,
                    all_loot_table_ids=all_loot_table_ids,
                    all_template_pool_ids=all_template_pool_ids,
                )
                pair_key = (structure_set_id, structure_id)
                detected_links_by_pair[pair_key] = detected_links

                profile_state[pair_key] = {
                    "base_loot_table_ids": set(),
                    "manual_active_link_count": 0,
                    "detected_active_link_count": 0,
                    "out_of_scope_loot_table_count": 0,
                    "base_items": set(),
                    "effective_items": set(),
                    "stage2_added_items": set(),
                }

                structure_entry_rows.append(
                    {
                        "structure_set_id": structure_set_id,
                        "structure_id": structure_id,
                        "structure_weight_in_set": as_csv_value(raw_entry.get("weight")),
                        "structure_type": structure_type,
                        "structure_set_pack_id": effective_set.pack.pack_id,
                        "structure_pack_id": structure_effective.pack.pack_id if structure_effective is not None else "",
                        "structure_set_source_path": effective_set.display_source_path(),
                        "structure_source_path": structure_source_path,
                        "dynamic_mapping_status": dynamic_status,
                    }
                )
                structure_entry_lookup[pair_key] = structure_entry_rows[-1]

        exact_link_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
        audit_rows: list[dict[str, Any]] = []
        for (structure_set_id, structure_id), detected_links in sorted(detected_links_by_pair.items()):
            for loot_table_id, detected in sorted(detected_links.items()):
                key = (structure_set_id, structure_id, loot_table_id)
                exact_link_rows[key] = {
                    "structure_set_id": structure_set_id,
                    "structure_id": structure_id,
                    "loot_table_id": loot_table_id,
                    "is_in_stage1_loot_scope": "true" if loot_table_id in stage1_table_ids else "false",
                    "link_source": "detected_from_data",
                    "link_method": detected["method"],
                    "notes": detected["notes"],
                }
                audit_rows.append(
                    {
                        "structure_set_id": structure_set_id,
                        "structure_id": structure_id,
                        "loot_table_id": loot_table_id,
                        "candidate_source": "detected_from_data",
                        "candidate_method": detected["method"],
                        "resolution": "active_detected_exact_match",
                        "notes": detected["notes"],
                    }
                )

        ambiguous_candidates = self._collect_ambiguous_match_candidates(
            structure_entry_lookup=structure_entry_lookup,
            exact_link_keys=set(exact_link_rows),
        )
        ambiguous_result = self._sync_ambiguous_resolution_entries(
            current_candidates=ambiguous_candidates,
            structure_entry_lookup=structure_entry_lookup,
        )
        audit_rows.extend(ambiguous_result["audit_rows"])

        exact_match_table_ids = {key[2] for key in exact_link_rows}
        ambiguous_match_table_ids = {key[0] for key in ambiguous_candidates}
        no_match_table_ids = sorted(stage1_table_ids - exact_match_table_ids - ambiguous_match_table_ids)

        manual_result = self._sync_manual_resolution_entries(
            current_no_match_table_ids=no_match_table_ids,
            structure_entry_lookup=structure_entry_lookup,
        )
        audit_rows.extend(manual_result["audit_rows"])

        link_rows: list[dict[str, Any]] = []
        link_rows.extend(exact_link_rows.values())
        link_rows.extend(ambiguous_result["active_link_rows"])
        link_rows.extend(manual_result["active_link_rows"])

        for row in sorted(
            link_rows,
            key=lambda value: (value["structure_set_id"], value["structure_id"], value["loot_table_id"]),
        ):
            pair_key = (row["structure_set_id"], row["structure_id"])
            pair_profile = profile_state[pair_key]
            loot_table_id = row["loot_table_id"]
            pair_profile["base_loot_table_ids"].add(loot_table_id)
            if row["link_source"] == "detected_from_data":
                pair_profile["detected_active_link_count"] += 1
            else:
                pair_profile["manual_active_link_count"] += 1
            if row["is_in_stage1_loot_scope"] != "true":
                pair_profile["out_of_scope_loot_table_count"] += 1

            for item_id in sorted(base_items_by_table.get(loot_table_id, set())):
                pair_profile["base_items"].add(item_id)
                pair_profile["effective_items"].add(item_id)
                presence_key = (row["structure_set_id"], row["structure_id"], item_id)
                base_state = base_presence_state.setdefault(presence_key, {"source_loot_table_ids": set()})
                base_state["source_loot_table_ids"].add(loot_table_id)

                effective_state = effective_presence_state.setdefault(
                    presence_key,
                    {"base_loot_table_ids": set(), "stage2_modifier_ids": set()},
                )
                effective_state["base_loot_table_ids"].add(loot_table_id)

            for item_id, modifier_ids in modifier_items_by_target.get(loot_table_id, {}).items():
                pair_profile["effective_items"].add(item_id)
                pair_profile["stage2_added_items"].add(item_id)
                presence_key = (row["structure_set_id"], row["structure_id"], item_id)
                effective_state = effective_presence_state.setdefault(
                    presence_key,
                    {"base_loot_table_ids": set(), "stage2_modifier_ids": set()},
                )
                effective_state["stage2_modifier_ids"].update(modifier_ids)

        self.structure_set_entry_rows = structure_entry_rows
        self.structure_set_loot_link_rows = sorted(
            link_rows,
            key=lambda row: (row["structure_set_id"], row["structure_id"], row["loot_table_id"]),
        )
        self.structure_set_loot_link_audit_rows = sorted(
            audit_rows,
            key=lambda row: (
                row["structure_set_id"],
                row["structure_id"],
                row["loot_table_id"],
                row["candidate_source"],
                row["candidate_method"],
                row["resolution"],
            ),
        )
        self.structure_set_base_item_presence_rows = [
            {
                "structure_set_id": structure_set_id,
                "structure_id": structure_id,
                "item_id": item_id,
                "source_loot_table_count": len(state["source_loot_table_ids"]),
                "source_loot_table_ids_json": json_cell(sorted(state["source_loot_table_ids"])),
            }
            for (structure_set_id, structure_id, item_id), state in sorted(base_presence_state.items())
        ]
        self.structure_set_effective_item_presence_rows = [
            {
                "structure_set_id": structure_set_id,
                "structure_id": structure_id,
                "item_id": item_id,
                "item_presence_kind": (
                    "base_and_stage2"
                    if state["base_loot_table_ids"] and state["stage2_modifier_ids"]
                    else "base_only"
                    if state["base_loot_table_ids"]
                    else "stage2_only"
                ),
                "base_loot_table_count": len(state["base_loot_table_ids"]),
                "base_loot_table_ids_json": json_cell(sorted(state["base_loot_table_ids"])),
                "stage2_modifier_count": len(state["stage2_modifier_ids"]),
                "stage2_modifier_ids_json": json_cell(sorted(state["stage2_modifier_ids"])),
            }
            for (structure_set_id, structure_id, item_id), state in sorted(effective_presence_state.items())
        ]
        self.structure_set_profile_summary_rows = [
            {
                "structure_set_id": structure_set_id,
                "structure_id": structure_id,
                "base_loot_table_count": len(state["base_loot_table_ids"]),
                "manual_active_link_count": state["manual_active_link_count"],
                "detected_active_link_count": state["detected_active_link_count"],
                "out_of_scope_loot_table_count": state["out_of_scope_loot_table_count"],
                "base_unique_item_count": len(state["base_items"]),
                "effective_unique_item_count": len(state["effective_items"]),
                "stage2_added_unique_item_count": len(state["stage2_added_items"]),
            }
            for (structure_set_id, structure_id), state in sorted(profile_state.items())
        ]
        self.structure_loot_resolution_report = {
            "exact_match_count": len(exact_link_rows),
            "ambiguous_match_candidate_count": len(ambiguous_candidates),
            "ambiguous_match_autoresolved_count": len(ambiguous_result["active_link_rows"]),
            "ambiguous_match_pending_count": sum(
                1 for row in ambiguous_result["current_rows"] if not parse_boolish(row.get("autoresolve"))
            ),
            "no_match_count": len(no_match_table_ids),
            "no_match_mapped_count": manual_result["mapped_table_count"],
            "no_match_unresolved_count": manual_result["unresolved_table_count"],
            "stale_ambiguous_rows": ambiguous_result["stale_rows"],
            "stale_manual_rows": manual_result["stale_rows"],
            "skipped_active_stale_rows": ambiguous_result["skipped_active_stale_rows"]
            + manual_result["skipped_active_stale_rows"],
            "warnings": ambiguous_result["warnings"] + manual_result["warnings"],
        }

    def _collect_effective_resource_ids(self, family: str, suffix: str) -> set[str]:
        found: set[str] = set()
        for resource_path in self.effective_resources:
            resource_id = resource_path_to_resource_id(resource_path, family, suffix)
            if resource_id is not None:
                found.add(resource_id)
        return found

    @staticmethod
    def _ambiguous_candidate_priority(match_rule: str) -> int:
        return {
            "structure_family_candidate": 2,
            "loose_table_candidate": 1,
        }.get(match_rule, 0)

    def _collect_ambiguous_match_candidates(
        self,
        *,
        structure_entry_lookup: dict[tuple[str, str], dict[str, Any]],
        exact_link_keys: set[tuple[str, str, str]],
    ) -> dict[tuple[str, str, str], dict[str, Any]]:
        candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
        named_table_set = set(self.named_table_ids)

        structure_entries_by_type: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for (structure_set_id, structure_id), row in sorted(structure_entry_lookup.items()):
            structure_type = self._string_or_blank(row.get("structure_type")).strip()
            if structure_type:
                structure_entries_by_type[structure_type].append((structure_set_id, structure_id))

        evidence_state: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for row in self.table_role_evidence_rows:
            if row["evidence_type"] != STRUCTURE_EVIDENCE_TYPE:
                continue
            loot_table_id = row["table_id"]
            if loot_table_id not in named_table_set:
                continue
            family = get_structure_family_from_source_object(self._string_or_blank(row.get("source_object")))
            if family in STRUCTURE_FAMILY_TYPE_REGISTRY:
                evidence_state[loot_table_id][family].add(self._string_or_blank(row.get("source_object")))

        for loot_table_id, family_map in sorted(evidence_state.items()):
            for family, source_objects in sorted(family_map.items()):
                structure_type = STRUCTURE_FAMILY_TYPE_REGISTRY[family]
                for structure_set_id, structure_id in structure_entries_by_type.get(structure_type, []):
                    key = (loot_table_id, structure_set_id, structure_id)
                    if (structure_set_id, structure_id, loot_table_id) in exact_link_keys:
                        continue
                    candidate = {
                        "loot_table_id": loot_table_id,
                        "structure_set_id": structure_set_id,
                        "structure_id": structure_id,
                        "match_rule": "structure_family_candidate",
                        "evidence_kind": "structure_nbt_family",
                        "evidence_data": {
                            "family": family,
                            "source_object_count": len(source_objects),
                            "source_objects": sorted(source_objects),
                        },
                        "autoresolve": False,
                        "notes": "",
                    }
                    existing = candidates.get(key)
                    if existing is None or self._ambiguous_candidate_priority(candidate["match_rule"]) > self._ambiguous_candidate_priority(existing["match_rule"]):
                        candidates[key] = candidate
                    elif existing["match_rule"] == candidate["match_rule"]:
                        merged_objects = sorted(
                            set(existing["evidence_data"].get("source_objects", [])) | set(candidate["evidence_data"]["source_objects"])
                        )
                        existing["evidence_data"]["source_objects"] = merged_objects
                        existing["evidence_data"]["source_object_count"] = len(merged_objects)

        for loot_table_id, raw_targets in sorted(LOOSE_TABLE_CANDIDATE_REGISTRY.items()):
            if loot_table_id not in named_table_set:
                continue
            for structure_set_id, structure_id in raw_targets:
                if (structure_set_id, structure_id) not in structure_entry_lookup:
                    continue
                if (structure_set_id, structure_id, loot_table_id) in exact_link_keys:
                    continue
                key = (loot_table_id, structure_set_id, structure_id)
                candidate = {
                    "loot_table_id": loot_table_id,
                    "structure_set_id": structure_set_id,
                    "structure_id": structure_id,
                    "match_rule": "loose_table_candidate",
                    "evidence_kind": "curated_table_lookup",
                    "evidence_data": {
                        "registry_key": loot_table_id,
                        "candidate_count": len(raw_targets),
                    },
                    "autoresolve": False,
                    "notes": "",
                }
                existing = candidates.get(key)
                if existing is None or self._ambiguous_candidate_priority(candidate["match_rule"]) > self._ambiguous_candidate_priority(existing["match_rule"]):
                    candidates[key] = candidate

        return dict(sorted(candidates.items()))

    def _load_yaml_entries(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        raw_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw_entries = ensure_list(raw_data.get("entries"), f"{path}.entries")
        return [entry for entry in raw_entries if isinstance(entry, dict)]

    def _normalize_ambiguous_resolution_entry(self, raw_entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "loot_table_id": self._string_or_blank(raw_entry.get("loot_table_id")).strip(),
            "structure_set_id": self._string_or_blank(raw_entry.get("structure_set_id")).strip(),
            "structure_id": self._string_or_blank(raw_entry.get("structure_id")).strip(),
            "match_rule": self._string_or_blank(raw_entry.get("match_rule")).strip(),
            "evidence_kind": self._string_or_blank(raw_entry.get("evidence_kind")).strip(),
            "evidence_data": raw_entry.get("evidence_data") if isinstance(raw_entry.get("evidence_data"), dict) else {},
            "autoresolve": parse_boolish(raw_entry.get("autoresolve")),
            "notes": self._string_or_blank(raw_entry.get("notes")).strip(),
        }

    def _write_ambiguous_resolution_yaml(self, entries: list[dict[str, Any]]) -> None:
        write_yaml_with_header(
            self.ambiguous_resolution_config_path,
            header_lines=AMBIGUOUS_RESOLUTION_YAML_HEADER,
            payload={"version": 1, "entries": entries},
        )

    def _sync_ambiguous_resolution_entries(
        self,
        *,
        current_candidates: dict[tuple[str, str, str], dict[str, Any]],
        structure_entry_lookup: dict[tuple[str, str], dict[str, Any]],
    ) -> dict[str, Any]:
        existing_entries = [
            self._normalize_ambiguous_resolution_entry(row)
            for row in self._load_yaml_entries(self.ambiguous_resolution_config_path)
        ]
        seen_keys: set[tuple[str, str, str]] = set()
        final_entries: list[dict[str, Any]] = []
        current_rows: list[dict[str, Any]] = []
        active_link_rows: list[dict[str, Any]] = []
        audit_rows: list[dict[str, Any]] = []
        stale_rows: list[dict[str, Any]] = []
        skipped_active_stale_rows: list[dict[str, Any]] = []
        warnings: list[str] = []

        for existing in existing_entries:
            key = (existing["loot_table_id"], existing["structure_set_id"], existing["structure_id"])
            if key in current_candidates:
                current = current_candidates[key]
                merged = {
                    **current,
                    "autoresolve": existing["autoresolve"],
                    "notes": existing["notes"],
                }
                final_entries.append(merged)
                current_rows.append(merged)
                seen_keys.add(key)
                continue
            final_entries.append(existing)
            stale_rows.append(existing)
            if existing["autoresolve"]:
                warning = (
                    "stale ambiguous autoresolve skipped for "
                    f"{existing['loot_table_id']} -> {existing['structure_set_id']} / {existing['structure_id']}"
                )
                warnings.append(warning)
                skipped_active_stale_rows.append(
                    {
                        "resolution_source": "ambiguous_match",
                        "loot_table_id": existing["loot_table_id"],
                        "structure_set_id": existing["structure_set_id"],
                        "structure_id": existing["structure_id"],
                        "warning": warning,
                    }
                )
                audit_rows.append(
                    {
                        "structure_set_id": existing["structure_set_id"],
                        "structure_id": existing["structure_id"],
                        "loot_table_id": existing["loot_table_id"],
                        "candidate_source": "ambiguous_match",
                        "candidate_method": existing["match_rule"],
                        "resolution": "skipped_stale_ambiguous_autoresolve",
                        "notes": existing["notes"] or warning,
                    }
                )

        for key, current in current_candidates.items():
            if key in seen_keys:
                continue
            final_entries.append(current)
            current_rows.append(current)

        self._write_ambiguous_resolution_yaml(final_entries)

        named_table_set = set(self.named_table_ids)
        for row in current_rows:
            if parse_boolish(row.get("autoresolve")):
                if (row["structure_set_id"], row["structure_id"]) not in structure_entry_lookup:
                    warning = (
                        "ambiguous autoresolve target missing from current structure set entries for "
                        f"{row['loot_table_id']} -> {row['structure_set_id']} / {row['structure_id']}"
                    )
                    warnings.append(warning)
                    skipped_active_stale_rows.append(
                        {
                            "resolution_source": "ambiguous_match",
                            "loot_table_id": row["loot_table_id"],
                            "structure_set_id": row["structure_set_id"],
                            "structure_id": row["structure_id"],
                            "warning": warning,
                        }
                    )
                    audit_rows.append(
                        {
                            "structure_set_id": row["structure_set_id"],
                            "structure_id": row["structure_id"],
                            "loot_table_id": row["loot_table_id"],
                            "candidate_source": "ambiguous_match",
                            "candidate_method": row["match_rule"],
                            "resolution": "skipped_stale_ambiguous_autoresolve",
                            "notes": row["notes"] or warning,
                        }
                    )
                    continue
                active_link_rows.append(
                    {
                        "structure_set_id": row["structure_set_id"],
                        "structure_id": row["structure_id"],
                        "loot_table_id": row["loot_table_id"],
                        "is_in_stage1_loot_scope": "true" if row["loot_table_id"] in named_table_set else "false",
                        "link_source": "ambiguous_match",
                        "link_method": row["match_rule"],
                        "notes": row["notes"] or f"{row['evidence_kind']}:{json_cell(row['evidence_data'])}",
                    }
                )
                audit_rows.append(
                    {
                        "structure_set_id": row["structure_set_id"],
                        "structure_id": row["structure_id"],
                        "loot_table_id": row["loot_table_id"],
                        "candidate_source": "ambiguous_match",
                        "candidate_method": row["match_rule"],
                        "resolution": "active_ambiguous_autoresolve",
                        "notes": row["notes"],
                    }
                )
            else:
                audit_rows.append(
                    {
                        "structure_set_id": row["structure_set_id"],
                        "structure_id": row["structure_id"],
                        "loot_table_id": row["loot_table_id"],
                        "candidate_source": "ambiguous_match",
                        "candidate_method": row["match_rule"],
                        "resolution": "pending_ambiguous_match",
                        "notes": row["notes"],
                    }
                )

        return {
            "current_rows": current_rows,
            "active_link_rows": active_link_rows,
            "audit_rows": audit_rows,
            "stale_rows": stale_rows,
            "skipped_active_stale_rows": skipped_active_stale_rows,
            "warnings": warnings,
        }

    def _normalize_manual_resolution_entry(self, raw_entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "loot_table_id": self._string_or_blank(raw_entry.get("loot_table_id")).strip(),
            "status": self._string_or_blank(raw_entry.get("status")).strip(),
            "structure_set_id": self._string_or_blank(raw_entry.get("structure_set_id")).strip(),
            "structure_id": self._string_or_blank(raw_entry.get("structure_id")).strip(),
            "notes": self._string_or_blank(raw_entry.get("notes")).strip(),
        }

    def _write_manual_resolution_yaml(self, entries: list[dict[str, Any]]) -> None:
        write_yaml_with_header(
            self.manual_resolution_config_path,
            header_lines=MANUAL_RESOLUTION_YAML_HEADER,
            payload={"version": 1, "entries": entries},
        )

    def _sync_manual_resolution_entries(
        self,
        *,
        current_no_match_table_ids: list[str],
        structure_entry_lookup: dict[tuple[str, str], dict[str, Any]],
    ) -> dict[str, Any]:
        current_no_match_set = set(current_no_match_table_ids)
        existing_entries = [
            self._normalize_manual_resolution_entry(row)
            for row in self._load_yaml_entries(self.manual_resolution_config_path)
        ]
        rows_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
        stale_rows: list[dict[str, Any]] = []
        skipped_active_stale_rows: list[dict[str, Any]] = []
        warnings: list[str] = []

        for entry in existing_entries:
            rows_by_table[entry["loot_table_id"]].append(entry)
            if entry["loot_table_id"] not in current_no_match_set:
                stale_rows.append(entry)
                if entry["status"] == "mapped" and entry["structure_set_id"] and entry["structure_id"]:
                    warning = (
                        "stale manual no-match mapping skipped for "
                        f"{entry['loot_table_id']} -> {entry['structure_set_id']} / {entry['structure_id']}"
                    )
                    warnings.append(warning)
                    skipped_active_stale_rows.append(
                        {
                            "resolution_source": "manual_no_match",
                            "loot_table_id": entry["loot_table_id"],
                            "structure_set_id": entry["structure_set_id"],
                            "structure_id": entry["structure_id"],
                            "warning": warning,
                        }
                    )

        final_entries = list(existing_entries)
        for loot_table_id in current_no_match_table_ids:
            existing = rows_by_table.get(loot_table_id, [])
            has_unresolved = any(
                row["status"] == "unresolved" and not row["structure_set_id"] and not row["structure_id"]
                for row in existing
            )
            valid_mapped_rows = [
                row
                for row in existing
                if row["status"] == "mapped"
                and row["structure_set_id"]
                and row["structure_id"]
                and (row["structure_set_id"], row["structure_id"]) in structure_entry_lookup
            ]
            if not existing or (not has_unresolved and not valid_mapped_rows):
                unresolved = {
                    "loot_table_id": loot_table_id,
                    "status": "unresolved",
                    "structure_set_id": "",
                    "structure_id": "",
                    "notes": "",
                }
                final_entries.append(unresolved)
                rows_by_table[loot_table_id].append(unresolved)

        self._write_manual_resolution_yaml(final_entries)

        active_link_rows: list[dict[str, Any]] = []
        audit_rows: list[dict[str, Any]] = []
        mapped_table_ids: set[str] = set()
        unresolved_table_ids: set[str] = set()
        named_table_set = set(self.named_table_ids)

        for loot_table_id in current_no_match_table_ids:
            entries = rows_by_table.get(loot_table_id, [])
            if any(
                row["status"] == "unresolved" and not row["structure_set_id"] and not row["structure_id"]
                for row in entries
            ):
                unresolved_table_ids.add(loot_table_id)

            for row in entries:
                if row["status"] != "mapped" or not row["structure_set_id"] or not row["structure_id"]:
                    continue
                pair_key = (row["structure_set_id"], row["structure_id"])
                if pair_key not in structure_entry_lookup:
                    warning = (
                        "manual no-match mapping target missing from current structure set entries for "
                        f"{row['loot_table_id']} -> {row['structure_set_id']} / {row['structure_id']}"
                    )
                    warnings.append(warning)
                    skipped_active_stale_rows.append(
                        {
                            "resolution_source": "manual_no_match",
                            "loot_table_id": row["loot_table_id"],
                            "structure_set_id": row["structure_set_id"],
                            "structure_id": row["structure_id"],
                            "warning": warning,
                        }
                    )
                    audit_rows.append(
                        {
                            "structure_set_id": row["structure_set_id"],
                            "structure_id": row["structure_id"],
                            "loot_table_id": row["loot_table_id"],
                            "candidate_source": "manual_no_match",
                            "candidate_method": "manual_resolution_map",
                            "resolution": "skipped_stale_manual_no_match",
                            "notes": row["notes"] or warning,
                        }
                    )
                    continue
                mapped_table_ids.add(loot_table_id)
                active_link_rows.append(
                    {
                        "structure_set_id": row["structure_set_id"],
                        "structure_id": row["structure_id"],
                        "loot_table_id": row["loot_table_id"],
                        "is_in_stage1_loot_scope": "true" if row["loot_table_id"] in named_table_set else "false",
                        "link_source": "manual_no_match",
                        "link_method": "manual_resolution_map",
                        "notes": row["notes"],
                    }
                )
                audit_rows.append(
                    {
                        "structure_set_id": row["structure_set_id"],
                        "structure_id": row["structure_id"],
                        "loot_table_id": row["loot_table_id"],
                        "candidate_source": "manual_no_match",
                        "candidate_method": "manual_resolution_map",
                        "resolution": "active_manual_no_match",
                        "notes": row["notes"],
                    }
                )

        return {
            "active_link_rows": active_link_rows,
            "audit_rows": audit_rows,
            "stale_rows": stale_rows,
            "skipped_active_stale_rows": skipped_active_stale_rows,
            "warnings": warnings,
            "mapped_table_count": len(mapped_table_ids),
            "unresolved_table_count": len(unresolved_table_ids),
        }

    def _detect_structure_links_for_entry(
        self,
        *,
        structure_id: str,
        all_loot_table_ids: set[str],
        all_template_pool_ids: set[str],
    ) -> tuple[str, dict[str, dict[str, str]]]:
        structure_resource_path = structure_id_to_resource_path(structure_id)
        effective = self.effective_resources.get(structure_resource_path)
        if effective is None:
            return "missing_structure_resource", {}
        try:
            raw_structure = ensure_dict(
                json.loads(read_pack_text(effective.pack, structure_resource_path)),
                effective.display_source_path(),
            )
        except Exception:
            return "invalid_structure_json", {}

        structure_type = self._string_or_blank(raw_structure.get("type"))
        if structure_type != "minecraft:jigsaw":
            return f"unsupported_structure_type:{structure_type or 'missing'}", {}
        start_pool_value = raw_structure.get("start_pool")
        if not isinstance(start_pool_value, str) or not start_pool_value.strip():
            return "missing_start_pool", {}

        detected_links = self._detect_jigsaw_structure_links(
            structure_id=structure_id,
            raw_structure=raw_structure,
            all_loot_table_ids=all_loot_table_ids,
            all_template_pool_ids=all_template_pool_ids,
        )
        return ("detected_links_found" if detected_links else "no_links_detected"), detected_links

    def _detect_jigsaw_structure_links(
        self,
        *,
        structure_id: str,
        raw_structure: dict[str, Any],
        all_loot_table_ids: set[str],
        all_template_pool_ids: set[str],
    ) -> dict[str, dict[str, str]]:
        default_namespace = structure_id.split(":", 1)[0]
        start_pool_id = normalize_namespaced_id(self._string_or_blank(raw_structure.get("start_pool")), default_namespace)
        alias_targets = self._extract_pool_alias_targets(raw_structure, default_namespace)
        known_pool_targets = set(all_template_pool_ids) | set(alias_targets)
        detected_links: dict[str, dict[str, str]] = {}
        queue: list[str] = sorted(alias_targets.get(start_pool_id, {start_pool_id}))
        seen_pools: set[str] = set()
        processor_cache: dict[str, set[str]] = {}
        template_cache: dict[str, tuple[set[str], set[str]]] = {}

        while queue:
            pool_id = queue.pop(0)
            if pool_id in seen_pools:
                continue
            seen_pools.add(pool_id)
            resource_path = template_pool_id_to_resource_path(pool_id)
            effective = self.effective_resources.get(resource_path)
            if effective is None:
                continue
            try:
                raw_pool = ensure_dict(
                    json.loads(read_pack_text(effective.pack, resource_path)),
                    effective.display_source_path(),
                )
            except Exception:
                continue
            for wrapper in ensure_list(raw_pool.get("elements"), f"{pool_id}.elements"):
                if not isinstance(wrapper, dict):
                    continue
                self._walk_pool_element_for_structure_links(
                    raw_element=wrapper.get("element"),
                    default_namespace=pool_id.split(":", 1)[0],
                    all_loot_table_ids=all_loot_table_ids,
                    known_pool_targets=known_pool_targets,
                    alias_targets=alias_targets,
                    queue=queue,
                    detected_links=detected_links,
                    processor_cache=processor_cache,
                    template_cache=template_cache,
                )
        return detected_links

    def _extract_pool_alias_targets(self, raw_structure: dict[str, Any], default_namespace: str) -> dict[str, set[str]]:
        aliases: dict[str, set[str]] = defaultdict(set)

        def visit(node: Any) -> None:
            if isinstance(node, dict):
                alias_value = node.get("alias")
                target_value = node.get("target")
                if isinstance(alias_value, str) and isinstance(target_value, str):
                    aliases[normalize_namespaced_id(alias_value, default_namespace)].add(
                        normalize_namespaced_id(target_value, default_namespace)
                    )
                targets = node.get("targets")
                if isinstance(alias_value, str) and isinstance(targets, list):
                    alias_id = normalize_namespaced_id(alias_value, default_namespace)
                    for raw_target in targets:
                        if isinstance(raw_target, dict) and isinstance(raw_target.get("data"), str):
                            aliases[alias_id].add(normalize_namespaced_id(raw_target["data"], default_namespace))
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(raw_structure.get("pool_aliases"))
        return {alias_id: set(targets) for alias_id, targets in aliases.items()}

    def _walk_pool_element_for_structure_links(
        self,
        *,
        raw_element: Any,
        default_namespace: str,
        all_loot_table_ids: set[str],
        known_pool_targets: set[str],
        alias_targets: dict[str, set[str]],
        queue: list[str],
        detected_links: dict[str, dict[str, str]],
        processor_cache: dict[str, set[str]],
        template_cache: dict[str, tuple[set[str], set[str]]],
    ) -> None:
        if not isinstance(raw_element, dict):
            return
        element_type = self._string_or_blank(raw_element.get("element_type"))
        if element_type == "minecraft:list_pool_element":
            for child in ensure_list(raw_element.get("elements"), "list_pool_element.elements"):
                self._walk_pool_element_for_structure_links(
                    raw_element=child,
                    default_namespace=default_namespace,
                    all_loot_table_ids=all_loot_table_ids,
                    known_pool_targets=known_pool_targets,
                    alias_targets=alias_targets,
                    queue=queue,
                    detected_links=detected_links,
                    processor_cache=processor_cache,
                    template_cache=template_cache,
                )
            return
        if element_type in {"minecraft:empty_pool_element", "minecraft:feature_pool_element"}:
            return
        if not element_type.endswith("single_pool_element"):
            return

        location_value = raw_element.get("location")
        if not isinstance(location_value, str) or not location_value.strip():
            return
        template_id = normalize_namespaced_id(location_value.strip(), default_namespace)
        loot_ids, next_pool_ids = template_cache.setdefault(
            template_id,
            self._scan_structure_template_links(template_id, all_loot_table_ids, known_pool_targets),
        )
        for loot_table_id in sorted(loot_ids):
            detected_links.setdefault(
                loot_table_id,
                {"method": "jigsaw_start_pool_traversal", "notes": template_id},
            )

        processors_value = raw_element.get("processors")
        if isinstance(processors_value, str) and processors_value.strip() and processors_value.strip() != "minecraft:empty":
            processor_id = normalize_namespaced_id(processors_value.strip(), default_namespace)
            processor_loot_ids = processor_cache.setdefault(
                processor_id,
                self._scan_processor_list_loot_links(processor_id, all_loot_table_ids),
            )
            for loot_table_id in sorted(processor_loot_ids):
                detected_links.setdefault(
                    loot_table_id,
                    {"method": "jigsaw_processor_assignment", "notes": processor_id},
                )

        for next_pool_id in sorted(next_pool_ids):
            for expanded_pool_id in sorted(alias_targets.get(next_pool_id, {next_pool_id})):
                if expanded_pool_id not in queue:
                    queue.append(expanded_pool_id)

    def _scan_structure_template_links(
        self,
        template_id: str,
        all_loot_table_ids: set[str],
        known_pool_targets: set[str],
    ) -> tuple[set[str], set[str]]:
        resource_path = structure_template_id_to_resource_path(template_id)
        effective = self.effective_resources.get(resource_path)
        if effective is None:
            return set(), set()
        search_bytes = self._read_search_bytes_for_resource(effective)
        matched_ids = {match.decode("utf-8") for match in LOOT_ID_SEARCH_PATTERN.findall(search_bytes)}
        return matched_ids & all_loot_table_ids, matched_ids & known_pool_targets

    def _scan_processor_list_loot_links(self, processor_id: str, all_loot_table_ids: set[str]) -> set[str]:
        resource_path = processor_list_id_to_resource_path(processor_id)
        effective = self.effective_resources.get(resource_path)
        if effective is None:
            return set()
        try:
            raw_json = json.loads(read_pack_text(effective.pack, resource_path))
        except Exception:
            return set()
        return {
            table_id
            for table_id, _pointer in self._find_direct_assignment_matches(raw_json)
            if table_id in all_loot_table_ids
        }

    def _build_item_classification_outputs(self) -> None:
        self.classification_records = load_classification_records(self.classification_csv_path)
        self.classification_version = ""
        for record in self.classification_records.values():
            if record.classification_version:
                self.classification_version = record.classification_version
                break
        if not self.classification_version and self.classification_csv_path is not None:
            self.classification_version = infer_classification_version(self.classification_csv_path)

        self.item_classification_rows = [
            {
                "item_id": record.item_id,
                "function": record.function,
                "value": record.value,
                "amount_class": record.amount_class,
                "matched_rule_id": record.matched_rule_id,
                "matched_detail": record.matched_detail,
                "classification_status": record.classification_status,
                "is_fallback_match": "true" if record.is_fallback_match else "false",
                "classification_version": record.classification_version,
            }
            for record in sorted(self.classification_records.values(), key=lambda row: row.item_id)
        ]

        affinity_rows: list[dict[str, Any]] = []
        for record in sorted(self.classification_records.values(), key=lambda row: row.item_id):
            for affinity in record.affinities:
                affinity_rows.append(
                    {
                        "item_id": record.item_id,
                        "affinity": affinity,
                        "classification_version": record.classification_version,
                    }
                )
        self.item_affinity_rows = affinity_rows

        loot_items: dict[str, dict[str, Any]] = {}
        for row in self.leaf_rows:
            item_id = row["item_id"]
            if not item_id:
                continue
            state = loot_items.setdefault(
                item_id,
                {
                    "root_table_ids": set(),
                    "leaf_row_count": 0,
                },
            )
            state["root_table_ids"].add(row["root_table_id"])
            state["leaf_row_count"] += 1

        coverage_rows: list[dict[str, Any]] = []
        for item_id in sorted(loot_items):
            state = loot_items[item_id]
            record = self.classification_records.get(item_id)
            coverage_rows.append(
                {
                    "item_id": item_id,
                    "loot_root_table_count": len(state["root_table_ids"]),
                    "loot_leaf_row_count": state["leaf_row_count"],
                    "has_classification": "true" if record is not None else "false",
                    "classification_status": record.classification_status if record is not None else "missing",
                    "is_fallback_match": "true" if record is not None and record.is_fallback_match else "false",
                    "function": record.function if record is not None else "",
                    "value": record.value if record is not None else "",
                    "amount_class": record.amount_class if record is not None else "",
                    "matched_rule_id": record.matched_rule_id if record is not None else "",
                    "matched_detail": record.matched_detail if record is not None else "",
                    "classification_version": record.classification_version if record is not None else self.classification_version,
                }
            )
        self.classification_coverage_rows = coverage_rows

    def _scan_structure_evidence(self) -> list[RoleEvidenceRecord]:
        named_table_set = set(self.named_table_ids)
        if not named_table_set:
            return []

        evidence_rows: list[RoleEvidenceRecord] = []
        for resource_path in sorted(self.effective_resources):
            if get_resource_family(resource_path) != "structure" or not resource_path.endswith(".nbt"):
                continue
            effective = self.effective_resources[resource_path]
            search_bytes = self._read_search_bytes_for_resource(effective)
            source_object = get_structure_source_object(resource_path)
            matched_ids = {
                match.decode("utf-8")
                for match in LOOT_ID_SEARCH_PATTERN.findall(search_bytes)
            }
            for table_id in sorted(matched_ids & named_table_set):
                evidence_rows.append(
                    RoleEvidenceRecord(
                        table_id=table_id,
                        evidence_type=STRUCTURE_EVIDENCE_TYPE,
                        source_path=effective.display_source_path(),
                        source_object=source_object,
                        target_table_id=table_id,
                    )
                )
        return evidence_rows

    def _scan_direct_assignment_evidence(self) -> list[RoleEvidenceRecord]:
        named_table_set = set(self.named_table_ids)
        evidence_rows: list[RoleEvidenceRecord] = []

        for resource_path in sorted(self.effective_resources):
            if not resource_path.endswith(".json"):
                continue
            if get_resource_family(resource_path) not in DIRECT_ASSIGNMENT_DIRS:
                continue
            effective = self.effective_resources[resource_path]
            raw_json = json.loads(read_pack_text(effective.pack, resource_path))
            for table_id, pointer in self._find_direct_assignment_matches(raw_json):
                if table_id not in named_table_set:
                    continue
                evidence_rows.append(
                    RoleEvidenceRecord(
                        table_id=table_id,
                        evidence_type=DATA_ASSIGNMENT_EVIDENCE_TYPE,
                        source_path=effective.display_source_path(),
                        source_object=pointer,
                        target_table_id=table_id,
                    )
                )
        return evidence_rows

    def _find_direct_assignment_matches(self, node: Any, pointer: str = "$") -> list[tuple[str, str]]:
        matches: list[tuple[str, str]] = []

        if isinstance(node, dict):
            for key, value in node.items():
                child_pointer = f"{pointer}.{key}"
                if key in DIRECT_ASSIGNMENT_KEYS and isinstance(value, str):
                    matches.append((value, child_pointer))
                matches.extend(self._find_direct_assignment_matches(value, child_pointer))
            return matches

        if isinstance(node, list):
            for index, value in enumerate(node):
                matches.extend(self._find_direct_assignment_matches(value, f"{pointer}[{index}]"))
        return matches

    def _build_role_note(self, raw_role: str) -> str:
        if raw_role == "helper_from_data":
            return "Referenced by other scoped loot tables but no direct data-side invocation evidence was found."
        if raw_role == "direct_from_data":
            return "Direct data-side invocation evidence was found with no inbound scoped loot-table references."
        if raw_role == "both_direct_and_helper":
            return "Direct data-side invocation evidence was found and the table is also referenced by other scoped loot tables."
        return (
            "No direct data-side invocation evidence was found locally; Tableau treats this as direct because "
            "missing data-side references are not trusted as proof of helper-only status."
        )

    def _read_search_bytes_for_resource(self, effective: EffectiveResource) -> bytes:
        raw_bytes = read_pack_bytes(effective.pack, effective.resource_path)
        if raw_bytes.startswith(b"\x1f\x8b"):
            try:
                return gzip.decompress(raw_bytes)
            except OSError:
                return raw_bytes
        return raw_bytes

    def _build_manifest(self) -> dict[str, Any]:
        named_tables = [table for table in self.tables.values() if table.table_id_kind == "named"]
        inline_tables = [table for table in self.tables.values() if table.table_id_kind == "inline"]
        classified_loot_item_count = sum(
            1 for row in self.classification_coverage_rows if row["has_classification"] == "true"
        )
        missing_loot_item_count = sum(
            1 for row in self.classification_coverage_rows if row["has_classification"] != "true"
        )
        return {
            "base_pack_root": str(self.base_pack_root),
            "scope_config_source": self.scope_settings.source,
            "pack_order_source": self.pack_order_source,
            "classification_csv_source": str(self.classification_csv_path) if self.classification_csv_path is not None else "",
            "classification_version": self.classification_version,
            "output_dir": str(self.output_dir),
            "selected_pack_ids": [pack.pack_id for pack in self.ordered_packs],
            "selected_pack_count": len(self.ordered_packs),
            "named_table_count": len(named_tables),
            "inline_table_count": len(inline_tables),
            "table_count": len(self.tables),
            "pool_count": len(self.pools),
            "entry_count": len(self.entries),
            "leaf_candidate_count": len(self.leaf_rows),
            "named_reference_count": self.named_reference_count,
            "inline_reference_count": self.inline_reference_count,
            "table_role_summary_count": len(self.table_role_summary_rows),
            "table_role_evidence_count": len(self.table_role_evidence_rows),
            "glm_modifier_chain_count": len(self.glm_modifier_chain_rows),
            "modifier_added_leaf_candidate_count": len(self.modifier_added_leaf_rows),
            "target_table_modifier_summary_count": len(self.target_table_modifier_summary_rows),
            "target_table_added_item_summary_count": len(self.target_table_added_item_summary_rows),
            "item_classification_count": len(self.item_classification_rows),
            "item_affinity_count": len(self.item_affinity_rows),
            "classification_coverage_count": len(self.classification_coverage_rows),
            "structure_set_entry_count": len(self.structure_set_entry_rows),
            "structure_set_loot_link_count": len(self.structure_set_loot_link_rows),
            "structure_set_loot_link_audit_count": len(self.structure_set_loot_link_audit_rows),
            "structure_set_base_item_presence_count": len(self.structure_set_base_item_presence_rows),
            "structure_set_effective_item_presence_count": len(self.structure_set_effective_item_presence_rows),
            "structure_set_profile_summary_count": len(self.structure_set_profile_summary_rows),
            "classified_loot_item_count": classified_loot_item_count,
            "missing_loot_item_count": missing_loot_item_count,
            "raw_role_counts": dict(sorted(self.raw_role_counts.items())),
            "effective_role_counts": dict(sorted(self.effective_role_counts.items())),
        }

    def _write_output_bundle(
        self,
        scope_report: dict[str, Any],
        manifest: dict[str, Any],
        precheck_report: dict[str, Any],
    ) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._write_csv(
            self.output_dir / "tables.csv",
            TABLES_FIELDNAMES,
            [self.tables[table_id].to_row() for table_id in sorted(self.tables)],
        )
        self._write_csv(
            self.output_dir / "pools.csv",
            POOLS_FIELDNAMES,
            [self.pools[pool_id].to_row() for pool_id in sorted(self.pools)],
        )
        self._write_csv(
            self.output_dir / "entries.csv",
            ENTRIES_FIELDNAMES,
            [self.entries[entry_id].to_row() for entry_id in sorted(self.entries)],
        )
        self._write_csv(
            self.output_dir / "leaf_candidates.csv",
            LEAF_FIELDNAMES,
            sorted(
                self.leaf_rows,
                key=lambda row: (
                    row["root_table_id"],
                    row["root_pool_index"],
                    row["root_entry_id"],
                    row["leaf_table_id"],
                    row["leaf_entry_id"],
                ),
            ),
        )
        self._write_csv(
            self.output_dir / "table_role_summary.csv",
            TABLE_ROLE_SUMMARY_FIELDNAMES,
            self.table_role_summary_rows,
        )
        self._write_csv(
            self.output_dir / "table_role_evidence.csv",
            TABLE_ROLE_EVIDENCE_FIELDNAMES,
            self.table_role_evidence_rows,
        )
        self._write_csv(
            self.output_dir / "glm_modifier_chain.csv",
            GLM_MODIFIER_CHAIN_FIELDNAMES,
            self.glm_modifier_chain_rows,
        )
        self._write_csv(
            self.output_dir / "modifier_added_leaf_candidates.csv",
            MODIFIER_ADDED_LEAF_FIELDNAMES,
            self.modifier_added_leaf_rows,
        )
        self._write_csv(
            self.output_dir / "target_table_modifier_summary.csv",
            TARGET_TABLE_MODIFIER_SUMMARY_FIELDNAMES,
            self.target_table_modifier_summary_rows,
        )
        self._write_csv(
            self.output_dir / "target_table_added_item_summary.csv",
            TARGET_TABLE_ADDED_ITEM_SUMMARY_FIELDNAMES,
            self.target_table_added_item_summary_rows,
        )
        self._write_csv(
            self.output_dir / "item_classification.csv",
            ITEM_CLASSIFICATION_FIELDNAMES,
            self.item_classification_rows,
        )
        self._write_csv(
            self.output_dir / "item_affinities.csv",
            ITEM_AFFINITIES_FIELDNAMES,
            self.item_affinity_rows,
        )
        self._write_csv(
            self.output_dir / "classification_coverage.csv",
            CLASSIFICATION_COVERAGE_FIELDNAMES,
            self.classification_coverage_rows,
        )
        self._write_csv(
            self.output_dir / "structure_set_entries.csv",
            STRUCTURE_SET_ENTRIES_FIELDNAMES,
            self.structure_set_entry_rows,
        )
        self._write_csv(
            self.output_dir / "structure_set_loot_links.csv",
            STRUCTURE_SET_LOOT_LINKS_FIELDNAMES,
            self.structure_set_loot_link_rows,
        )
        self._write_csv(
            self.output_dir / "structure_set_loot_link_audit.csv",
            STRUCTURE_SET_LOOT_LINK_AUDIT_FIELDNAMES,
            self.structure_set_loot_link_audit_rows,
        )
        self._write_csv(
            self.output_dir / "structure_set_base_item_presence.csv",
            STRUCTURE_SET_BASE_ITEM_PRESENCE_FIELDNAMES,
            self.structure_set_base_item_presence_rows,
        )
        self._write_csv(
            self.output_dir / "structure_set_effective_item_presence.csv",
            STRUCTURE_SET_EFFECTIVE_ITEM_PRESENCE_FIELDNAMES,
            self.structure_set_effective_item_presence_rows,
        )
        self._write_csv(
            self.output_dir / "structure_set_profile_summary.csv",
            STRUCTURE_SET_PROFILE_SUMMARY_FIELDNAMES,
            self.structure_set_profile_summary_rows,
        )

        write_json(self.output_dir / "scope_report.json", scope_report)
        write_json(self.output_dir / "manifest.json", manifest)
        write_json(self.output_dir / DEFAULT_PRECHECK_FILENAME, precheck_report)
        write_json(self.output_dir / "stage2_report.json", self.stage2_report)
        write_json(self.output_dir / DEFAULT_STRUCTURE_LOOT_RESOLUTION_REPORT, self.structure_loot_resolution_report)
        (self.output_dir / "README.md").write_text(
            self._build_readme(scope_report, manifest, precheck_report),
            encoding="utf-8",
        )

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _build_readme(
        self,
        scope_report: dict[str, Any],
        manifest: dict[str, Any],
        precheck_report: dict[str, Any],
    ) -> str:
        included_lines = [
            f"- `{item['name']}`: {item['file_count']} effective loot-table resources"
            for item in scope_report["included_dirs"]
        ]
        excluded_lines = [
            f"- `{item['name']}`: {item['file_count']} effective loot-table resources"
            for item in scope_report["excluded_dirs"]
        ]
        deferred_lines = [
            f"- `{item['name']}`: {item['file_count']} effective loot-table resources"
            for item in scope_report["deferred_dirs"]
        ]
        warning_lines = [
            f"- `{warning['name']}` introduced by {', '.join(warning['pack_ids'])}"
            for warning in scope_report["warnings"]
        ]
        selected_pack_lines = [
            f"- `{row['pack_id']}` ({row['kind']}) from `{row['path']}`"
            for row in precheck_report["selected_packs"]
        ]

        lines = [
            "# Loot Stack V1",
            "",
            "Effective layered Stage 1 loot-table export built from the implicit vanilla base plus selected mod packs.",
            "",
            "## Summary",
            "",
            f"- Base pack root: `{manifest['base_pack_root']}`",
            f"- Scope config: `{scope_report['scope_config_source']}`",
            f"- Ignore roots: {', '.join(f'`{path}`' for path in precheck_report['ignore_roots']) or '`None`'}",
            f"- Selected pack count: {manifest['selected_pack_count']}",
            f"- Classification source: `{manifest['classification_csv_source'] or 'not found'}`",
            f"- Classification version: `{manifest['classification_version'] or 'unknown'}`",
            f"- Named table rows: {manifest['named_table_count']}",
            f"- Inline table rows: {manifest['inline_table_count']}",
            f"- Pool rows: {manifest['pool_count']}",
            f"- Entry rows: {manifest['entry_count']}",
            f"- Leaf candidate rows: {manifest['leaf_candidate_count']}",
            f"- Table role rows: {manifest['table_role_summary_count']}",
            f"- Table role evidence rows: {manifest['table_role_evidence_count']}",
            f"- GLM chain rows: {manifest['glm_modifier_chain_count']}",
            f"- Modifier-added leaf rows: {manifest['modifier_added_leaf_candidate_count']}",
            f"- Target table modifier summary rows: {manifest['target_table_modifier_summary_count']}",
            f"- Target table added item summary rows: {manifest['target_table_added_item_summary_count']}",
            f"- Item classification rows: {manifest['item_classification_count']}",
            f"- Item affinity rows: {manifest['item_affinity_count']}",
            f"- Classification coverage rows: {manifest['classification_coverage_count']}",
            f"- Structure-set entry rows: {manifest['structure_set_entry_count']}",
            f"- Structure-set loot-link rows: {manifest['structure_set_loot_link_count']}",
            f"- Structure-set loot-link audit rows: {manifest['structure_set_loot_link_audit_count']}",
            f"- Structure-set base item presence rows: {manifest['structure_set_base_item_presence_count']}",
            f"- Structure-set effective item presence rows: {manifest['structure_set_effective_item_presence_count']}",
            f"- Structure-set profile summary rows: {manifest['structure_set_profile_summary_count']}",
            f"- Classified loot items: {manifest['classified_loot_item_count']}",
            f"- Missing loot items: {manifest['missing_loot_item_count']}",
            "",
            "## Selected Packs",
            "",
            *(selected_pack_lines or ["- None"]),
            "",
            "## Files",
            "",
            "- `precheck_report.json`: discovered packs, selected packs, effective order, overlap groups, and fatal precheck errors.",
            "- `tables.csv`: one row per effective named table plus synthetic inline table.",
            "- `pools.csv`: one row per pool with roll metadata and pool-level conditions.",
            "- `entries.csv`: one row per entry with direct metadata, raw JSON, reference targets, and entry-level pool weight shares.",
            "- `leaf_candidates.csv`: denormalized root-to-leaf paths for Tableau-style analysis, including raw path weights and normalized pool-share metrics.",
            "- `table_role_summary.csv`: one row per named effective table with raw and Tableau-facing directness roles.",
            "- `table_role_evidence.csv`: evidence edges behind the table role classification.",
            "- `glm_modifier_chain.csv`: one row per effective NeoForge GLM chain entry with target-table and payload-table analysis status.",
            "- `modifier_added_leaf_candidates.csv`: one row per resolved added payload leaf for recognized Stage 2 modifiers.",
            "- `target_table_modifier_summary.csv`: one row per target table summarizing modifier counts and added-item novelty/overlap.",
            "- `target_table_added_item_summary.csv`: one row per target table plus item_id summarizing modifier-added item paths.",
            "- `stage2_report.json`: Stage 2 chain counts, recognized/unsupported totals, and warnings.",
            f"- `{DEFAULT_STRUCTURE_LOOT_RESOLUTION_REPORT}`: exact-match, ambiguous-match, and no-match structure resolution counts plus stale-row warnings.",
            "- `item_classification.csv`: one row per classified item_id sourced from the canonical resolved_loot export.",
            "- `item_affinities.csv`: one row per item_id plus affinity for relational Tableau joins.",
            "- `classification_coverage.csv`: one row per distinct loot item_id with classified-or-missing coverage status.",
            "- `structure_set_entries.csv`: one row per effective structure_set entry with structure source metadata and dynamic mapping status.",
            "- `structure_set_loot_links.csv`: one row per final structure_set entry plus loot_table_id link after exact-match detection, ambiguous autoresolve, and manual no-match mapping.",
            "- `structure_set_loot_link_audit.csv`: audit trail for exact-match detections, ambiguous-match candidates, manual no-match mappings, and stale skipped rows.",
            "- `structure_set_base_item_presence.csv`: one row per structure_set entry plus item_id showing worst-case base item presence from linked Stage 1 loot tables.",
            "- `structure_set_effective_item_presence.csv`: one row per structure_set entry plus item_id including recognized Stage 2 modifier-added item presence.",
            "- `structure_set_profile_summary.csv`: one row per structure_set entry summarizing linked loot tables and base/effective unique item counts.",
            "- `scope_report.json`: allowed, excluded, and deferred top-level loot_table folder scope with warnings.",
            "- `manifest.json`: export counts for tables, pools, entries, references, and leaf rows.",
            "",
            "## Join Keys",
            "",
            "- `tables.csv.table_id` joins to `pools.csv.table_id` and `entries.csv.table_id`.",
            "- `pools.csv.pool_id` joins to `entries.csv.pool_id`.",
            "- `leaf_candidates.csv.root_table_id` joins back to named rows in `tables.csv`.",
            "- `glm_modifier_chain.csv.target_table_id` joins to `tables.csv.table_id` for target-table metadata.",
            "- `modifier_added_leaf_candidates.csv.target_table_id` joins to `tables.csv.table_id` for base target-table context.",
            "- `modifier_added_leaf_candidates.csv.item_id` joins to `item_classification.csv.item_id` for Stage 2 item traits.",
            "- `target_table_added_item_summary.csv.item_id` joins to `item_classification.csv.item_id` for Stage 2 added-item slicing.",
            "- `leaf_candidates.csv.item_id` joins to `item_classification.csv.item_id` for Stage 1.5 item traits.",
            "- `structure_set_loot_links.csv.loot_table_id` joins to `tables.csv.table_id` for loot-table metadata when the linked table is in Stage 1 scope.",
            "- `structure_set_base_item_presence.csv.item_id` joins to `item_classification.csv.item_id` for structure-level base item traits.",
            "- `structure_set_effective_item_presence.csv.item_id` joins to `item_classification.csv.item_id` for modifier-aware structure item traits.",
            "- `leaf_candidates.csv.root_table_id` joins to `table_role_summary.csv.table_id` for gameplay-source filtering.",
            "- `item_classification.csv.item_id` joins to `item_affinities.csv.item_id` for affinity slicing.",
            "- `classification_coverage.csv.item_id` joins to `item_classification.csv.item_id` for audit and completeness checks.",
            "- `table_role_summary.csv.table_id` joins to `table_role_evidence.csv.table_id` for provenance drill-down.",
            "",
            "## Allowed Folders",
            "",
            *(included_lines or ["- None"]),
            "",
            "## Excluded Folders",
            "",
            *(excluded_lines or ["- None"]),
            "",
            "## Deferred Stage 2 Folders",
            "",
            *(deferred_lines or ["- None"]),
            "",
            "## Warnings",
            "",
            *(warning_lines or ["- None"]),
            "",
            "## Notes",
            "",
            "- The scope config is always authoritative for Stage 1 allowed and deferred top-level loot_table directories.",
            "- Descendants of the configured ignore roots are skipped during auto-discovery and archive-root scans unless you include them explicitly with `--pack`.",
            "- Top-level `loot_table/inject/...` is treated as deferred Stage 2 and is intentionally omitted from Stage 1 outputs.",
            "- Nested paths like `loot_table/entities/inject/...` are still ordinary Stage 1 loot tables because the top-level directory is `entities`.",
            "- Inline tables use synthetic IDs in the form `inline:{entry_id}`.",
            "- `entries.csv.conditions_json` stores only conditions declared directly on entry objects. In many vanilla and modded tables, real conditions may still live at the pool level instead.",
            "- `entries.csv.quality` and `leaf_candidates.csv.leaf_quality` remain in the schema because they are valid loot fields even when blank in a given scope.",
            "- Raw `weight` values are not standardized across unrelated pools or tables, so compare normalized share fields when you need cross-table weighting context.",
            "- For the current scope, normalization is pool-based because the parsed entries are all top-level pool entries rather than nested composite siblings.",
            "- Missing entry `weight` values are normalized as Minecraft's implicit default of `1` for the pool-share calculations.",
            "- `entries.csv.pool_weight_share` is the entry's local share of its pool total and is the authoritative raw normalized-weight field for this scope.",
            "- `leaf_candidates.csv.root_entry_weight` and `leaf_candidates.csv.root_entry_quality` come from the first chain step only.",
            "- `leaf_candidates.csv.root_pool_weight_share` describes the normalized root-step context without restating an effective-weight denominator column.",
            "- `leaf_candidates.csv.path_pool_shares_json` lists the ordered local pool shares across the resolved path.",
            "- `leaf_candidates.csv.path_pool_share_product` is a relative path-choice share, not final drop probability.",
            "- `leaf_candidates.csv.leaf_weight` remains terminal-entry-only for backward compatibility; it is not a path weight or probability.",
            "- `leaf_candidates.csv.path_explicit_weights_json` lists only explicitly declared weights encountered along the resolved path.",
            "- `leaf_candidates.csv.path_explicit_weight_product` is the product of explicit path weights only; it is not normalized chance.",
            "- `set_count_min` and `set_count_max` only reflect explicit terminal `minecraft:set_count` functions.",
            "- `leaf_candidates.csv` is a path table. For source counts in Tableau, join it to `table_role_summary.csv` on `root_table_id = table_id` and filter `count_as_direct = true`.",
            "- For Tableau weighting work, prefer `entries.csv.pool_weight_share`, `leaf_candidates.csv.root_pool_weight_share`, and `leaf_candidates.csv.path_pool_share_product` over raw weight sums.",
            "- Stage 2 inventories NeoForge Global Loot Modifiers only. LootJS/KubeJS runtime mutations remain out of scope.",
            "- `glm_modifier_chain.csv` inventories every effective GLM in order, but detailed delta rows only exist for recognized inject/add-table semantics.",
            "- `modifier_added_leaf_candidates.csv` is a delta table, not a final runtime probability model. It shows what recognized modifiers add, not exact post-modifier odds.",
            "- Structure-set entry profiles are presence-based, not frequency-based. They are intended for structure-generation balancing rather than final loot EV.",
            "- Structure pairing is built from the final effective layered resource set after pack stacking, not from per-pack intermediate passes.",
            "- Exact-match links apply automatically from the conservative structure-side detector.",
            f"- Ambiguous-match candidates live in `{self.ambiguous_resolution_config_path}`. Review them there and set `autoresolve: true` only for the specific rows you want applied automatically.",
            f"- No-match manual resolutions live in `{self.manual_resolution_config_path}`. Open the file, research unresolved rows, fill in `structure_set_id` and `structure_id`, then set `status: mapped`.",
            "- No suppressions are part of this workflow. If an exact detected link is wrong, the matching logic should be corrected instead of overridden.",
            "- Automatic structure-to-loot mapping remains conservative: jigsaw start-pool traversal, pool aliases, reachable template pools, template NBT loot-table scans, explicit processor-list loot assignments, explicit structure-family candidate rules, and explicit curated loose table candidates.",
            "- Non-jigsaw structures may still land in ambiguous-match or no-match until you confirm them through the resolution YAMLs.",
            "- `structure_set_loot_links.csv` is the raw structure-to-loot-table layer, while `structure_set_effective_item_presence.csv` is the modifier-aware gameplay-facing structure item profile.",
            "- `resolved_loot_v*.csv` remains the canonical raw classification export, but its `affinities` field is a serialized list. Prefer `item_classification.csv` plus `item_affinities.csv` for Tableau.",
            "- `classification_coverage.csv` makes missing loot-item classifications explicit instead of silently dropping them.",
            "- `raw_role` keeps the conservative local-data provenance result; `effective_role` converts `unknown_directness` to `assumed_direct_for_tableau`.",
            "- `tables.csv.source_pack`, `tables.csv.resource_path`, and `tables.csv.is_override` identify the winning source behind each effective table row.",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _string_or_blank(value: Any) -> str:
        return value if isinstance(value, str) else ""


def export_loot_stack(
    *,
    scope_config_path: Path | str | None = DEFAULT_SCOPE_CONFIG,
    scope_override: dict[str, Any] | None = None,
    pack_order_manifest: Path | str | None = None,
    classification_csv_path: Path | str | None = None,
    ambiguous_resolution_config_path: Path | str = DEFAULT_AMBIGUOUS_STRUCTURE_RESOLUTION_CONFIG,
    manual_resolution_config_path: Path | str = DEFAULT_MANUAL_STRUCTURE_RESOLUTION_CONFIG,
    mods_root: Path | str = DEFAULT_MODS_ROOT,
    ignore_roots: list[Path | str] | None = None,
    archive_roots: list[Path | str] | None = None,
    explicit_packs: list[Path | str] | None = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    base_pack_root: Path | str = DEFAULT_BASE_PACK_ROOT,
    auto_discover_mod_dirs: bool = True,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        scope_settings = load_scope_settings(scope_config_path=scope_config_path, scope_override=scope_override)
        pack_order_ids, pack_order_source = load_pack_order_manifest(pack_order_manifest)
        if classification_csv_path is not None:
            resolved_classification_path = Path(classification_csv_path)
            if not resolved_classification_path.exists():
                raise FileNotFoundError(f"classification csv does not exist: {resolved_classification_path}")
        else:
            resolved_classification_path = find_latest_classification_csv(DEFAULT_CLASSIFICATION_SEARCH_ROOT)
    except Exception as exc:
        report = {
            "scope_config_source": str(scope_config_path) if scope_config_path is not None else None,
            "pack_order_source": str(pack_order_manifest) if pack_order_manifest is not None else None,
            "discovered_packs": [],
            "selected_packs": [],
            "effective_order": [],
            "duplicate_source_issues": [],
            "replacements": [],
            "overlap_groups": [],
            "resolved_overlaps": [],
            "fatal_errors": [str(exc)],
        }
        write_json(output_path / DEFAULT_PRECHECK_FILENAME, report)
        raise PrecheckFailed(str(exc))

    exporter = LootStackExporter(
        base_pack_root=Path(base_pack_root),
        mods_root=Path(mods_root),
        ignore_roots=[Path(path) for path in (ignore_roots or [DEFAULT_IGNORE_ROOT])],
        archive_roots=[Path(path) for path in (archive_roots or [])],
        explicit_packs=[Path(path) for path in (explicit_packs or [])],
        output_dir=output_path,
        scope_settings=scope_settings,
        pack_order_ids=pack_order_ids,
        pack_order_source=pack_order_source,
        auto_discover_mod_dirs=auto_discover_mod_dirs,
        classification_csv_path=resolved_classification_path,
        ambiguous_resolution_config_path=Path(ambiguous_resolution_config_path),
        manual_resolution_config_path=Path(manual_resolution_config_path),
    )
    return exporter.export()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = export_loot_stack(
            scope_config_path=args.scope_config,
            pack_order_manifest=args.pack_order_manifest,
            mods_root=args.mods_root,
            ignore_roots=args.ignore_root,
            archive_roots=args.archive_root,
            explicit_packs=args.pack,
            output_dir=args.output_dir,
            classification_csv_path=args.classification_csv,
            ambiguous_resolution_config_path=args.ambiguous_structure_resolution_config,
            manual_resolution_config_path=args.manual_structure_resolution_config,
        )
    except PrecheckFailed as exc:
        print(f"Precheck failed. Wrote {DEFAULT_PRECHECK_FILENAME} to {args.output_dir}")
        print(str(exc))
        return 1

    manifest = result["manifest"]
    print(f"Wrote loot stack export to {result['output_dir']}")
    print(f"Selected packs: {', '.join(manifest['selected_pack_ids'])}")
    print(
        "Counts: "
        f"{manifest['named_table_count']} named tables, "
        f"{manifest['inline_table_count']} inline tables, "
        f"{manifest['leaf_candidate_count']} leaf rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
