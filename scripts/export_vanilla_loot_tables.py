from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "libs" / "neoforge-21.1.162_ref" / "data" / "minecraft" / "loot_table"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "loot_docs" / "vanilla_loot_v1"
DEFAULT_INCLUDED_DIRS = ("chests", "equipment", "pots", "spawners")
SOURCE_PACK = "base"

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
    "leaf_weight",
    "leaf_quality",
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

STRUCTURE_EVIDENCE_TYPE = "structure_nbt"
LOOT_REF_EVIDENCE_TYPE = "loot_table_ref"
DATA_ASSIGNMENT_EVIDENCE_TYPE = "data_assignment_json"
DIRECT_ASSIGNMENT_DIRS = ("worldgen/processor_list",)
DIRECT_ASSIGNMENT_KEYS = {"loot_table", "LootTable"}
SCOPED_LOOT_ID_PATTERN = re.compile(rb"minecraft:(?:chests|equipment|pots|spawners)/[a-z0-9_./-]+")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export scoped vanilla loot tables into normalized CSVs and leaf candidate rows."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help="Root minecraft loot_table directory to scan.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write CSV, JSON, and README outputs to.",
    )
    parser.add_argument(
        "--include-dirs",
        default=",".join(DEFAULT_INCLUDED_DIRS),
        help="Comma-separated list of top-level loot_table folders to include.",
    )
    return parser.parse_args(argv)


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def join_types(values: list[str] | tuple[str, ...]) -> str:
    return "|".join(values)


def as_csv_value(value: Any) -> Any:
    return "" if value is None else value


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


