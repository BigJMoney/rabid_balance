from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBS_ROOT = PROJECT_ROOT / "libs"
ILLAGER_DIR = LIBS_ROOT / "IllagerInvasion-v21.1.6-NeoForge"
ILLAGER_ARCHIVE = LIBS_ROOT / "IllagerInvasion-v21.1.6-NeoForge.zip"
SOPHISTICATED_DIR = LIBS_ROOT / "sophisticatedbackpacks-3.25.34.1581"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import export_loot_stack as exporter


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_mod_pack(root: Path, pack_id: str, resources: dict[str, str]) -> None:
    (root / "META-INF").mkdir(parents=True, exist_ok=True)
    (root / "META-INF" / "neoforge.mods.toml").write_text(
        f'[[mods]]\nmodId = "{pack_id}"\n',
        encoding="utf-8",
    )
    for relative_path, content in resources.items():
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


class ExportLootStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.tempdir.name) / "default_stack"
        exporter.export_loot_stack(output_dir=cls.output_dir)

        cls.precheck = json.loads((cls.output_dir / "precheck_report.json").read_text(encoding="utf-8"))
        cls.scope_report = json.loads((cls.output_dir / "scope_report.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((cls.output_dir / "manifest.json").read_text(encoding="utf-8"))
        cls.tables = read_csv_rows(cls.output_dir / "tables.csv")
        cls.evidence = read_csv_rows(cls.output_dir / "table_role_evidence.csv")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def test_default_stack_discovers_mod_dirs_and_defers_inject(self) -> None:
        self.assertEqual(self.manifest["selected_pack_ids"], ["base", "illagerinvasion", "sophisticatedbackpacks"])
        deferred = {item["name"]: item["file_count"] for item in self.scope_report["deferred_dirs"]}
        self.assertEqual(deferred, {"inject": 9})
        self.assertEqual(self.scope_report["warnings"], [])
        self.assertGreaterEqual(
            sum(1 for row in self.tables if row["table_id"].startswith("illagerinvasion:")),
            7,
        )
        self.assertFalse(any(row["table_id"].startswith("sophisticatedbackpacks:inject/") for row in self.tables))

    def test_illager_structure_override_feeds_provenance(self) -> None:
        matching_rows = [
            row
            for row in self.evidence
            if row["evidence_type"] == "structure_nbt"
            and "IllagerInvasion-v21.1.6-NeoForge" in row["source_path"]
            and "woodland_mansion" in row["source_path"]
        ]
        self.assertTrue(matching_rows)

    def test_explicit_archive_replaces_auto_discovered_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "archive_replace"
            exporter.export_loot_stack(
                output_dir=output_dir,
                explicit_packs=[ILLAGER_ARCHIVE],
            )
            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            illager_row = next(row for row in precheck["selected_packs"] if row["pack_id"] == "illagerinvasion")
            self.assertEqual(illager_row["kind"], "archive")
            self.assertEqual(Path(illager_row["path"]), ILLAGER_ARCHIVE)

    def test_archive_root_discovers_archives(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "archive_root"
            result = exporter.export_loot_stack(
                output_dir=output_dir,
                archive_roots=[LIBS_ROOT],
                auto_discover_mod_dirs=False,
                mods_root=PROJECT_ROOT / "__unused_mods_root__",
            )
            self.assertEqual(result["manifest"]["selected_pack_ids"], ["base", "illagerinvasion"])
            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            illager_row = next(row for row in precheck["selected_packs"] if row["pack_id"] == "illagerinvasion")
            self.assertEqual(illager_row["kind"], "archive")

    def test_precheck_without_manifest_reports_all_overlaps(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            shared_a = json.dumps(
                {
                    "type": "minecraft:chest",
                    "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:stick"}]}],
                }
            )
            shared_b = json.dumps(
                {
                    "type": "minecraft:chest",
                    "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:diamond"}]}],
                }
            )
            write_mod_pack(
                mods_root / "mod_a",
                "moda",
                {
                    "data/shared/loot_table/chests/common.json": shared_a,
                    "data/shared/loot_table/chests/second.json": shared_a,
                },
            )
            write_mod_pack(
                mods_root / "mod_b",
                "modb",
                {
                    "data/shared/loot_table/chests/common.json": shared_b,
                    "data/shared/loot_table/chests/second.json": shared_b,
                },
            )

            with self.assertRaises(exporter.PrecheckFailed):
                exporter.export_loot_stack(
                    output_dir=output_dir,
                    mods_root=mods_root,
                    archive_roots=[],
                    explicit_packs=[],
                )

            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertEqual(len(precheck["overlap_groups"]), 2)
            self.assertEqual(len(precheck["fatal_errors"]), 2)
            self.assertTrue(all("mod-vs-mod same-file overlap" in message for message in precheck["fatal_errors"]))

    def test_precheck_with_manifest_resolves_overlaps(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            manifest_path = Path(tempdir) / "pack_order.json"
            manifest_path.write_text(json.dumps(["moda", "modb"]), encoding="utf-8")

            shared_a = json.dumps(
                {
                    "type": "minecraft:chest",
                    "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:stick"}]}],
                }
            )
            shared_b = json.dumps(
                {
                    "type": "minecraft:chest",
                    "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:diamond"}]}],
                }
            )
            write_mod_pack(
                mods_root / "mod_a",
                "moda",
                {
                    "data/shared/loot_table/chests/common.json": shared_a,
                    "data/shared/loot_table/chests/second.json": shared_a,
                },
            )
            write_mod_pack(
                mods_root / "mod_b",
                "modb",
                {
                    "data/shared/loot_table/chests/common.json": shared_b,
                    "data/shared/loot_table/chests/second.json": shared_b,
                },
            )

            exporter.export_loot_stack(
                output_dir=output_dir,
                mods_root=mods_root,
                archive_roots=[],
                explicit_packs=[],
                pack_order_manifest=manifest_path,
            )

            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertEqual(precheck["effective_order"], ["base", "moda", "modb"])
            self.assertEqual(len(precheck["resolved_overlaps"]), 2)
            self.assertTrue(all(row["winner_pack_id"] == "modb" for row in precheck["resolved_overlaps"]))

            tables = read_csv_rows(output_dir / "tables.csv")
            common_row = next(row for row in tables if row["table_id"] == "shared:chests/common")
            self.assertEqual(common_row["source_pack"], "modb")

    def test_unknown_manifest_pack_id_is_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "out"
            manifest_path = Path(tempdir) / "pack_order.json"
            manifest_path.write_text(json.dumps(["not_a_real_pack"]), encoding="utf-8")

            with self.assertRaises(exporter.PrecheckFailed):
                exporter.export_loot_stack(
                    output_dir=output_dir,
                    auto_discover_mod_dirs=False,
                    mods_root=PROJECT_ROOT / "__unused_mods_root__",
                    archive_roots=[],
                    explicit_packs=[SOPHISTICATED_DIR],
                    pack_order_manifest=manifest_path,
                )

            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertTrue(any("unknown pack ids" in message for message in precheck["fatal_errors"]))

    def test_ignore_root_skips_auto_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            ignore_root = mods_root / "ignore"
            output_dir = Path(tempdir) / "out"
            simple_table = json.dumps(
                {
                    "type": "minecraft:chest",
                    "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:stick"}]}],
                }
            )
            write_mod_pack(
                mods_root / "visible_mod",
                "visiblemod",
                {"data/visible/loot_table/chests/example.json": simple_table},
            )
            write_mod_pack(
                ignore_root / "hidden_mod",
                "hiddenmod",
                {"data/hidden/loot_table/chests/example.json": simple_table},
            )

            result = exporter.export_loot_stack(
                output_dir=output_dir,
                mods_root=mods_root,
                ignore_roots=[ignore_root],
                archive_roots=[],
                explicit_packs=[],
            )

            self.assertEqual(result["manifest"]["selected_pack_ids"], ["base", "visiblemod"])
            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertIn(str(ignore_root), precheck["ignored_sources"])


if __name__ == "__main__":
    unittest.main()
