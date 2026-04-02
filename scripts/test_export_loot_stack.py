from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBS_ROOT = PROJECT_ROOT / "libs"
ILLAGER_DIR = LIBS_ROOT / "IllagerInvasion-v21.1.6-NeoForge"
ILLAGER_ARCHIVE = LIBS_ROOT / "IllagerInvasion-v21.1.6-NeoForge.zip"
SOPHISTICATED_DIR = LIBS_ROOT / "sophisticatedbackpacks-3.25.34.1581"
FIXTURES_DIR = PROJECT_ROOT / "scripts" / "test_fixtures"
AMBIGUOUS_FIXTURE_PATH = FIXTURES_DIR / "structure_loot_ambiguous_resolution_map.yaml"
MANUAL_FIXTURE_PATH = FIXTURES_DIR / "structure_loot_manual_resolution_map.yaml"
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


def copy_resolution_map_fixtures(destination_root: Path) -> tuple[Path, Path]:
    destination_root.mkdir(parents=True, exist_ok=True)
    ambiguous_path = destination_root / "structure_loot_ambiguous_resolution_map.yaml"
    manual_path = destination_root / "structure_loot_manual_resolution_map.yaml"
    ambiguous_path.write_text(AMBIGUOUS_FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    manual_path.write_text(MANUAL_FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return ambiguous_path, manual_path


def export_with_temp_resolution_maps(output_dir: Path, **kwargs) -> dict[str, object]:
    ambiguous_path = kwargs.pop("ambiguous_resolution_config_path", None)
    manual_path = kwargs.pop("manual_resolution_config_path", None)
    if ambiguous_path is None or manual_path is None:
        default_ambiguous_path, default_manual_path = copy_resolution_map_fixtures(output_dir.parent)
        ambiguous_path = ambiguous_path or default_ambiguous_path
        manual_path = manual_path or default_manual_path
    return exporter.export_loot_stack(
        output_dir=output_dir,
        ambiguous_resolution_config_path=Path(ambiguous_path),
        manual_resolution_config_path=Path(manual_path),
        **kwargs,
    )


class ExportLootStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.tempdir.name) / "default_stack"
        cls.ambiguous_resolution_path, cls.manual_resolution_path = copy_resolution_map_fixtures(Path(cls.tempdir.name))
        exporter.export_loot_stack(
            output_dir=cls.output_dir,
            ambiguous_resolution_config_path=cls.ambiguous_resolution_path,
            manual_resolution_config_path=cls.manual_resolution_path,
        )

        cls.precheck = json.loads((cls.output_dir / "precheck_report.json").read_text(encoding="utf-8"))
        cls.scope_report = json.loads((cls.output_dir / "scope_report.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((cls.output_dir / "manifest.json").read_text(encoding="utf-8"))
        cls.structure_resolution_report = json.loads(
            (cls.output_dir / "structure_loot_resolution_report.json").read_text(encoding="utf-8")
        )
        cls.ambiguous_resolution_text = cls.ambiguous_resolution_path.read_text(encoding="utf-8")
        cls.manual_resolution_text = cls.manual_resolution_path.read_text(encoding="utf-8")
        cls.ambiguous_resolution_map = yaml.safe_load(cls.ambiguous_resolution_text)
        cls.manual_resolution_map = yaml.safe_load(cls.manual_resolution_text)
        cls.tables = read_csv_rows(cls.output_dir / "tables.csv")
        cls.pools = read_csv_rows(cls.output_dir / "pools.csv")
        cls.entries = read_csv_rows(cls.output_dir / "entries.csv")
        cls.leaf_rows = read_csv_rows(cls.output_dir / "leaf_candidates.csv")
        cls.evidence = read_csv_rows(cls.output_dir / "table_role_evidence.csv")
        cls.glm_chain = read_csv_rows(cls.output_dir / "glm_modifier_chain.csv")
        cls.modifier_added_leaf_rows = read_csv_rows(cls.output_dir / "modifier_added_leaf_candidates.csv")
        cls.target_table_modifier_summary = read_csv_rows(cls.output_dir / "target_table_modifier_summary.csv")
        cls.target_table_added_item_summary = read_csv_rows(cls.output_dir / "target_table_added_item_summary.csv")
        cls.stage2_report = json.loads((cls.output_dir / "stage2_report.json").read_text(encoding="utf-8"))
        cls.item_classification = read_csv_rows(cls.output_dir / "item_classification.csv")
        cls.item_affinities = read_csv_rows(cls.output_dir / "item_affinities.csv")
        cls.classification_coverage = read_csv_rows(cls.output_dir / "classification_coverage.csv")
        cls.structure_set_entries = read_csv_rows(cls.output_dir / "structure_set_entries.csv")
        cls.structure_set_loot_links = read_csv_rows(cls.output_dir / "structure_set_loot_links.csv")
        cls.structure_set_loot_link_audit = read_csv_rows(cls.output_dir / "structure_set_loot_link_audit.csv")
        cls.structure_set_base_item_presence = read_csv_rows(cls.output_dir / "structure_set_base_item_presence.csv")
        cls.structure_set_effective_item_presence = read_csv_rows(cls.output_dir / "structure_set_effective_item_presence.csv")
        cls.structure_set_profile_summary = read_csv_rows(cls.output_dir / "structure_set_profile_summary.csv")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def test_default_stack_discovers_mod_dirs_and_defers_inject(self) -> None:
        expected_pack_ids = ["base"]
        if ILLAGER_DIR.exists():
            expected_pack_ids.append("illagerinvasion")
        if SOPHISTICATED_DIR.exists():
            expected_pack_ids.append("sophisticatedbackpacks")
        self.assertEqual(self.manifest["selected_pack_ids"], expected_pack_ids)
        deferred = {item["name"]: item["file_count"] for item in self.scope_report["deferred_dirs"]}
        if SOPHISTICATED_DIR.exists():
            self.assertEqual(deferred, {"inject": 9})
        else:
            self.assertEqual(deferred, {})
        self.assertEqual(self.scope_report["warnings"], [])
        self.assertGreaterEqual(
            sum(1 for row in self.tables if row["table_id"].startswith("illagerinvasion:")),
            7 if ILLAGER_DIR.exists() else 0,
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

    def test_illager_leaf_rows_have_path_weight_fields(self) -> None:
        row = next(row for row in self.leaf_rows if row["root_table_id"] == "illagerinvasion:chests/illager_fort_ground")
        self.assertIn("root_entry_weight", row)
        self.assertIn("root_pool_weight_share", row)
        self.assertIn("path_pool_shares_json", row)
        self.assertIn("path_explicit_weights_json", row)

    def test_default_stack_raw_tables_include_normalized_weight_fields(self) -> None:
        pool_row = next(iter(self.pools))
        entry_row = next(iter(self.entries))
        self.assertNotIn("pool_defaulted_weight_entry_count", pool_row)
        self.assertNotIn("weight_was_defaulted", entry_row)
        self.assertIn("pool_weight_share", entry_row)

    def test_default_stack_writes_stage15_classification_tables(self) -> None:
        self.assertTrue(self.item_classification)
        self.assertTrue(self.classification_coverage)
        arrow = next(row for row in self.item_classification if row["item_id"] == "minecraft:arrow")
        self.assertEqual(arrow["function"], "weapon")
        self.assertEqual(arrow["classification_version"], "10")

    def test_default_stack_writes_structure_set_tables(self) -> None:
        expected_entry_count = 34 + (5 if ILLAGER_DIR.exists() else 0)
        self.assertEqual(len(self.structure_set_entries), expected_entry_count)
        self.assertEqual(len(self.structure_set_profile_summary), expected_entry_count)
        self.assertTrue(self.structure_set_loot_links)
        self.assertTrue(self.structure_set_loot_link_audit)
        self.assertTrue(self.structure_set_base_item_presence)
        self.assertTrue(self.structure_set_effective_item_presence)

    def test_default_stack_structure_set_entries_include_illager_structures(self) -> None:
        if not ILLAGER_DIR.exists():
            self.skipTest("Illager directory fixture is not present in libs")
        illager_rows = [row for row in self.structure_set_entries if row["structure_set_id"].startswith("illagerinvasion:")]
        self.assertEqual(len(illager_rows), 5)
        self.assertTrue(any(row["structure_set_id"] == "illagerinvasion:illager_fort" for row in illager_rows))

    def test_default_stack_dynamic_structure_mapping_detects_trial_chambers_and_illager(self) -> None:
        trial_row = next(row for row in self.structure_set_entries if row["structure_set_id"] == "minecraft:trial_chambers")
        self.assertEqual(trial_row["dynamic_mapping_status"], "detected_links_found")
        trial_links = [
            row
            for row in self.structure_set_loot_links
            if row["structure_set_id"] == "minecraft:trial_chambers"
        ]
        self.assertTrue(any(row["loot_table_id"] == "minecraft:chests/trial_chambers/reward" for row in trial_links))
        if ILLAGER_DIR.exists():
            illager_row = next(row for row in self.structure_set_entries if row["structure_set_id"] == "illagerinvasion:illager_fort")
            self.assertEqual(illager_row["dynamic_mapping_status"], "detected_links_found")
            self.assertTrue(
                any(
                    row["structure_set_id"] == "illagerinvasion:illager_fort"
                    and row["loot_table_id"] == "illagerinvasion:chests/illager_fort_ground"
                    for row in self.structure_set_loot_links
                )
            )

    def test_default_stack_base_item_presence_dedupes_duplicate_items(self) -> None:
        bastion_arrow = next(
            row
            for row in self.structure_set_base_item_presence
            if row["structure_set_id"] == "minecraft:nether_complexes"
            and row["structure_id"] == "minecraft:bastion_remnant"
            and row["item_id"] == "minecraft:arrow"
        )
        self.assertEqual(bastion_arrow["source_loot_table_count"], "3")
        keys = {
            (row["structure_set_id"], row["structure_id"], row["item_id"])
            for row in self.structure_set_base_item_presence
        }
        self.assertEqual(len(keys), len(self.structure_set_base_item_presence))

    def test_default_stack_stage2_discovers_sophisticated_backpacks_glms(self) -> None:
        if not SOPHISTICATED_DIR.exists():
            self.assertEqual(self.glm_chain, [])
            self.assertEqual(self.stage2_report["glm_chain_length"], 0)
            return
        self.assertEqual(len(self.glm_chain), 9)
        self.assertEqual(self.stage2_report["glm_chain_length"], 9)
        self.assertEqual(self.stage2_report["recognized_modifier_count"], 9)
        self.assertEqual(self.stage2_report["unsupported_modifier_count"], 0)
        self.assertTrue(all(row["analysis_status"] == "recognized_inject_semantics" for row in self.glm_chain))
        self.assertTrue(all(row["modifier_type"] == "sophisticatedbackpacks:inject_loot" for row in self.glm_chain))

    def test_default_stack_stage2_payload_rows_include_woodland_mansion_items(self) -> None:
        if not SOPHISTICATED_DIR.exists():
            self.skipTest("Sophisticated Backpacks directory fixture is not present in libs")
        woodland_rows = [
            row
            for row in self.modifier_added_leaf_rows
            if row["target_table_id"] == "minecraft:chests/woodland_mansion"
        ]
        self.assertTrue(woodland_rows)
        item_ids = {row["item_id"] for row in woodland_rows}
        self.assertIn("sophisticatedbackpacks:iron_backpack", item_ids)
        self.assertIn("sophisticatedbackpacks:gold_backpack", item_ids)
        self.assertIn("sophisticatedbackpacks:advanced_magnet_upgrade", item_ids)

    def test_default_stack_stage2_target_summary_tracks_novel_items(self) -> None:
        if not SOPHISTICATED_DIR.exists():
            self.skipTest("Sophisticated Backpacks directory fixture is not present in libs")
        summary_row = next(
            row for row in self.target_table_modifier_summary if row["target_table_id"] == "minecraft:chests/woodland_mansion"
        )
        self.assertEqual(summary_row["modifier_count"], "1")
        self.assertEqual(summary_row["supported_modifier_count"], "1")
        self.assertEqual(summary_row["unsupported_modifier_count"], "0")
        self.assertGreaterEqual(int(summary_row["novel_item_count"]), 3)

    def test_default_stack_marks_missing_mod_item_classification_in_coverage(self) -> None:
        if not ILLAGER_DIR.exists():
            self.skipTest("Illager directory fixture is not present in libs")
        missing_rows = [row for row in self.classification_coverage if row["has_classification"] == "false"]
        self.assertTrue(missing_rows)
        self.assertTrue(any(row["item_id"].startswith("illagerinvasion:") for row in missing_rows))

    def test_default_stack_normalizes_item_affinities(self) -> None:
        apple_affinities = {
            row["affinity"]
            for row in self.item_affinities
            if row["item_id"] == "minecraft:apple"
        }
        self.assertEqual(apple_affinities, {"food", "household"})

    def test_resolution_yaml_files_include_one_to_many_comments(self) -> None:
        self.assertIn("# One-to-many model:", self.ambiguous_resolution_text)
        self.assertIn("# One-to-many model:", self.manual_resolution_text)
        self.assertIn("loot_table_id may legitimately map to multiple", self.ambiguous_resolution_text)
        self.assertIn("unresolved placeholder row may remain beside mapped rows", self.manual_resolution_text)

    def test_default_stack_writes_ambiguous_and_no_match_resolution_data(self) -> None:
        self.assertGreater(self.structure_resolution_report["exact_match_count"], 0)
        self.assertGreater(self.structure_resolution_report["ambiguous_match_candidate_count"], 0)
        self.assertEqual(self.structure_resolution_report["no_match_count"], 2)
        self.assertEqual(self.structure_resolution_report["no_match_unresolved_count"], 2)
        ambiguous_entries = self.ambiguous_resolution_map["entries"]
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/desert_pyramid"
                and entry["match_rule"] == "loose_table_candidate"
                and entry["autoresolve"] is False
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/ruined_portal"
                and entry["match_rule"] == "structure_family_candidate"
                for entry in ambiguous_entries
            )
        )
        manual_entries = self.manual_resolution_map["entries"]
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/simple_dungeon"
                and entry["status"] == "unresolved"
                for entry in manual_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/spawn_bonus_chest"
                and entry["status"] == "unresolved"
                for entry in manual_entries
            )
        )

    def test_ambiguous_autoresolve_applies_candidate_and_stage2_effective_presence(self) -> None:
        if not SOPHISTICATED_DIR.exists():
            self.skipTest("Sophisticated Backpacks directory fixture is not present in libs")
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "ambiguous_autoresolve"
            ambiguous_path = Path(tempdir) / "ambiguous.yaml"
            manual_path = Path(tempdir) / "manual.yaml"
            ambiguous_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {
                                "loot_table_id": "minecraft:chests/woodland_mansion",
                                "structure_set_id": "minecraft:woodland_mansions",
                                "structure_id": "minecraft:mansion",
                                "match_rule": "structure_family_candidate",
                                "evidence_kind": "structure_nbt_family",
                                "evidence_data": {"family": "woodland_mansion"},
                                "autoresolve": True,
                                "notes": "Autoresolve mansion candidate for structure profile test.",
                            }
                        ],
                    },
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            export_with_temp_resolution_maps(
                output_dir=output_dir,
                ambiguous_resolution_config_path=ambiguous_path,
                manual_resolution_config_path=manual_path,
            )
            links = read_csv_rows(output_dir / "structure_set_loot_links.csv")
            audit = read_csv_rows(output_dir / "structure_set_loot_link_audit.csv")
            effective_rows = read_csv_rows(output_dir / "structure_set_effective_item_presence.csv")
            self.assertTrue(
                any(
                    row["structure_set_id"] == "minecraft:woodland_mansions"
                    and row["structure_id"] == "minecraft:mansion"
                    and row["loot_table_id"] == "minecraft:chests/woodland_mansion"
                    and row["link_source"] == "ambiguous_match"
                    for row in links
                )
            )
            self.assertTrue(
                any(
                    row["structure_set_id"] == "minecraft:woodland_mansions"
                    and row["structure_id"] == "minecraft:mansion"
                    and row["loot_table_id"] == "minecraft:chests/woodland_mansion"
                    and row["resolution"] == "active_ambiguous_autoresolve"
                    for row in audit
                )
            )
            self.assertTrue(
                any(
                    row["structure_set_id"] == "minecraft:woodland_mansions"
                    and row["structure_id"] == "minecraft:mansion"
                    and row["item_id"] == "sophisticatedbackpacks:iron_backpack"
                    and row["item_presence_kind"] == "stage2_only"
                    for row in effective_rows
                )
            )

    def test_manual_no_match_mapping_applies_row_grain_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "manual_no_match"
            ambiguous_path = Path(tempdir) / "ambiguous.yaml"
            manual_path = Path(tempdir) / "manual.yaml"
            manual_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {
                                "loot_table_id": "minecraft:chests/simple_dungeon",
                                "status": "mapped",
                                "structure_set_id": "minecraft:mineshafts",
                                "structure_id": "minecraft:mineshaft",
                                "notes": "Manual no-match mapping for workflow test.",
                            }
                        ],
                    },
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            export_with_temp_resolution_maps(
                output_dir=output_dir,
                ambiguous_resolution_config_path=ambiguous_path,
                manual_resolution_config_path=manual_path,
            )
            links = read_csv_rows(output_dir / "structure_set_loot_links.csv")
            audit = read_csv_rows(output_dir / "structure_set_loot_link_audit.csv")
            self.assertTrue(
                any(
                    row["structure_set_id"] == "minecraft:mineshafts"
                    and row["structure_id"] == "minecraft:mineshaft"
                    and row["loot_table_id"] == "minecraft:chests/simple_dungeon"
                    and row["link_source"] == "manual_no_match"
                    for row in links
                )
            )
            self.assertTrue(
                any(
                    row["structure_set_id"] == "minecraft:mineshafts"
                    and row["structure_id"] == "minecraft:mineshaft"
                    and row["loot_table_id"] == "minecraft:chests/simple_dungeon"
                    and row["resolution"] == "active_manual_no_match"
                    for row in audit
                )
            )

    def test_explicit_archive_replaces_auto_discovered_directory(self) -> None:
        if not ILLAGER_ARCHIVE.exists():
            self.skipTest("Illager archive fixture is not present in libs")
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "archive_replace"
            export_with_temp_resolution_maps(
                output_dir=output_dir,
                explicit_packs=[ILLAGER_ARCHIVE],
            )
            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            illager_row = next(row for row in precheck["selected_packs"] if row["pack_id"] == "illagerinvasion")
            self.assertEqual(illager_row["kind"], "archive")
            self.assertEqual(Path(illager_row["path"]), ILLAGER_ARCHIVE)

    def test_archive_root_discovers_archives(self) -> None:
        if not ILLAGER_ARCHIVE.exists():
            self.skipTest("Illager archive fixture is not present in libs")
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "archive_root"
            result = export_with_temp_resolution_maps(
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
                export_with_temp_resolution_maps(
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

            export_with_temp_resolution_maps(
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

    def test_glm_registry_overlap_merges_without_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "mod_a",
                "moda",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["moda:test_add"], "replace": False}
                    ),
                    "data/moda/loot_modifiers/test_add.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/simple_dungeon",
                                }
                            ],
                            "table": "moda:inject/chests/simple_dungeon",
                        }
                    ),
                    "data/moda/loot_table/inject/chests/simple_dungeon.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:apple"}]}],
                        }
                    ),
                },
            )
            write_mod_pack(
                mods_root / "mod_b",
                "modb",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["modb:test_add"], "replace": False}
                    ),
                    "data/modb/loot_modifiers/test_add.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/woodland_mansion",
                                }
                            ],
                            "table": "modb:inject/chests/woodland_mansion",
                        }
                    ),
                    "data/modb/loot_table/inject/chests/woodland_mansion.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:bread"}]}],
                        }
                    ),
                },
            )

            export_with_temp_resolution_maps(
                output_dir=output_dir,
                mods_root=mods_root,
                archive_roots=[],
                explicit_packs=[],
            )

            chain_rows = read_csv_rows(output_dir / "glm_modifier_chain.csv")
            self.assertEqual([row["modifier_id"] for row in chain_rows], ["moda:test_add", "modb:test_add"])

    def test_glm_registry_replace_true_resets_earlier_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "mod_a",
                "moda",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["moda:test_add"], "replace": False}
                    ),
                    "data/moda/loot_modifiers/test_add.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/simple_dungeon",
                                }
                            ],
                            "table": "moda:inject/chests/simple_dungeon",
                        }
                    ),
                    "data/moda/loot_table/inject/chests/simple_dungeon.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:apple"}]}],
                        }
                    ),
                },
            )
            write_mod_pack(
                mods_root / "mod_b",
                "modb",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["modb:test_add"], "replace": True}
                    ),
                    "data/modb/loot_modifiers/test_add.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/woodland_mansion",
                                }
                            ],
                            "table": "modb:inject/chests/woodland_mansion",
                        }
                    ),
                    "data/modb/loot_table/inject/chests/woodland_mansion.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:bread"}]}],
                        }
                    ),
                },
            )

            export_with_temp_resolution_maps(
                output_dir=output_dir,
                mods_root=mods_root,
                archive_roots=[],
                explicit_packs=[],
            )

            chain_rows = read_csv_rows(output_dir / "glm_modifier_chain.csv")
            self.assertEqual([row["modifier_id"] for row in chain_rows], ["modb:test_add"])

    def test_stage2_marks_unsupported_and_out_of_scope_modifiers(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "mod_stage2",
                "modstage2",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["modstage2:unsupported", "modstage2:out_of_scope"], "replace": False}
                    ),
                    "data/modstage2/loot_modifiers/unsupported.json": json.dumps(
                        {
                            "type": "modstage2:custom_logic",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/simple_dungeon",
                                }
                            ],
                        }
                    ),
                    "data/modstage2/loot_modifiers/out_of_scope.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:entities/cow",
                                }
                            ],
                            "table": "modstage2:inject/entities/cow",
                        }
                    ),
                    "data/modstage2/loot_table/inject/entities/cow.json": json.dumps(
                        {
                            "type": "minecraft:entity",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:leather"}]}],
                        }
                    ),
                },
            )

            export_with_temp_resolution_maps(
                output_dir=output_dir,
                mods_root=mods_root,
                archive_roots=[],
                explicit_packs=[],
            )

            chain_rows = read_csv_rows(output_dir / "glm_modifier_chain.csv")
            unsupported_row = next(row for row in chain_rows if row["modifier_id"] == "modstage2:unsupported")
            out_of_scope_row = next(row for row in chain_rows if row["modifier_id"] == "modstage2:out_of_scope")
            self.assertEqual(unsupported_row["analysis_status"], "unsupported_modifier_type")
            self.assertEqual(out_of_scope_row["analysis_status"], "recognized_inject_target_out_of_scope")
            self.assertEqual(out_of_scope_row["target_in_stage1_scope"], "false")
            added_rows = read_csv_rows(output_dir / "modifier_added_leaf_candidates.csv")
            self.assertEqual(added_rows, [])

    def test_unknown_manifest_pack_id_is_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            manifest_path = Path(tempdir) / "pack_order.json"
            manifest_path.write_text(json.dumps(["not_a_real_pack"]), encoding="utf-8")
            write_mod_pack(
                mods_root / "real_mod",
                "realm",
                {
                    "data/realm/loot_table/chests/example.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:stick"}]}],
                        }
                    )
                },
            )

            with self.assertRaises(exporter.PrecheckFailed):
                export_with_temp_resolution_maps(
                    output_dir=output_dir,
                    mods_root=mods_root,
                    archive_roots=[],
                    explicit_packs=[],
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

            result = export_with_temp_resolution_maps(
                output_dir=output_dir,
                mods_root=mods_root,
                ignore_roots=[ignore_root],
                archive_roots=[],
                explicit_packs=[],
            )

            self.assertEqual(result["manifest"]["selected_pack_ids"], ["base", "visiblemod"])
            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertIn(str(ignore_root), precheck["ignored_sources"])

    def test_synthetic_path_weight_fields_cover_multi_hop_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "weights_mod",
                "weightsmod",
                {
                    "data/weightsmod/loot_table/chests/root_weighted.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {
                                            "type": "minecraft:loot_table",
                                            "value": "weightsmod:chests/mid_weighted",
                                            "weight": 3,
                                        },
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:stone",
                                            "weight": 1,
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                    "data/weightsmod/loot_table/chests/mid_weighted.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:diamond",
                                            "weight": 5,
                                        },
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:gold_ingot",
                                            "weight": 5,
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                    "data/weightsmod/loot_table/chests/root_unweighted.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {
                                            "type": "minecraft:loot_table",
                                            "value": "weightsmod:chests/mid_weighted",
                                        }
                                        ,
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:cobblestone",
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                    "data/weightsmod/loot_table/chests/root_all_unweighted.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {
                                            "type": "minecraft:loot_table",
                                            "value": "weightsmod:chests/mid_unweighted",
                                        }
                                        ,
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:dirt",
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                    "data/weightsmod/loot_table/chests/mid_unweighted.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:stick",
                                        }
                                        ,
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:oak_planks",
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                },
            )

            export_with_temp_resolution_maps(
                output_dir=output_dir,
                mods_root=mods_root,
                archive_roots=[],
                explicit_packs=[],
            )

            leaf_rows = read_csv_rows(output_dir / "leaf_candidates.csv")
            pool_rows = read_csv_rows(output_dir / "pools.csv")
            entry_rows = read_csv_rows(output_dir / "entries.csv")

            root_weighted_pool = next(
                row for row in pool_rows if row["table_id"] == "weightsmod:chests/root_weighted"
            )
            self.assertNotIn("pool_defaulted_weight_entry_count", root_weighted_pool)

            root_unweighted_entry = next(
                row
                for row in entry_rows
                if row["table_id"] == "weightsmod:chests/root_unweighted" and row["entry_type"] == "minecraft:loot_table"
            )
            self.assertNotIn("weight_was_defaulted", root_unweighted_entry)
            self.assertEqual(root_unweighted_entry["pool_weight_share"], "0.5")

            weighted_row = next(
                row
                for row in leaf_rows
                if row["root_table_id"] == "weightsmod:chests/root_weighted" and row["item_id"] == "minecraft:diamond"
            )
            self.assertEqual(weighted_row["root_entry_weight"], "3")
            self.assertEqual(weighted_row["leaf_weight"], "5")
            self.assertNotIn("root_entry_weight_was_defaulted", weighted_row)
            self.assertEqual(weighted_row["root_pool_weight_share"], "0.75")
            self.assertEqual(weighted_row["path_pool_shares_json"], "[0.75,0.5]")
            self.assertEqual(weighted_row["path_pool_share_product"], "0.375")
            self.assertEqual(weighted_row["path_explicit_weights_json"], "[3,5]")
            self.assertEqual(weighted_row["path_explicit_weight_product"], "15")
            self.assertNotIn("path_missing_weight_count", weighted_row)
            self.assertNotIn("path_has_implicit_default_weights", weighted_row)

            root_missing_row = next(
                row
                for row in leaf_rows
                if row["root_table_id"] == "weightsmod:chests/root_unweighted" and row["item_id"] == "minecraft:diamond"
            )
            self.assertEqual(root_missing_row["root_entry_weight"], "")
            self.assertEqual(root_missing_row["leaf_weight"], "5")
            self.assertNotIn("root_entry_weight_was_defaulted", root_missing_row)
            self.assertEqual(root_missing_row["root_pool_weight_share"], "0.5")
            self.assertEqual(root_missing_row["path_pool_shares_json"], "[0.5,0.5]")
            self.assertEqual(root_missing_row["path_pool_share_product"], "0.25")
            self.assertEqual(root_missing_row["path_explicit_weights_json"], "[5]")
            self.assertEqual(root_missing_row["path_explicit_weight_product"], "5")
            self.assertNotIn("path_missing_weight_count", root_missing_row)
            self.assertNotIn("path_has_implicit_default_weights", root_missing_row)

            all_missing_row = next(
                row
                for row in leaf_rows
                if row["root_table_id"] == "weightsmod:chests/root_all_unweighted" and row["item_id"] == "minecraft:stick"
            )
            self.assertEqual(all_missing_row["root_entry_weight"], "")
            self.assertEqual(all_missing_row["leaf_weight"], "")
            self.assertNotIn("root_entry_weight_was_defaulted", all_missing_row)
            self.assertEqual(all_missing_row["root_pool_weight_share"], "0.5")
            self.assertEqual(all_missing_row["path_pool_shares_json"], "[0.5,0.5]")
            self.assertEqual(all_missing_row["path_pool_share_product"], "0.25")
            self.assertEqual(all_missing_row["path_explicit_weights_json"], "[]")
            self.assertEqual(all_missing_row["path_explicit_weight_product"], "")
            self.assertNotIn("path_missing_weight_count", all_missing_row)
            self.assertNotIn("path_has_implicit_default_weights", all_missing_row)

    def test_custom_classification_csv_handles_mod_items_and_normalized_affinities(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            classification_csv = Path(tempdir) / "resolved_loot_v77.csv"
            with classification_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "item_id",
                        "function",
                        "affinities",
                        "value",
                        "amount_class",
                        "matched_rule_id",
                        "matched_detail",
                        "amatched_details",
                        "classification_status",
                        "is_fallback_match",
                        "classification_version",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "item_id": "minecraft:stick",
                        "function": "item_material",
                        "affinities": "['wooden']",
                        "value": "junk",
                        "amount_class": "small",
                        "matched_rule_id": "test_rule",
                        "matched_detail": "minecraft:stick",
                        "amatched_details": "['#c:rods']",
                        "classification_status": "matched",
                        "is_fallback_match": "false",
                        "classification_version": "77",
                    }
                )
                writer.writerow(
                    {
                        "item_id": "moda:token",
                        "function": "misc_tool",
                        "affinities": "['treasure','underground']",
                        "value": "rare",
                        "amount_class": "singleton",
                        "matched_rule_id": "mod_rule",
                        "matched_detail": "moda:token",
                        "amatched_details": "['moda:token']",
                        "classification_status": "matched",
                        "is_fallback_match": "false",
                        "classification_version": "77",
                    }
                )
            write_mod_pack(
                mods_root / "mod_a",
                "moda",
                {
                    "data/moda/loot_table/chests/example.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {"type": "minecraft:item", "name": "moda:token"},
                                        {"type": "minecraft:item", "name": "minecraft:stick"},
                                    ],
                                }
                            ],
                        }
                    )
                },
            )

            export_with_temp_resolution_maps(
                output_dir=output_dir,
                mods_root=mods_root,
                archive_roots=[],
                explicit_packs=[],
                classification_csv_path=classification_csv,
            )

            item_classification = read_csv_rows(output_dir / "item_classification.csv")
            item_affinities = read_csv_rows(output_dir / "item_affinities.csv")
            coverage = read_csv_rows(output_dir / "classification_coverage.csv")

            mod_row = next(row for row in item_classification if row["item_id"] == "moda:token")
            self.assertEqual(mod_row["function"], "misc_tool")
            self.assertEqual(mod_row["classification_version"], "77")

            mod_affinities = {
                row["affinity"]
                for row in item_affinities
                if row["item_id"] == "moda:token"
            }
            self.assertEqual(mod_affinities, {"treasure", "underground"})

            coverage_row = next(row for row in coverage if row["item_id"] == "moda:token")
            self.assertEqual(coverage_row["has_classification"], "true")
            self.assertEqual(coverage_row["classification_status"], "matched")
            self.assertEqual(coverage_row["function"], "misc_tool")


if __name__ == "__main__":
    unittest.main()