class LootTableExporter:
    def __init__(self, source_root: Path, included_dirs: tuple[str, ...], output_dir: Path) -> None:
        self.source_root = source_root
        self.included_dirs = included_dirs
        self.output_dir = output_dir

        self.tables: dict[str, TableRecord] = {}
        self.pools: dict[str, PoolRecord] = {}
        self.entries: dict[str, EntryRecord] = {}
        self.entry_id_by_key: dict[tuple[str, int, str], str] = {}
        self.named_table_ids: list[str] = []
        self.leaf_rows: list[dict[str, Any]] = []
        self.table_role_summary_rows: list[dict[str, Any]] = []
        self.table_role_evidence_rows: list[dict[str, Any]] = []
        self.raw_role_counts: Counter[str] = Counter()
        self.effective_role_counts: Counter[str] = Counter()

        self.named_reference_count = 0
        self.inline_reference_count = 0

    def export(self) -> dict[str, Any]:
        scope_report = self._discover_scope()
        self._parse_named_tables()
        self._validate_references()
        self._build_leaf_rows()
        self._build_table_roles()
        manifest = self._build_manifest()
        self._write_output_bundle(scope_report, manifest)
        return {
            "scope_report": scope_report,
            "manifest": manifest,
            "output_dir": str(self.output_dir),
        }

    def _discover_scope(self) -> dict[str, Any]:
        if not self.source_root.exists():
            raise ValueError(f"source root does not exist: {self.source_root}")

        all_dirs = sorted(path for path in self.source_root.iterdir() if path.is_dir())
        dir_counts = {
            path.name: sum(1 for _ in path.rglob("*.json"))
            for path in all_dirs
        }

        unknown_includes = sorted(set(self.included_dirs) - set(dir_counts))
        if unknown_includes:
            raise ValueError(f"unknown include dirs: {', '.join(unknown_includes)}")

        included = [
            {"name": path.name, "file_count": dir_counts[path.name]}
            for path in all_dirs
            if path.name in self.included_dirs
        ]
        excluded = [
            {"name": path.name, "file_count": dir_counts[path.name]}
            for path in all_dirs
            if path.name not in self.included_dirs
        ]

        return {
            "source_root": str(self.source_root),
            "included_dirs": included,
            "excluded_dirs": excluded,
            "included_table_total": sum(item["file_count"] for item in included),
            "excluded_table_total": sum(item["file_count"] for item in excluded),
        }

    def _parse_named_tables(self) -> None:
        for category in self.included_dirs:
            folder = self.source_root / category
            for json_path in sorted(folder.rglob("*.json")):
                rel_path = json_path.relative_to(self.source_root)
                table_id = f"minecraft:{rel_path.with_suffix('').as_posix()}"
                raw_table = ensure_dict(
                    json.loads(json_path.read_text(encoding="utf-8")),
                    f"table file {json_path}",
                )
                table = self._register_table(
                    table_id=table_id,
                    table_id_kind="named",
                    generated_from_entry_id="",
                    namespace="minecraft",
                    path=rel_path.with_suffix("").as_posix(),
                    category=category,
                    table_type=self._string_or_blank(raw_table.get("type")),
                    random_sequence=self._string_or_blank(raw_table.get("random_sequence")),
                    source_pack=SOURCE_PACK,
                    source_file=rel_path.as_posix(),
                    raw_table=raw_table,
                )
                self.named_table_ids.append(table.table_id)
                self._parse_table_contents(table)

    def _register_table(
        self,
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
                ref_table_id = value
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
            condition_types=collect_condition_types(conditions),
            function_types=collect_function_types(functions),
            conditions=conditions,
            functions=functions,
            raw_entry=entry,
        )
        self.entries[entry_id] = entry_record
        self.entry_id_by_key[(table.table_id, pool.pool_index, entry_path)] = entry_id

        if inline_table_id:
            inline_table_data = ensure_dict(entry.get("value"), f"{entry_id}.value")
            inline_table = self._register_table(
                table_id=inline_table_id,
                table_id_kind="inline",
                generated_from_entry_id=entry_id,
                namespace="",
                path="",
                category=table.category,
                table_type=self._string_or_blank(inline_table_data.get("type")),
                random_sequence=self._string_or_blank(inline_table_data.get("random_sequence")),
                source_pack=table.source_pack,
                source_file=table.source_file,
                raw_table=inline_table_data,
            )
            self._parse_table_contents(inline_table)

        for child_key in ("children", "entries"):
            children = entry.get(child_key)
            if not isinstance(children, list):
                continue
            for child_index, child in enumerate(children):
                child_path = f"{entry_path}.{child_key}.{child_index}"
                self._parse_entry(
                    table=table,
                    pool=pool,
                    raw_entry=child,
                    entry_path=child_path,
                )

    def _validate_references(self) -> None:
        missing_refs = sorted(
            {
                target
                for table in self.tables.values()
                for target in table.references
                if target not in self.tables
            }
        )
        if missing_refs:
            raise ValueError(f"missing referenced tables: {', '.join(missing_refs)}")

        graph = {
            table_id: sorted(set(table.references))
            for table_id, table in self.tables.items()
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(table_id: str, stack: list[str]) -> None:
            if table_id in visited:
                return
            if table_id in visiting:
                cycle = " -> ".join(stack + [table_id])
                raise ValueError(f"cyclic loot_table reference detected: {cycle}")
            visiting.add(table_id)
            for target in graph[table_id]:
                visit(target, stack + [table_id])
            visiting.remove(table_id)
            visited.add(table_id)

        for table_id in graph:
            visit(table_id, [])

    def _build_leaf_rows(self) -> None:
        for root_table_id in self.named_table_ids:
            root_table = self.tables[root_table_id]
            for pool_id in root_table.pool_ids:
                pool = self.pools[pool_id]
                root_entries = ensure_list(pool.raw_pool.get("entries"), f"{pool_id}.entries")
                for entry_index, _ in enumerate(root_entries):
                    root_entry_path = str(entry_index)
                    root_entry_id = self.entry_id_by_key[(root_table_id, pool.pool_index, root_entry_path)]
                    self._resolve_entry(
                        current_table_id=root_table_id,
                        current_pool_index=pool.pool_index,
                        current_entry_path=root_entry_path,
                        root_table_id=root_table_id,
                        root_pool_index=pool.pool_index,
                        root_entry_id=root_entry_id,
                        chain=[],
                        path_condition_types=set(),
                        path_function_types=set(),
                        table_stack=[root_table_id],
                    )

    def _resolve_entry(
        self,
        current_table_id: str,
        current_pool_index: int,
        current_entry_path: str,
        root_table_id: str,
        root_pool_index: int,
        root_entry_id: str,
        chain: list[dict[str, Any]],
        path_condition_types: set[str],
        path_function_types: set[str],
        table_stack: list[str],
    ) -> None:
        pool_id = f"{current_table_id}#pool:{current_pool_index}"
        pool = self.pools[pool_id]
        entry_id = self.entry_id_by_key[(current_table_id, current_pool_index, current_entry_path)]
        entry = self.entries[entry_id]

        current_condition_types = set(path_condition_types)
        current_condition_types.update(pool.condition_types)
        current_condition_types.update(entry.condition_types)

        current_function_types = set(path_function_types)
        current_function_types.update(entry.function_types)

        current_chain = list(chain)
        current_chain.append(self._build_chain_step(pool, entry))

        if entry.entry_type in {"minecraft:item", "minecraft:empty"}:
            self._append_leaf_row(
                root_table_id=root_table_id,
                root_pool_index=root_pool_index,
                root_entry_id=root_entry_id,
                leaf_table_id=current_table_id,
                leaf_entry=entry,
                chain=current_chain,
                path_condition_types=current_condition_types,
                path_function_types=current_function_types,
                unresolved_reason="",
            )
            return

        if entry.entry_type == "minecraft:loot_table":
            target_table_id = entry.inline_table_id or entry.ref_table_id
            if not target_table_id:
                self._append_leaf_row(
                    root_table_id=root_table_id,
                    root_pool_index=root_pool_index,
                    root_entry_id=root_entry_id,
                    leaf_table_id=current_table_id,
                    leaf_entry=entry,
                    chain=current_chain,
                    path_condition_types=current_condition_types,
                    path_function_types=current_function_types,
                    unresolved_reason="missing_loot_table_target",
                )
                return

            if target_table_id in table_stack:
                self._append_leaf_row(
                    root_table_id=root_table_id,
                    root_pool_index=root_pool_index,
                    root_entry_id=root_entry_id,
                    leaf_table_id=current_table_id,
                    leaf_entry=entry,
                    chain=current_chain,
                    path_condition_types=current_condition_types,
                    path_function_types=current_function_types,
                    unresolved_reason="cycle_detected",
                )
                return

            target_table = self.tables[target_table_id]
            for target_pool_id in target_table.pool_ids:
                target_pool = self.pools[target_pool_id]
                target_entries = ensure_list(target_pool.raw_pool.get("entries"), f"{target_pool_id}.entries")
                for target_entry_index, _ in enumerate(target_entries):
                    self._resolve_entry(
                        current_table_id=target_table_id,
                        current_pool_index=target_pool.pool_index,
                        current_entry_path=str(target_entry_index),
                        root_table_id=root_table_id,
                        root_pool_index=root_pool_index,
                        root_entry_id=root_entry_id,
                        chain=current_chain,
                        path_condition_types=current_condition_types,
                        path_function_types=current_function_types,
                        table_stack=table_stack + [target_table_id],
                    )
            return

        raw_entry = entry.raw_entry
        for child_key in ("children", "entries"):
            children = raw_entry.get(child_key)
            if not isinstance(children, list):
                continue
            for child_index, _ in enumerate(children):
                self._resolve_entry(
                    current_table_id=current_table_id,
                    current_pool_index=current_pool_index,
                    current_entry_path=f"{current_entry_path}.{child_key}.{child_index}",
                    root_table_id=root_table_id,
                    root_pool_index=root_pool_index,
                    root_entry_id=root_entry_id,
                    chain=current_chain,
                    path_condition_types=current_condition_types,
                    path_function_types=current_function_types,
                    table_stack=table_stack,
                )
            return

        self._append_leaf_row(
            root_table_id=root_table_id,
            root_pool_index=root_pool_index,
            root_entry_id=root_entry_id,
            leaf_table_id=current_table_id,
            leaf_entry=entry,
            chain=current_chain,
            path_condition_types=current_condition_types,
            path_function_types=current_function_types,
            unresolved_reason=f"unsupported_entry_type:{entry.entry_type or 'missing'}",
        )

    def _append_leaf_row(
        self,
        root_table_id: str,
        root_pool_index: int,
        root_entry_id: str,
        leaf_table_id: str,
        leaf_entry: EntryRecord,
        chain: list[dict[str, Any]],
        path_condition_types: set[str],
        path_function_types: set[str],
        unresolved_reason: str,
    ) -> None:
        root_table = self.tables[root_table_id]
        set_count_min, set_count_max = extract_set_count_range(leaf_entry.functions)
        self.leaf_rows.append(
            {
                "root_table_id": root_table_id,
                "root_category": root_table.category,
                "root_table_type": root_table.table_type,
                "root_pool_index": root_pool_index,
                "root_entry_id": root_entry_id,
                "leaf_table_id": leaf_table_id,
                "leaf_entry_id": leaf_entry.entry_id,
                "leaf_kind": leaf_entry.entry_type,
                "item_id": leaf_entry.name if leaf_entry.entry_type == "minecraft:item" else "",
                "chain_depth": len(chain),
                "selection_chain_json": json_cell(chain),
                "path_condition_types": join_types(sorted(path_condition_types)),
                "path_function_types": join_types(sorted(path_function_types)),
                "leaf_weight": as_csv_value(leaf_entry.weight),
                "leaf_quality": as_csv_value(leaf_entry.quality),
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
                    source_path=str((self.source_root / source_table.source_file).resolve()),
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

    def _scan_structure_evidence(self) -> list[RoleEvidenceRecord]:
        named_table_set = set(self.named_table_ids)
        structure_root = self.source_root.parent / "structure"
        if not structure_root.exists():
            return []

        evidence_rows: list[RoleEvidenceRecord] = []
        for nbt_path in sorted(structure_root.rglob("*.nbt")):
            search_bytes = self._read_search_bytes(nbt_path)
            matched_ids = {
                match.decode("utf-8")
                for match in SCOPED_LOOT_ID_PATTERN.findall(search_bytes)
            }
            for table_id in sorted(matched_ids & named_table_set):
                evidence_rows.append(
                    RoleEvidenceRecord(
                        table_id=table_id,
                        evidence_type=STRUCTURE_EVIDENCE_TYPE,
                        source_path=str(nbt_path.resolve()),
                        source_object=nbt_path.relative_to(structure_root).with_suffix("").as_posix(),
                        target_table_id=table_id,
                    )
                )
        return evidence_rows

    def _scan_direct_assignment_evidence(self) -> list[RoleEvidenceRecord]:
        named_table_set = set(self.named_table_ids)
        data_root = self.source_root.parent
        evidence_rows: list[RoleEvidenceRecord] = []

        for relative_dir in DIRECT_ASSIGNMENT_DIRS:
            scan_root = data_root / relative_dir
            if not scan_root.exists():
                continue
            for json_path in sorted(scan_root.rglob("*.json")):
                raw_json = json.loads(json_path.read_text(encoding="utf-8"))
                for table_id, pointer in self._find_direct_assignment_matches(raw_json):
                    if table_id not in named_table_set:
                        continue
                    evidence_rows.append(
                        RoleEvidenceRecord(
                            table_id=table_id,
                            evidence_type=DATA_ASSIGNMENT_EVIDENCE_TYPE,
                            source_path=str(json_path.resolve()),
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

    @staticmethod
    def _read_search_bytes(path: Path) -> bytes:
        raw_bytes = path.read_bytes()
        if raw_bytes.startswith(b"\x1f\x8b"):
            try:
                return gzip.decompress(raw_bytes)
            except OSError:
                return raw_bytes
        return raw_bytes

    def _build_manifest(self) -> dict[str, Any]:
        named_tables = [table for table in self.tables.values() if table.table_id_kind == "named"]
        inline_tables = [table for table in self.tables.values() if table.table_id_kind == "inline"]
        return {
            "source_root": str(self.source_root),
            "output_dir": str(self.output_dir),
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
            "raw_role_counts": dict(sorted(self.raw_role_counts.items())),
            "effective_role_counts": dict(sorted(self.effective_role_counts.items())),
        }

    def _write_output_bundle(self, scope_report: dict[str, Any], manifest: dict[str, Any]) -> None:
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

        (self.output_dir / "scope_report.json").write_text(
            json.dumps(scope_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.output_dir / "README.md").write_text(
            self._build_readme(scope_report, manifest),
            encoding="utf-8",
        )

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _build_readme(self, scope_report: dict[str, Any], manifest: dict[str, Any]) -> str:
        included_lines = [
            f"- `{item['name']}`: {item['file_count']} tables"
            for item in scope_report["included_dirs"]
        ]
        excluded_lines = [
            f"- `{item['name']}`: {item['file_count']} tables"
            for item in scope_report["excluded_dirs"]
        ]

        lines = [
            "# Vanilla Loot V1",
            "",
            "Scoped vanilla loot-table export for analysis and later round-tripping.",
            "",
            "## Summary",
            "",
            f"- Source root: `{scope_report['source_root']}`",
            f"- Included table total: {scope_report['included_table_total']}",
            f"- Excluded table total: {scope_report['excluded_table_total']}",
            f"- Named table rows: {manifest['named_table_count']}",
            f"- Inline table rows: {manifest['inline_table_count']}",
            f"- Pool rows: {manifest['pool_count']}",
            f"- Entry rows: {manifest['entry_count']}",
            f"- Leaf candidate rows: {manifest['leaf_candidate_count']}",
            f"- Table role rows: {manifest['table_role_summary_count']}",
            f"- Table role evidence rows: {manifest['table_role_evidence_count']}",
            "",
            "## Files",
            "",
            "- `tables.csv`: one row per named table plus synthetic inline table.",
            "- `pools.csv`: one row per pool with roll metadata and pool-level conditions.",
            "- `entries.csv`: one row per entry with direct metadata, raw JSON, and reference targets.",
            "- `leaf_candidates.csv`: denormalized root-to-leaf paths for Tableau-style analysis.",
            "- `table_role_summary.csv`: one row per named scoped table with raw and Tableau-facing directness roles.",
            "- `table_role_evidence.csv`: evidence edges behind the table role classification.",
            "- `scope_report.json`: included and excluded folder scope with file counts.",
            "- `manifest.json`: export counts for tables, pools, entries, references, and leaf rows.",
            "",
            "## Join Keys",
            "",
            "- `tables.csv.table_id` joins to `pools.csv.table_id` and `entries.csv.table_id`.",
            "- `pools.csv.pool_id` joins to `entries.csv.pool_id`.",
            "- `leaf_candidates.csv.root_table_id` joins back to named rows in `tables.csv`.",
            "- `leaf_candidates.csv.leaf_table_id` joins back to terminal rows in `tables.csv`.",
            "- `leaf_candidates.csv.root_table_id` joins to `table_role_summary.csv.table_id` for gameplay-source filtering.",
            "- `table_role_summary.csv.table_id` joins to `table_role_evidence.csv.table_id` for provenance drill-down.",
            "",
            "## Included Folders",
            "",
            *included_lines,
            "",
            "## Excluded Folders",
            "",
            *excluded_lines,
            "",
            "## Notes",
            "",
            "- Inline tables use synthetic IDs in the form `inline:{entry_id}`.",
            "- Inline tables can have blank `table_type` or `random_sequence` when the embedded object omits them.",
            "- `entries.csv.conditions_json` stores only conditions declared directly on entry objects. In this scoped vanilla export, all entry rows are `[]` because the observed conditions are pool-level instead.",
            "- `entries.csv.quality` and `leaf_candidates.csv.leaf_quality` remain in the schema because they are valid loot fields, but they are blank for this scoped vanilla export because no included entry declares `quality`.",
            "- `set_count_min` and `set_count_max` only reflect explicit terminal `minecraft:set_count` functions.",
            "- This export preserves roll, weight, condition, and function structure but does not compute expected value.",
            "- For Tableau source counts, join `leaf_candidates.csv` to `table_role_summary.csv` and filter `count_as_direct = true`.",
            "- `raw_role` keeps the conservative local-data provenance result; `effective_role` converts `unknown_directness` to `assumed_direct_for_tableau`.",
            "- Unknown tables are counted as direct in Tableau because missing local data-side references are not treated as proof of helper-only status.",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _string_or_blank(value: Any) -> str:
        return value if isinstance(value, str) else ""


def export_loot_tables(
    source_root: Path | str = DEFAULT_SOURCE_ROOT,
    included_dirs: tuple[str, ...] = DEFAULT_INCLUDED_DIRS,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    exporter = LootTableExporter(
        source_root=Path(source_root),
        included_dirs=tuple(included_dirs),
        output_dir=Path(output_dir),
    )
    return exporter.export()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    include_dirs = tuple(part.strip() for part in args.include_dirs.split(",") if part.strip())
    result = export_loot_tables(
        source_root=args.source_root,
        included_dirs=include_dirs,
        output_dir=args.output_dir,
    )
    scope = result["scope_report"]
    manifest = result["manifest"]
    print(f"Wrote scoped loot export to {result['output_dir']}")
    print(f"Included folders: {', '.join(item['name'] for item in scope['included_dirs'])}")
    print(f"Excluded folders: {', '.join(item['name'] for item in scope['excluded_dirs'])}")
    print(
        "Counts: "
        f"{manifest['named_table_count']} named tables, "
        f"{manifest['inline_table_count']} inline tables, "
        f"{manifest['leaf_candidate_count']} leaf rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
