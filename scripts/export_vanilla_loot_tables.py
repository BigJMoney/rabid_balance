from __future__ import annotations

import argparse
from pathlib import Path

import export_loot_stack as stack_exporter


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "libs" / "neoforge-21.1.162_ref" / "data" / "minecraft" / "loot_table"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "loot_docs" / "vanilla_loot_v1"
DEFAULT_INCLUDED_DIRS = ("chests", "equipment", "pots", "spawners")


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
    parser.add_argument(
        "--classification-csv",
        type=Path,
        default=None,
        help="Optional resolved_loot_v*.csv classification source for Stage 1.5 tables.",
    )
    parser.add_argument(
        "--refresh-all-structure-resolution-maps",
        action="store_true",
        help=(
            "Destructively rebuild both structure resolution YAMLs from current export results only. "
            "This drops existing ambiguous/manual entries before writing fresh rows."
        ),
    )
    return parser.parse_args(argv)


def export_loot_tables(
    source_root: Path | str = DEFAULT_SOURCE_ROOT,
    included_dirs: tuple[str, ...] = DEFAULT_INCLUDED_DIRS,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    classification_csv_path: Path | str | None = None,
    ambiguous_resolution_config_path: Path | str = stack_exporter.DEFAULT_AMBIGUOUS_STRUCTURE_RESOLUTION_CONFIG,
    manual_resolution_config_path: Path | str = stack_exporter.DEFAULT_MANUAL_STRUCTURE_RESOLUTION_CONFIG,
    refresh_all_structure_resolution_maps: bool = False,
) -> dict[str, object]:
    source_root_path = Path(source_root)
    if source_root_path.name != "loot_table":
        raise ValueError(f"expected source_root to end with loot_table, got {source_root_path}")
    base_pack_root = source_root_path.parents[2]
    scope_override = {
        "allowed_loot_dirs": list(included_dirs),
        "deferred_loot_dirs": ["inject"],
    }
    return stack_exporter.export_loot_stack(
        base_pack_root=base_pack_root,
        output_dir=output_dir,
        scope_override=scope_override,
        auto_discover_mod_dirs=False,
        mods_root=PROJECT_ROOT / "__no_mods__",
        archive_roots=[],
        explicit_packs=[],
        classification_csv_path=classification_csv_path,
        ambiguous_resolution_config_path=ambiguous_resolution_config_path,
        manual_resolution_config_path=manual_resolution_config_path,
        refresh_all_structure_resolution_maps=refresh_all_structure_resolution_maps,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    include_dirs = tuple(part.strip() for part in args.include_dirs.split(",") if part.strip())
    result = export_loot_tables(
        source_root=args.source_root,
        included_dirs=include_dirs,
        output_dir=args.output_dir,
        classification_csv_path=args.classification_csv,
        refresh_all_structure_resolution_maps=args.refresh_all_structure_resolution_maps,
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
