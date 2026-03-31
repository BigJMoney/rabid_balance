from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_PACK_ROOT = PROJECT_ROOT / "libs" / "neoforge-21.1.162_ref"
DEFAULT_MODS_ROOT = PROJECT_ROOT / "libs"
DEFAULT_IGNORE_ROOT = DEFAULT_MODS_ROOT / "ignore"
DEFAULT_SCOPE_CONFIG = PROJECT_ROOT / "configs" / "loot_scope.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "loot_docs" / "loot_stack_v1"
DEFAULT_PRECHECK_FILENAME = "precheck_report.json"
DIRECT_ASSIGNMENT_DIRS = ("worldgen/processor_list",)
DIRECT_ASSIGNMENT_KEYS = {"loot_table", "LootTable"}
STRUCTURE_EVIDENCE_TYPE = "structure_nbt"
LOOT_REF_EVIDENCE_TYPE = "loot_table_ref"
DATA_ASSIGNMENT_EVIDENCE_TYPE = "data_assignment_json"
LOOT_ID_SEARCH_PATTERN = re.compile(rb"[a-z_](?:[a-z0-9_.-]*):[a-z0-9_./-]+")

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
    "path_explicit_weights_json",
    "path_explicit_weight_product",
    "path_missing_weight_count",
    "path_has_implicit_default_weights",
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
    return parser.parse_args(argv)


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def join_types(values: list[str] | tuple[str, ...]) -> str:
    return "|".join(values)


def as_csv_value(value: Any) -> Any:
    return "" if value is None else value


def is_explicit_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
    if len(parts) >= 3 and parts[1] == "worldgen" and parts[2] == "processor_list":
        return "worldgen/processor_list"
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


def get_structure_source_object(resource_path: str) -> str:
    parts = split_resource_path(resource_path)
    if len(parts) < 4:
        return resource_path
    return PurePosixPath(*parts[2:]).with_suffix("").as_posix()


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

        self.tables: dict[str, TableRecord] = {}
        self.pools: dict[str, PoolRecord] = {}
        self.entries: dict[str, EntryRecord] = {}
        self.entry_id_by_key: dict[tuple[str, int, str], str] = {}
        self.entry_ids_by_pool: dict[str, list[str]] = defaultdict(list)
        self.named_table_ids: list[str] = []
        self.leaf_rows: list[dict[str, Any]] = []
        self.table_role_summary_rows: list[dict[str, Any]] = []
        self.table_role_evidence_rows: list[dict[str, Any]] = []
        self.raw_role_counts: Counter[str] = Counter()
        self.effective_role_counts: Counter[str] = Counter()

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
        self._build_leaf_rows()
        self._build_table_roles()
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
        missing_weight_count = sum(1 for step in chain if not is_explicit_number(step.get("weight")))
        path_weight_product: int | float | None = None
        if explicit_weights:
            product: int | float = 1
            for value in explicit_weights:
                product *= value
            path_weight_product = product
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
                "path_explicit_weights_json": json_cell(explicit_weights),
                "path_explicit_weight_product": as_csv_value(path_weight_product),
                "path_missing_weight_count": missing_weight_count,
                "path_has_implicit_default_weights": "true" if missing_weight_count > 0 else "false",
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
        return {
            "base_pack_root": str(self.base_pack_root),
            "scope_config_source": self.scope_settings.source,
            "pack_order_source": self.pack_order_source,
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

        write_json(self.output_dir / "scope_report.json", scope_report)
        write_json(self.output_dir / "manifest.json", manifest)
        write_json(self.output_dir / DEFAULT_PRECHECK_FILENAME, precheck_report)
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
            f"- Named table rows: {manifest['named_table_count']}",
            f"- Inline table rows: {manifest['inline_table_count']}",
            f"- Pool rows: {manifest['pool_count']}",
            f"- Entry rows: {manifest['entry_count']}",
            f"- Leaf candidate rows: {manifest['leaf_candidate_count']}",
            f"- Table role rows: {manifest['table_role_summary_count']}",
            f"- Table role evidence rows: {manifest['table_role_evidence_count']}",
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
            "- `entries.csv`: one row per entry with direct metadata, raw JSON, and reference targets.",
            "- `leaf_candidates.csv`: denormalized root-to-leaf paths for Tableau-style analysis.",
            "- `table_role_summary.csv`: one row per named effective table with raw and Tableau-facing directness roles.",
            "- `table_role_evidence.csv`: evidence edges behind the table role classification.",
            "- `scope_report.json`: allowed, excluded, and deferred top-level loot_table folder scope with warnings.",
            "- `manifest.json`: export counts for tables, pools, entries, references, and leaf rows.",
            "",
            "## Join Keys",
            "",
            "- `tables.csv.table_id` joins to `pools.csv.table_id` and `entries.csv.table_id`.",
            "- `pools.csv.pool_id` joins to `entries.csv.pool_id`.",
            "- `leaf_candidates.csv.root_table_id` joins back to named rows in `tables.csv`.",
            "- `leaf_candidates.csv.root_table_id` joins to `table_role_summary.csv.table_id` for gameplay-source filtering.",
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
            "- `leaf_candidates.csv.root_entry_weight` and `leaf_candidates.csv.root_entry_quality` come from the first chain step only.",
            "- `leaf_candidates.csv.leaf_weight` remains terminal-entry-only for backward compatibility; it is not a path weight or probability.",
            "- `leaf_candidates.csv.path_explicit_weights_json` lists only explicitly declared weights encountered along the resolved path.",
            "- `leaf_candidates.csv.path_explicit_weight_product` is the product of explicit path weights only; it is not normalized chance.",
            "- `leaf_candidates.csv.path_has_implicit_default_weights = true` means at least one chain step omitted `weight`, so the explicit product is incomplete as a chance-like proxy.",
            "- `set_count_min` and `set_count_max` only reflect explicit terminal `minecraft:set_count` functions.",
            "- `leaf_candidates.csv` is a path table. For source counts in Tableau, join it to `table_role_summary.csv` on `root_table_id = table_id` and filter `count_as_direct = true`.",
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
