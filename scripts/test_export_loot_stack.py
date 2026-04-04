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
SOURCE_LIBS_ROOT = PROJECT_ROOT / "sourcelibs"
ILLAGER_DIR = LIBS_ROOT / "IllagerInvasion-v21.1.6-NeoForge"
ILLAGER_ARCHIVE = LIBS_ROOT / "IllagerInvasion-v21.1.6-NeoForge.zip"
SOPHISTICATED_DIR = LIBS_ROOT / "sophisticatedbackpacks-3.25.34.1581"
RABID_BALANCE_DIRS = [path for path in (LIBS_ROOT / "rabid_balance", SOURCE_LIBS_ROOT / "rabid_balance") if path.exists()]
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
    ignore_roots = kwargs.pop("ignore_roots", None)
    if ambiguous_path is None or manual_path is None:
        default_ambiguous_path, default_manual_path = copy_resolution_map_fixtures(output_dir.parent)
        ambiguous_path = ambiguous_path or default_ambiguous_path
        manual_path = manual_path or default_manual_path
    if ignore_roots is None:
        ignore_roots = list(exporter.DEFAULT_IGNORE_ROOTS)
        ignore_roots.extend(RABID_BALANCE_DIRS)
    return exporter.export_loot_stack(
        output_dir=output_dir,
        ambiguous_resolution_config_path=Path(ambiguous_path),
        manual_resolution_config_path=Path(manual_path),
        ignore_roots=ignore_roots,
        **kwargs,
    )


class ExportLootStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.tempdir.name) / "default_stack"
        cls.ambiguous_resolution_path, cls.manual_resolution_path = copy_resolution_map_fixtures(Path(cls.tempdir.name))
        ignore_roots = list(exporter.DEFAULT_IGNORE_ROOTS)
        ignore_roots.extend(RABID_BALANCE_DIRS)
        exporter.export_loot_stack(
            output_dir=cls.output_dir,
            ambiguous_resolution_config_path=cls.ambiguous_resolution_path,
            manual_resolution_config_path=cls.manual_resolution_path,
            ignore_roots=ignore_roots,
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
        cls.root_table_item_summary = read_csv_rows(cls.output_dir / "root_table_item_summary.csv")
        cls.evidence = read_csv_rows(cls.output_dir / "table_role_evidence.csv")
        cls.glm_chain = read_csv_rows(cls.output_dir / "glm_modifier_chain.csv")
        cls.modifier_added_leaf_rows = read_csv_rows(cls.output_dir / "modifier_added_leaf_candidates.csv")
        cls.target_table_modifier_summary = read_csv_rows(cls.output_dir / "target_table_modifier_summary.csv")
        cls.target_table_added_item_summary = read_csv_rows(cls.output_dir / "target_table_added_item_summary.csv")
        cls.stage2_report = json.loads((cls.output_dir / "stage2_report.json").read_text(encoding="utf-8"))
        cls.item_classification = read_csv_rows(cls.output_dir / "item_classification.csv")
        cls.item_affinities = read_csv_rows(cls.output_dir / "item_affinities.csv")
        cls.classification_coverage = read_csv_rows(cls.output_dir / "classification_coverage.csv")
        cls.structure_rows = read_csv_rows(cls.output_dir / "structures.csv")
        cls.structure_loot_links = read_csv_rows(cls.output_dir / "structure_loot_links.csv")
        cls.structure_loot_link_audit = read_csv_rows(cls.output_dir / "structure_loot_link_audit.csv")

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
        self.assertIn("has_random_chance", pool_row)
        self.assertIn("random_chance_value", pool_row)
        self.assertIn("has_random_chance", entry_row)
        self.assertIn("random_chance_value", entry_row)
        summary_row = next(iter(self.root_table_item_summary))
        self.assertIn("drop_events_expected", summary_row)
        self.assertIn("drop_yield_expected", summary_row)
        self.assertIn("at_least_one_chance", summary_row)
        self.assertIn("chance_status", summary_row)

    def test_illager_entry_random_chance_exports_as_entry_level_scalar(self) -> None:
        entry_row = next(
            row
            for row in self.entries
            if row["table_id"] == "illagerinvasion:chests/illager_fort_ground" and row["name"] == "minecraft:crossbow"
        )
        self.assertEqual(entry_row["has_random_chance"], "true")
        self.assertEqual(entry_row["random_chance_value"], "0.25")

        pool_row = next(row for row in self.pools if row["pool_id"] == entry_row["pool_id"])
        self.assertEqual(pool_row["has_random_chance"], "false")
        self.assertEqual(pool_row["random_chance_value"], "")

        leaf_row = next(
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "illagerinvasion:chests/illager_fort_ground"
            and row["item_id"] == "minecraft:crossbow"
        )
        self.assertEqual(leaf_row["path_random_chance_product"], "0.25")

        summary_row = next(
            row
            for row in self.root_table_item_summary
            if row["root_table_id"] == "illagerinvasion:chests/illager_fort_ground"
            and row["item_id"] == "minecraft:crossbow"
        )
        self.assertEqual(summary_row["path_count"], "1")
        self.assertEqual(summary_row["drop_events_expected"], "0.25")
        self.assertEqual(summary_row["drop_yield_expected"], "0.25")
        self.assertEqual(summary_row["at_least_one_chance"], "0.25")
        self.assertEqual(summary_row["chance_status"], "exact")

    def test_default_stack_writes_stage15_classification_tables(self) -> None:
        self.assertTrue(self.item_classification)
        self.assertTrue(self.classification_coverage)
        arrow = next(row for row in self.item_classification if row["item_id"] == "minecraft:arrow")
        self.assertEqual(arrow["function"], "weapon")
        self.assertEqual(arrow["classification_version"], "10")

    def test_default_stack_leaf_rows_embed_item_classification(self) -> None:
        arrow_leaf = next(row for row in self.leaf_rows if row["item_id"] == "minecraft:arrow")
        self.assertEqual(arrow_leaf["item_has_classification"], "true")
        self.assertEqual(arrow_leaf["item_classification_status"], "matched")
        self.assertEqual(arrow_leaf["item_function"], "weapon")
        self.assertEqual(arrow_leaf["item_value"], "common")
        self.assertEqual(arrow_leaf["item_amount_class"], "large")
        self.assertEqual(arrow_leaf["item_classification_version"], "10")

    def test_default_stack_writes_structure_tables(self) -> None:
        expected_structure_count = 34 + (5 if ILLAGER_DIR.exists() else 0)
        self.assertEqual(len(self.structure_rows), expected_structure_count)
        self.assertTrue(self.structure_loot_links)
        self.assertTrue(self.structure_loot_link_audit)
        for retired_name in (
            "structure_set_entries.csv",
            "structure_set_loot_links.csv",
            "structure_set_loot_link_audit.csv",
            "structure_set_base_item_presence.csv",
            "structure_set_effective_item_presence.csv",
            "structure_set_profile_summary.csv",
        ):
            self.assertFalse((self.output_dir / retired_name).exists())

    def test_default_stack_structure_rows_include_illager_structures(self) -> None:
        if not ILLAGER_DIR.exists():
            self.skipTest("Illager directory fixture is not present in libs")
        illager_rows = [row for row in self.structure_rows if row["structure_id"].startswith("illagerinvasion:")]
        self.assertEqual(len(illager_rows), 5)
        self.assertTrue(any(row["structure_id"] == "illagerinvasion:illager_fort" for row in illager_rows))

    def test_default_stack_structure_detection_tracks_trial_chambers_and_illager(self) -> None:
        trial_row = next(row for row in self.structure_rows if row["structure_id"] == "minecraft:trial_chambers")
        self.assertEqual(trial_row["structure_detection_status"], "exact_supported_links_found_root_match_eligible")
        trial_links = [
            row
            for row in self.structure_loot_links
            if row["structure_id"] == "minecraft:trial_chambers"
        ]
        self.assertTrue(any(row["loot_table_id"] == "minecraft:chests/trial_chambers/reward" for row in trial_links))
        if ILLAGER_DIR.exists():
            illager_row = next(row for row in self.structure_rows if row["structure_id"] == "illagerinvasion:illager_fort")
            self.assertEqual(illager_row["structure_detection_status"], "exact_supported_links_found_root_match_eligible")
            self.assertTrue(
                any(
                    row["structure_id"] == "illagerinvasion:illager_fort"
                    and row["loot_table_id"] == "illagerinvasion:chests/illager_fort_ground"
                    for row in self.structure_loot_links
                )
            )

    def test_default_stack_non_jigsaw_root_alias_supports_woodland_mansion(self) -> None:
        mansion_row = next(row for row in self.structure_rows if row["structure_id"] == "minecraft:mansion")
        self.assertEqual(
            mansion_row["structure_detection_status"],
            "exact_unsupported_root_match_eligible:minecraft:woodland_mansion",
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/woodland_mansion"
                and entry["structure_id"] == "minecraft:mansion"
                and entry["match_rule"] == "ambiguous_structure_root_match"
                and entry["evidence_data"]["structure_root"] == "woodland_mansion"
                and entry["evidence_data"]["match_mode"] == "first_segment"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )

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

    def test_default_stack_stage2_payload_rows_embed_item_classification(self) -> None:
        if not SOPHISTICATED_DIR.exists():
            self.skipTest("Sophisticated Backpacks directory fixture is not present in libs")
        backpack_row = next(
            row
            for row in self.modifier_added_leaf_rows
            if row["item_id"] == "sophisticatedbackpacks:diamond_backpack"
        )
        self.assertEqual(backpack_row["item_has_classification"], "true")
        self.assertEqual(backpack_row["item_classification_status"], "matched")
        self.assertEqual(backpack_row["item_function"], "wearable")
        self.assertEqual(backpack_row["item_value"], "epic")
        self.assertEqual(backpack_row["item_amount_class"], "singleton")
        self.assertEqual(backpack_row["item_classification_version"], "10")

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

    def test_default_stack_classification_coverage_is_complete_for_current_fixture_set(self) -> None:
        missing_rows = [row for row in self.classification_coverage if row["has_classification"] == "false"]
        self.assertEqual(missing_rows, [])

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
        self.assertIn("Once mapped rows exist for a loot_table_id", self.manual_resolution_text)

    def test_default_stack_writes_ambiguous_and_no_match_resolution_data(self) -> None:
        self.assertGreater(self.structure_resolution_report["exact_match_table_count"], 0)
        self.assertGreater(self.structure_resolution_report["exact_match_row_count"], 0)
        self.assertEqual(
            self.structure_resolution_report["ambiguous_match_candidate_row_count"],
            len(self.ambiguous_resolution_map["entries"]),
        )
        self.assertEqual(
            self.structure_resolution_report["ambiguous_match_pending_row_count"],
            len(self.ambiguous_resolution_map["entries"]),
        )
        self.assertEqual(self.structure_resolution_report["ambiguous_match_autoresolved_row_count"], 0)
        self.assertEqual(
            self.structure_resolution_report["no_match_unresolved_row_count"],
            len(self.manual_resolution_map["entries"]),
        )
        self.assertEqual(
            self.structure_resolution_report["no_match_unresolved_table_count"],
            len({entry["loot_table_id"] for entry in self.manual_resolution_map["entries"]}),
        )
        self.assertEqual(self.structure_resolution_report["warnings"], [])
        ambiguous_entries = self.ambiguous_resolution_map["entries"]
        self.assertTrue(ambiguous_entries)
        self.assertTrue(
            {entry["match_rule"] for entry in ambiguous_entries}.issubset(
                {
                    "ambiguous_structure_root_match",
                    "ambiguous_structure_id_match",
                    "ambiguous_structure_id_submatch",
                }
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/igloo_chest"
                and entry["structure_id"] == "minecraft:igloo"
                and entry["evidence_data"]["structure_root"] == "igloo"
                and entry["evidence_data"]["match_mode"] == "underscore_prefix"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/ruined_portal"
                and entry["structure_id"] == "minecraft:ruined_portal"
                and entry["evidence_data"]["structure_root"] == "ruined_portal"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/shipwreck_supply"
                and entry["structure_id"] == "minecraft:shipwreck"
                and entry["evidence_data"]["structure_root"] == "shipwreck"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/shipwreck_supply"
                and entry["structure_id"] == "minecraft:shipwreck_beached"
                and entry["match_rule"] == "ambiguous_structure_id_submatch"
                and entry["evidence_data"]["structure_id_submatch"] == "shipwreck"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/trial_chambers/intersection"
                and entry["structure_id"] == "minecraft:trial_chambers"
                and entry["evidence_data"]["structure_root"] == "trial_chambers"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/ruined_portal"
                and entry["structure_id"] == "minecraft:ruined_portal_desert"
                and entry["match_rule"] == "ambiguous_structure_id_submatch"
                and entry["evidence_data"]["structure_id_submatch"] == "ruined_portal"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/desert_pyramid"
                and entry["structure_id"] == "minecraft:desert_pyramid"
                and entry["match_rule"] == "ambiguous_structure_id_match"
                and entry["evidence_data"]["structure_id_stem"] == "desert_pyramid"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/buried_treasure"
                and entry["structure_id"] == "minecraft:buried_treasure"
                and entry["match_rule"] == "ambiguous_structure_id_match"
                and entry["evidence_data"]["structure_id_stem"] == "buried_treasure"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/stronghold_library"
                and entry["structure_id"] == "minecraft:stronghold"
                and entry["match_rule"] == "ambiguous_structure_id_match"
                and entry["evidence_data"]["match_mode"] == "underscore_prefix"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:equipment/trial_chamber"
                and entry["structure_id"] == "minecraft:trial_chambers"
                and entry["match_rule"] == "ambiguous_structure_root_match"
                and entry["evidence_data"]["match_mode"] == "first_segment_plural"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:spawners/trial_chamber/consumables"
                and entry["structure_id"] == "minecraft:trial_chambers"
                and entry["match_rule"] == "ambiguous_structure_root_match"
                and entry["evidence_data"]["match_mode"] == "first_segment_plural"
                for entry in ambiguous_entries
            )
        )
        self.assertTrue(
            all(entry["loot_table_id"] != "minecraft:chests/nether_bridge" for entry in ambiguous_entries)
        )
        manual_entries = self.manual_resolution_map["entries"]
        self.assertTrue(all(entry["loot_table_id"] != "minecraft:chests/buried_treasure" for entry in manual_entries))
        self.assertTrue(all(entry["loot_table_id"] != "minecraft:chests/desert_pyramid" for entry in manual_entries))
        self.assertTrue(all(entry["loot_table_id"] != "minecraft:equipment/trial_chamber" for entry in manual_entries))
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/underwater_ruin_big"
                and entry["status"] == "unresolved"
                for entry in manual_entries
            )
        )
        self.assertTrue(
            all(entry["loot_table_id"] != "minecraft:chests/woodland_mansion" for entry in manual_entries)
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/nether_bridge"
                and entry["status"] == "unresolved"
                and entry["structure_id"] == ""
                for entry in manual_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/simple_dungeon"
                and entry["status"] == "unresolved"
                for entry in manual_entries
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/jungle_temple"
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
                                "loot_table_id": "minecraft:chests/shipwreck_supply",
                                "structure_id": "minecraft:shipwreck_beached",
                                "match_rule": "ambiguous_structure_id_submatch",
                                "evidence_data": {
                                    "structure_id_submatch": "shipwreck",
                                    "matched_value": "shipwreck",
                                    "match_mode": "underscore_prefix",
                                },
                                "autoresolve": True,
                                "notes": "Autoresolve submatch candidate for structure-link test.",
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
            links = read_csv_rows(output_dir / "structure_loot_links.csv")
            audit = read_csv_rows(output_dir / "structure_loot_link_audit.csv")
            resolution_report = json.loads(
                (output_dir / "structure_loot_resolution_report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(
                any(
                    row["structure_id"] == "minecraft:shipwreck_beached"
                    and row["loot_table_id"] == "minecraft:chests/shipwreck_supply"
                    and row["link_source"] == "ambiguous_match"
                    and row["link_method"] == "ambiguous_structure_id_submatch"
                    for row in links
                )
            )
            self.assertTrue(
                any(
                    row["structure_id"] == "minecraft:shipwreck_beached"
                    and row["loot_table_id"] == "minecraft:chests/shipwreck_supply"
                    and row["resolution"] == "active_ambiguous_autoresolve"
                    for row in audit
                )
            )
            self.assertEqual(resolution_report["ambiguous_match_autoresolved_row_count"], 1)

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
            links = read_csv_rows(output_dir / "structure_loot_links.csv")
            audit = read_csv_rows(output_dir / "structure_loot_link_audit.csv")
            self.assertTrue(
                any(
                    row["structure_id"] == "minecraft:mineshaft"
                    and row["loot_table_id"] == "minecraft:chests/simple_dungeon"
                    and row["link_source"] == "manual_no_match"
                    for row in links
                )
            )
            self.assertTrue(
                any(
                    row["structure_id"] == "minecraft:mineshaft"
                    and row["loot_table_id"] == "minecraft:chests/simple_dungeon"
                    and row["resolution"] == "active_manual_no_match"
                    for row in audit
                )
            )
            final_manual_map = yaml.safe_load(manual_path.read_text(encoding="utf-8"))
            simple_rows = [
                entry
                for entry in final_manual_map["entries"]
                if entry["loot_table_id"] == "minecraft:chests/simple_dungeon"
            ]
            self.assertEqual(
                simple_rows,
                [
                    {
                        "loot_table_id": "minecraft:chests/simple_dungeon",
                        "status": "mapped",
                        "structure_id": "minecraft:mineshaft",
                        "notes": "Manual no-match mapping for workflow test.",
                    }
                ],
            )

    def test_rebuild_all_structure_resolution_maps_rebuilds_both_yaml_files(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "refresh_maps"
            ambiguous_path = Path(tempdir) / "ambiguous.yaml"
            manual_path = Path(tempdir) / "manual.yaml"
            ambiguous_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {
                                "loot_table_id": "minecraft:chests/nether_bridge",
                                "structure_id": "minecraft:fortress",
                                "match_rule": "bogus_rule",
                                "evidence_data": {"matched_value": "bogus"},
                                "autoresolve": True,
                                "notes": "Should be removed by refresh.",
                            }
                        ],
                    },
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            manual_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {
                                "loot_table_id": "minecraft:chests/buried_treasure",
                                "status": "mapped",
                                "structure_id": "minecraft:fortress",
                                "notes": "Should be removed by refresh.",
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
                rebuild_all_structure_resolution_maps=True,
            )
            refreshed_ambiguous = yaml.safe_load(ambiguous_path.read_text(encoding="utf-8"))
            refreshed_manual = yaml.safe_load(manual_path.read_text(encoding="utf-8"))
            self.assertTrue(
                any(
                    entry["loot_table_id"] == "minecraft:chests/buried_treasure"
                    and entry["structure_id"] == "minecraft:buried_treasure"
                    for entry in refreshed_ambiguous["entries"]
                )
            )
            self.assertTrue(
                all(
                    not (
                        entry["loot_table_id"] == "minecraft:chests/nether_bridge"
                        and entry.get("structure_id") == "minecraft:fortress"
                    )
                    for entry in refreshed_ambiguous["entries"]
                )
            )
            self.assertTrue(
                all(entry["loot_table_id"] != "minecraft:chests/buried_treasure" for entry in refreshed_manual["entries"])
            )

    def test_clean_structure_resolution_maps_prunes_stale_rows_but_preserves_current_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = Path(tempdir) / "clean_maps"
            ambiguous_path = Path(tempdir) / "ambiguous.yaml"
            manual_path = Path(tempdir) / "manual.yaml"
            ambiguous_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {
                                "loot_table_id": "minecraft:chests/buried_treasure",
                                "structure_id": "minecraft:buried_treasure",
                                "match_rule": "ambiguous_structure_id_match",
                                "evidence_data": {"structure_id_stem": "buried_treasure", "matched_value": "buried_treasure", "match_mode": "exact"},
                                "autoresolve": True,
                                "notes": "Keep this current ambiguous approval.",
                            },
                            {
                                "loot_table_id": "minecraft:chests/nether_bridge",
                                "structure_id": "minecraft:fortress",
                                "match_rule": "bogus_rule",
                                "evidence_data": {"matched_value": "bogus"},
                                "autoresolve": True,
                                "notes": "Prune this stale ambiguous row.",
                            },
                        ],
                    },
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            manual_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {
                                "loot_table_id": "minecraft:chests/simple_dungeon",
                                "status": "mapped",
                                "structure_id": "minecraft:mineshaft",
                                "notes": "Keep this current manual mapping.",
                            },
                            {
                                "loot_table_id": "minecraft:chests/buried_treasure",
                                "status": "mapped",
                                "structure_id": "minecraft:fortress",
                                "notes": "Prune this stale manual mapping.",
                            },
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
                clean_structure_resolution_maps=True,
            )
            cleaned_ambiguous = yaml.safe_load(ambiguous_path.read_text(encoding="utf-8"))
            cleaned_manual = yaml.safe_load(manual_path.read_text(encoding="utf-8"))
            links = read_csv_rows(output_dir / "structure_loot_links.csv")

            self.assertTrue(
                any(
                    entry["loot_table_id"] == "minecraft:chests/buried_treasure"
                    and entry["structure_id"] == "minecraft:buried_treasure"
                    and entry["autoresolve"] is True
                    for entry in cleaned_ambiguous["entries"]
                )
            )
            self.assertTrue(
                all(
                    not (
                        entry["loot_table_id"] == "minecraft:chests/nether_bridge"
                        and entry["structure_id"] == "minecraft:fortress"
                    )
                    for entry in cleaned_ambiguous["entries"]
                )
            )
            self.assertTrue(
                any(
                    entry["loot_table_id"] == "minecraft:chests/simple_dungeon"
                    and entry["status"] == "mapped"
                    and entry["structure_id"] == "minecraft:mineshaft"
                    for entry in cleaned_manual["entries"]
                )
            )
            self.assertTrue(
                all(
                    not (
                        entry["loot_table_id"] == "minecraft:chests/buried_treasure"
                        and entry.get("structure_id") == "minecraft:fortress"
                    )
                    for entry in cleaned_manual["entries"]
                )
            )
            self.assertTrue(
                any(
                    entry["loot_table_id"] == "minecraft:chests/nether_bridge"
                    and entry["status"] == "unresolved"
                    and entry["structure_id"] == ""
                    for entry in cleaned_manual["entries"]
                )
            )
            self.assertTrue(
                any(
                    row["structure_id"] == "minecraft:buried_treasure"
                    and row["loot_table_id"] == "minecraft:chests/buried_treasure"
                    and row["link_source"] == "ambiguous_match"
                    for row in links
                )
            )
            self.assertTrue(
                any(
                    row["structure_id"] == "minecraft:mineshaft"
                    and row["loot_table_id"] == "minecraft:chests/simple_dungeon"
                    and row["link_source"] == "manual_no_match"
                    for row in links
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

    def test_auto_discovery_scans_multiple_mod_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            libs_root = Path(tempdir) / "libs"
            sourcelibs_root = Path(tempdir) / "sourcelibs"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                sourcelibs_root / "source_mod",
                "sourcemod",
                {
                    "data/source/loot_table/chests/example.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:apple"}]}],
                        }
                    )
                },
            )

            result = export_with_temp_resolution_maps(
                output_dir=output_dir,
                mod_discovery_roots=[libs_root, sourcelibs_root],
                archive_roots=[],
                explicit_packs=[],
            )

            self.assertIn("sourcemod", result["manifest"]["selected_pack_ids"])
            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertEqual(
                precheck["mod_discovery_roots"],
                [str(libs_root.resolve()), str(sourcelibs_root.resolve())],
            )
            source_row = next(row for row in precheck["selected_packs"] if row["pack_id"] == "sourcemod")
            self.assertEqual(Path(source_row["path"]).resolve(), (sourcelibs_root / "source_mod").resolve())
            self.assertEqual(source_row["discovery_source"], f"auto_dir:{sourcelibs_root.resolve()}")

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

    def test_precheck_with_last_mod_pack_id_resolves_only_its_own_overlaps(self) -> None:
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

            export_with_temp_resolution_maps(
                output_dir=output_dir,
                mods_root=mods_root,
                archive_roots=[],
                explicit_packs=[],
                last_mod_pack_id="modb",
            )

            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertEqual(precheck["effective_order"], ["base", "moda", "modb"])
            self.assertEqual(precheck["last_mod_pack_id"], "modb")
            self.assertEqual(len(precheck["resolved_overlaps"]), 2)
            self.assertTrue(all(row["winner_pack_id"] == "modb" for row in precheck["resolved_overlaps"]))
            self.assertTrue(all(row.get("resolution_mode") == "last_mod" for row in precheck["resolved_overlaps"]))

            tables = read_csv_rows(output_dir / "tables.csv")
            common_row = next(row for row in tables if row["table_id"] == "shared:chests/common")
            self.assertEqual(common_row["source_pack"], "modb")

    def test_last_mod_pack_id_does_not_resolve_other_mod_overlaps(self) -> None:
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
                },
            )
            write_mod_pack(
                mods_root / "mod_b",
                "modb",
                {
                    "data/shared/loot_table/chests/common.json": shared_b,
                },
            )
            write_mod_pack(
                mods_root / "mod_c",
                "modc",
                {
                    "data/modc/loot_table/chests/extra.json": shared_a,
                },
            )

            with self.assertRaises(exporter.PrecheckFailed):
                export_with_temp_resolution_maps(
                    output_dir=output_dir,
                    mods_root=mods_root,
                    archive_roots=[],
                    explicit_packs=[],
                    last_mod_pack_id="modc",
                )

            precheck = json.loads((output_dir / "precheck_report.json").read_text(encoding="utf-8"))
            self.assertEqual(precheck["effective_order"], ["base", "moda", "modb", "modc"])
            self.assertEqual(precheck["last_mod_pack_id"], "modc")
            self.assertEqual(precheck["resolved_overlaps"], [])
            self.assertTrue(any("mod-vs-mod same-file overlap" in message for message in precheck["fatal_errors"]))

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

    def test_glm_registry_relisted_entry_moves_to_latest_position_without_duplication(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "mod_a",
                "moda",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["moda:first", "moda:second"], "replace": False}
                    ),
                    "data/moda/loot_modifiers/first.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/simple_dungeon",
                                }
                            ],
                            "table": "moda:inject/chests/first",
                        }
                    ),
                    "data/moda/loot_modifiers/second.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/woodland_mansion",
                                }
                            ],
                            "table": "moda:inject/chests/second",
                        }
                    ),
                    "data/moda/loot_table/inject/chests/first.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:apple"}]}],
                        }
                    ),
                    "data/moda/loot_table/inject/chests/second.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:bread"}]}],
                        }
                    ),
                },
            )
            write_mod_pack(
                mods_root / "mod_b",
                "modb",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["moda:first"], "replace": False}
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
            self.assertEqual([row["modifier_id"] for row in chain_rows], ["moda:second", "moda:first"])

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

    def test_stage2_added_leaf_rows_surface_path_random_chance_product(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "mod_stage2",
                "modstage2",
                {
                    "data/neoforge/loot_modifiers/global_loot_modifiers.json": json.dumps(
                        {"entries": ["modstage2:test_add"], "replace": False}
                    ),
                    "data/modstage2/loot_modifiers/test_add.json": json.dumps(
                        {
                            "type": "neoforge:add_table",
                            "conditions": [
                                {
                                    "condition": "neoforge:loot_table_id",
                                    "loot_table_id": "minecraft:chests/simple_dungeon",
                                }
                            ],
                            "table": "modstage2:inject/chests/simple_dungeon",
                        }
                    ),
                    "data/modstage2/loot_table/inject/chests/simple_dungeon.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "conditions": [
                                        {
                                            "condition": "minecraft:random_chance",
                                            "chance": 0.5,
                                        }
                                    ],
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:apple",
                                            "conditions": [
                                                {
                                                    "condition": "minecraft:random_chance",
                                                    "chance": 0.25,
                                                }
                                            ],
                                        }
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

            added_rows = read_csv_rows(output_dir / "modifier_added_leaf_candidates.csv")
            added_row = next(
                row
                for row in added_rows
                if row["target_table_id"] == "minecraft:chests/simple_dungeon" and row["item_id"] == "minecraft:apple"
            )
            self.assertEqual(added_row["path_random_chance_product"], "0.125")

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
            self.assertIn(str(ignore_root.resolve()), precheck["ignored_sources"])

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

    def test_random_chance_fields_cover_pool_entry_and_ambiguous_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "chance_mod",
                "chancecheck",
                {
                    "data/chancecheck/loot_table/chests/pool_only.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "conditions": [
                                        {
                                            "condition": "minecraft:random_chance",
                                            "chance": 0.5,
                                        }
                                    ],
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:apple",
                                        }
                                    ],
                                }
                            ],
                        }
                    ),
                    "data/chancecheck/loot_table/chests/pool_and_entry.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "conditions": [
                                        {
                                            "condition": "minecraft:random_chance",
                                            "chance": 0.5,
                                        }
                                    ],
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:bread",
                                            "conditions": [
                                                {
                                                    "condition": "minecraft:random_chance",
                                                    "chance": 0.25,
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ),
                    "data/chancecheck/loot_table/chests/ambiguous_entry.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:iron_ingot",
                                            "conditions": [
                                                {
                                                    "condition": "minecraft:random_chance",
                                                    "chance": 0.2,
                                                },
                                                {
                                                    "condition": "minecraft:random_chance",
                                                    "chance": 0.3,
                                                },
                                            ],
                                        }
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

            pool_rows = read_csv_rows(output_dir / "pools.csv")
            entry_rows = read_csv_rows(output_dir / "entries.csv")
            leaf_rows = read_csv_rows(output_dir / "leaf_candidates.csv")
            scope_report = json.loads((output_dir / "scope_report.json").read_text(encoding="utf-8"))

            pool_only_pool = next(row for row in pool_rows if row["table_id"] == "chancecheck:chests/pool_only")
            self.assertEqual(pool_only_pool["has_random_chance"], "true")
            self.assertEqual(pool_only_pool["random_chance_value"], "0.5")

            pool_only_entry = next(row for row in entry_rows if row["table_id"] == "chancecheck:chests/pool_only")
            self.assertEqual(pool_only_entry["has_random_chance"], "false")
            self.assertEqual(pool_only_entry["random_chance_value"], "")

            pool_only_leaf = next(row for row in leaf_rows if row["root_table_id"] == "chancecheck:chests/pool_only")
            self.assertEqual(pool_only_leaf["path_random_chance_product"], "0.5")

            pool_and_entry_entry = next(
                row for row in entry_rows if row["table_id"] == "chancecheck:chests/pool_and_entry"
            )
            self.assertEqual(pool_and_entry_entry["has_random_chance"], "true")
            self.assertEqual(pool_and_entry_entry["random_chance_value"], "0.25")

            pool_and_entry_leaf = next(
                row for row in leaf_rows if row["root_table_id"] == "chancecheck:chests/pool_and_entry"
            )
            self.assertEqual(pool_and_entry_leaf["path_random_chance_product"], "0.125")

            ambiguous_entry = next(
                row for row in entry_rows if row["table_id"] == "chancecheck:chests/ambiguous_entry"
            )
            self.assertEqual(ambiguous_entry["has_random_chance"], "true")
            self.assertEqual(ambiguous_entry["random_chance_value"], "")

            ambiguous_leaf = next(
                row for row in leaf_rows if row["root_table_id"] == "chancecheck:chests/ambiguous_entry"
            )
            self.assertEqual(ambiguous_leaf["path_random_chance_product"], "")
            self.assertTrue(
                any(
                    warning["type"] == "ambiguous_top_level_random_chance"
                    and warning["scope"] == "entry"
                    and warning["table_id"] == "chancecheck:chests/ambiguous_entry"
                    for warning in scope_report["warnings"]
                )
            )

    def test_root_table_item_summary_models_rolls_references_and_pool_independence(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            mods_root = Path(tempdir) / "mods"
            output_dir = Path(tempdir) / "out"
            write_mod_pack(
                mods_root / "summary_mod",
                "summarymod",
                {
                    "data/summarymod/loot_table/chests/root.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": {
                                        "type": "minecraft:uniform",
                                        "min": 1,
                                        "max": 2,
                                    },
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:apple",
                                            "weight": 1,
                                        },
                                        {
                                            "type": "minecraft:loot_table",
                                            "value": "summarymod:chests/branch",
                                            "weight": 1,
                                        },
                                    ],
                                },
                                {
                                    "rolls": 1,
                                    "conditions": [
                                        {
                                            "condition": "minecraft:random_chance",
                                            "chance": 0.5,
                                        }
                                    ],
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:apple",
                                        }
                                    ],
                                },
                            ],
                        }
                    ),
                    "data/summarymod/loot_table/chests/branch.json": json.dumps(
                        {
                            "type": "minecraft:chest",
                            "pools": [
                                {
                                    "rolls": 1,
                                    "entries": [
                                        {
                                            "type": "minecraft:item",
                                            "name": "minecraft:apple",
                                            "conditions": [
                                                {
                                                    "condition": "minecraft:random_chance",
                                                    "chance": 0.5,
                                                }
                                            ],
                                            "functions": [
                                                {
                                                    "function": "minecraft:set_count",
                                                    "count": {
                                                        "type": "minecraft:uniform",
                                                        "min": 0,
                                                        "max": 3,
                                                    },
                                                }
                                            ],
                                        }
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

            summary_rows = read_csv_rows(output_dir / "root_table_item_summary.csv")
            summary_row = next(
                row
                for row in summary_rows
                if row["root_table_id"] == "summarymod:chests/root" and row["item_id"] == "minecraft:apple"
            )

            self.assertEqual(summary_row["path_count"], "3")
            self.assertEqual(summary_row["drop_events_expected"], "1.53125")
            self.assertEqual(summary_row["drop_yield_expected"], "1.8125")
            self.assertEqual(summary_row["at_least_one_chance"], "0.8974609375")
            self.assertEqual(summary_row["chance_status"], "exact")

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
