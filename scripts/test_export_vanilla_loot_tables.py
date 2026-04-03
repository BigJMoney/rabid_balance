from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "scripts" / "test_fixtures"
AMBIGUOUS_FIXTURE_PATH = FIXTURES_DIR / "structure_loot_ambiguous_resolution_map.yaml"
MANUAL_FIXTURE_PATH = FIXTURES_DIR / "structure_loot_manual_resolution_map.yaml"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import export_vanilla_loot_tables as exporter


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def copy_resolution_map_fixtures(destination_root: Path) -> tuple[Path, Path]:
    destination_root.mkdir(parents=True, exist_ok=True)
    ambiguous_path = destination_root / "structure_loot_ambiguous_resolution_map.yaml"
    manual_path = destination_root / "structure_loot_manual_resolution_map.yaml"
    ambiguous_path.write_text(AMBIGUOUS_FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    manual_path.write_text(MANUAL_FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return ambiguous_path, manual_path


class ExportVanillaLootTablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.tempdir.name)
        cls.ambiguous_resolution_path, cls.manual_resolution_path = copy_resolution_map_fixtures(Path(cls.tempdir.name))
        exporter.export_loot_tables(
            output_dir=cls.output_dir,
            ambiguous_resolution_config_path=cls.ambiguous_resolution_path,
            manual_resolution_config_path=cls.manual_resolution_path,
        )

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
        cls.table_roles = read_csv_rows(cls.output_dir / "table_role_summary.csv")
        cls.table_role_evidence = read_csv_rows(cls.output_dir / "table_role_evidence.csv")
        cls.item_classification = read_csv_rows(cls.output_dir / "item_classification.csv")
        cls.item_affinities = read_csv_rows(cls.output_dir / "item_affinities.csv")
        cls.classification_coverage = read_csv_rows(cls.output_dir / "classification_coverage.csv")
        cls.structure_rows = read_csv_rows(cls.output_dir / "structures.csv")
        cls.structure_loot_links = read_csv_rows(cls.output_dir / "structure_loot_links.csv")
        cls.structure_loot_link_audit = read_csv_rows(cls.output_dir / "structure_loot_link_audit.csv")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def test_expected_files_exist(self) -> None:
        expected = {
            "tables.csv",
            "pools.csv",
            "entries.csv",
            "leaf_candidates.csv",
            "table_role_summary.csv",
            "table_role_evidence.csv",
            "glm_modifier_chain.csv",
            "modifier_added_leaf_candidates.csv",
            "target_table_modifier_summary.csv",
            "target_table_added_item_summary.csv",
            "stage2_report.json",
            "structure_loot_resolution_report.json",
            "item_classification.csv",
            "item_affinities.csv",
            "classification_coverage.csv",
            "structures.csv",
            "structure_loot_links.csv",
            "structure_loot_link_audit.csv",
            "scope_report.json",
            "manifest.json",
            "README.md",
        }
        found = {path.name for path in self.output_dir.iterdir()}
        self.assertTrue(expected.issubset(found))
        self.assertTrue(
            {
                "structure_set_entries.csv",
                "structure_set_loot_links.csv",
                "structure_set_loot_link_audit.csv",
                "structure_set_base_item_presence.csv",
                "structure_set_effective_item_presence.csv",
                "structure_set_profile_summary.csv",
            }.isdisjoint(found)
        )

    def test_scope_report_lists_included_and_excluded_folders(self) -> None:
        included = {item["name"]: item["file_count"] for item in self.scope_report["included_dirs"]}
        excluded = {item["name"]: item["file_count"] for item in self.scope_report["excluded_dirs"]}

        self.assertEqual(included, {"chests": 56, "equipment": 3, "pots": 1, "spawners": 5})
        self.assertEqual(
            excluded,
            {
                "archaeology": 6,
                "blocks": 982,
                "dispensers": 3,
                "entities": 100,
                "gameplay": 21,
                "shearing": 1,
            },
        )
        self.assertEqual(self.scope_report["included_table_total"], 65)
        self.assertEqual(self.scope_report["excluded_table_total"], 1113)

    def test_manifest_counts_match_scoped_source(self) -> None:
        self.assertEqual(self.manifest["named_table_count"], 65)
        self.assertEqual(self.manifest["inline_table_count"], 3)
        self.assertEqual(self.manifest["table_count"], 68)
        self.assertEqual(self.manifest["named_reference_count"], 10)
        self.assertEqual(self.manifest["inline_reference_count"], 3)
        self.assertEqual(self.manifest["table_role_summary_count"], 65)
        self.assertGreater(self.manifest["table_role_evidence_count"], 0)
        self.assertEqual(self.manifest["glm_modifier_chain_count"], 0)
        self.assertEqual(self.manifest["modifier_added_leaf_candidate_count"], 0)
        self.assertEqual(self.manifest["target_table_modifier_summary_count"], 0)
        self.assertEqual(self.manifest["target_table_added_item_summary_count"], 0)
        self.assertGreater(self.manifest["item_classification_count"], 0)
        self.assertGreater(self.manifest["item_affinity_count"], 0)
        self.assertGreater(self.manifest["classification_coverage_count"], 0)
        self.assertEqual(self.manifest["structure_count"], 34)
        self.assertEqual(self.manifest["structure_loot_link_count"], 49)
        self.assertEqual(self.manifest["structure_loot_link_audit_count"], 142)
        self.assertEqual(self.manifest["missing_loot_item_count"], 0)
        self.assertEqual(
            self.manifest["raw_role_counts"],
            {
                "direct_from_data": 35,
                "helper_from_data": 7,
                "unknown_directness": 23,
            },
        )
        self.assertEqual(
            self.manifest["effective_role_counts"],
            {
                "assumed_direct_for_tableau": 23,
                "direct_from_data": 35,
                "helper_from_data": 7,
            },
        )
        self.assertGreater(self.manifest["leaf_candidate_count"], 0)

    def test_vanilla_stage2_outputs_are_empty_but_present(self) -> None:
        self.assertEqual(read_csv_rows(self.output_dir / "glm_modifier_chain.csv"), [])
        self.assertEqual(read_csv_rows(self.output_dir / "modifier_added_leaf_candidates.csv"), [])
        self.assertEqual(read_csv_rows(self.output_dir / "target_table_modifier_summary.csv"), [])
        self.assertEqual(read_csv_rows(self.output_dir / "target_table_added_item_summary.csv"), [])
        stage2_report = json.loads((self.output_dir / "stage2_report.json").read_text(encoding="utf-8"))
        self.assertEqual(stage2_report["glm_chain_length"], 0)

    def test_vanilla_structure_outputs_are_present_and_stable(self) -> None:
        self.assertEqual(len(self.structure_rows), 34)
        self.assertEqual(len(self.structure_loot_links), 49)
        self.assertEqual(len(self.structure_loot_link_audit), 142)
        trial_row = next(row for row in self.structure_rows if row["structure_id"] == "minecraft:trial_chambers")
        self.assertEqual(trial_row["structure_detection_status"], "exact_supported_links_found_root_match_eligible")
        desert_row = next(row for row in self.structure_rows if row["structure_id"] == "minecraft:desert_pyramid")
        self.assertEqual(desert_row["structure_detection_status"], "exact_unsupported_no_root_match:minecraft:desert_pyramid")

    def test_vanilla_resolution_outputs_and_yaml_headers_exist(self) -> None:
        self.assertEqual(self.structure_resolution_report["exact_match_table_count"], 38)
        self.assertEqual(self.structure_resolution_report["exact_match_row_count"], 49)
        self.assertEqual(self.structure_resolution_report["ambiguous_match_candidate_table_count"], 38)
        self.assertEqual(self.structure_resolution_report["ambiguous_match_candidate_row_count"], 85)
        self.assertEqual(self.structure_resolution_report["ambiguous_match_pending_row_count"], 85)
        self.assertEqual(self.structure_resolution_report["ambiguous_match_autoresolved_row_count"], 0)
        self.assertEqual(self.structure_resolution_report["no_match_table_count"], 8)
        self.assertEqual(self.structure_resolution_report["no_match_unresolved_table_count"], 8)
        self.assertEqual(self.structure_resolution_report["no_match_unresolved_row_count"], 8)
        self.assertIn("# One-to-many model:", self.ambiguous_resolution_text)
        self.assertIn("# One-to-many model:", self.manual_resolution_text)
        self.assertTrue(
            {entry["match_rule"] for entry in self.ambiguous_resolution_map["entries"]}.issubset(
                {
                    "ambiguous_structure_root_match",
                    "ambiguous_structure_id_match",
                    "ambiguous_structure_id_submatch",
                }
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/desert_pyramid"
                and entry["structure_id"] == "minecraft:desert_pyramid"
                and entry["match_rule"] == "ambiguous_structure_id_match"
                and entry["evidence_data"]["structure_id_stem"] == "desert_pyramid"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/igloo_chest"
                and entry["structure_id"] == "minecraft:igloo"
                and entry["evidence_data"]["structure_root"] == "igloo"
                and entry["evidence_data"]["match_mode"] == "underscore_prefix"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/shipwreck_supply"
                and entry["structure_id"] == "minecraft:shipwreck"
                and entry["evidence_data"]["structure_root"] == "shipwreck"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/shipwreck_supply"
                and entry["structure_id"] == "minecraft:shipwreck_beached"
                and entry["match_rule"] == "ambiguous_structure_id_submatch"
                and entry["evidence_data"]["structure_id_submatch"] == "shipwreck"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/buried_treasure"
                and entry["structure_id"] == "minecraft:buried_treasure"
                and entry["match_rule"] == "ambiguous_structure_id_match"
                and entry["evidence_data"]["structure_id_stem"] == "buried_treasure"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/trial_chambers/intersection"
                and entry["structure_id"] == "minecraft:trial_chambers"
                and entry["evidence_data"]["structure_root"] == "trial_chambers"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/ruined_portal"
                and entry["structure_id"] == "minecraft:ruined_portal_desert"
                and entry["match_rule"] == "ambiguous_structure_id_submatch"
                and entry["evidence_data"]["structure_id_submatch"] == "ruined_portal"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:equipment/trial_chamber"
                and entry["structure_id"] == "minecraft:trial_chambers"
                and entry["match_rule"] == "ambiguous_structure_root_match"
                and entry["evidence_data"]["match_mode"] == "first_segment_plural"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            all(entry["loot_table_id"] != "minecraft:chests/buried_treasure" for entry in self.manual_resolution_map["entries"])
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/underwater_ruin_big"
                and entry["status"] == "unresolved"
                for entry in self.manual_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/woodland_mansion"
                and entry["structure_id"] == "minecraft:mansion"
                and entry["match_rule"] == "ambiguous_structure_root_match"
                and entry["evidence_data"]["structure_root"] == "woodland_mansion"
                for entry in self.ambiguous_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/simple_dungeon"
                and entry["status"] == "unresolved"
                for entry in self.manual_resolution_map["entries"]
            )
        )
        self.assertTrue(
            any(
                entry["loot_table_id"] == "minecraft:chests/nether_bridge"
                and entry["status"] == "unresolved"
                for entry in self.manual_resolution_map["entries"]
            )
        )

    def test_named_table_categories_stay_within_scope(self) -> None:
        named_rows = [row for row in self.tables if row["table_id_kind"] == "named"]
        self.assertEqual(len(named_rows), 65)
        self.assertEqual({row["category"] for row in named_rows}, {"chests", "equipment", "pots", "spawners"})

    def test_ids_are_unique(self) -> None:
        self.assertEqual(len(self.tables), len({row["table_id"] for row in self.tables}))
        self.assertEqual(len(self.pools), len({row["pool_id"] for row in self.pools}))
        self.assertEqual(len(self.entries), len({row["entry_id"] for row in self.entries}))
        self.assertEqual(len(self.table_roles), len({row["table_id"] for row in self.table_roles}))

    def test_named_and_inline_refs_resolve(self) -> None:
        table_ids = {row["table_id"] for row in self.tables}
        ref_ids = {row["ref_table_id"] for row in self.entries if row["ref_table_id"]}
        inline_ids = {row["inline_table_id"] for row in self.entries if row["inline_table_id"]}

        self.assertTrue(ref_ids)
        self.assertTrue(inline_ids)
        self.assertTrue(ref_ids.issubset(table_ids))
        self.assertTrue(inline_ids.issubset(table_ids))

    def test_village_weaponsmith_rows_capture_counts(self) -> None:
        weaponsmith_table = next(
            row for row in self.tables if row["table_id"] == "minecraft:chests/village/village_weaponsmith"
        )
        self.assertEqual(weaponsmith_table["table_type"], "minecraft:chest")

        diamond_row = next(
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:chests/village/village_weaponsmith"
            and row["item_id"] == "minecraft:diamond"
        )
        self.assertEqual(diamond_row["set_count_min"], "1.0")
        self.assertEqual(diamond_row["set_count_max"], "3.0")

    def test_trial_chambers_reward_resolves_named_refs(self) -> None:
        reward_rows = [
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:chests/trial_chambers/reward"
        ]
        leaf_table_ids = {row["leaf_table_id"] for row in reward_rows}

        self.assertIn("minecraft:chests/trial_chambers/reward_common", leaf_table_ids)
        self.assertIn("minecraft:chests/trial_chambers/reward_rare", leaf_table_ids)
        self.assertTrue(any(int(row["chain_depth"]) >= 2 for row in reward_rows))

    def test_trial_chamber_inline_tables_are_generated(self) -> None:
        inline_rows = [
            row
            for row in self.tables
            if row["table_id_kind"] == "inline" and row["source_file"] == "equipment/trial_chamber.json"
        ]
        self.assertEqual(len(inline_rows), 3)
        self.assertTrue(all(row["generated_from_entry_id"] for row in inline_rows))

        trial_chamber_rows = [
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:equipment/trial_chamber"
        ]
        self.assertTrue(any(row["leaf_table_id"].startswith("inline:") for row in trial_chamber_rows))

    def test_trial_chamber_melee_keeps_named_ref(self) -> None:
        melee_ref = next(
            row
            for row in self.entries
            if row["table_id"] == "minecraft:equipment/trial_chamber_melee"
            and row["ref_table_id"] == "minecraft:equipment/trial_chamber"
        )
        self.assertEqual(melee_ref["entry_type"], "minecraft:loot_table")

        melee_leaf = next(
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:equipment/trial_chamber_melee"
            and "minecraft:equipment/trial_chamber" in row["selection_chain_json"]
        )
        self.assertTrue(melee_leaf["selection_chain_json"])
        self.assertEqual(melee_leaf["root_entry_weight"], "")
        self.assertEqual(melee_leaf["leaf_weight"], "")
        self.assertEqual(melee_leaf["path_explicit_weights_json"], "[4]")
        self.assertEqual(melee_leaf["path_explicit_weight_product"], "4")
        self.assertNotIn("path_missing_weight_count", melee_leaf)
        self.assertNotIn("path_has_implicit_default_weights", melee_leaf)

    def test_pots_corridor_preserves_weight_and_literal_count(self) -> None:
        emerald_row = next(
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:pots/trial_chambers/corridor"
            and row["item_id"] == "minecraft:emerald"
        )
        self.assertEqual(emerald_row["root_entry_weight"], "125")
        self.assertEqual(emerald_row["leaf_weight"], "125")
        self.assertNotIn("root_entry_weight_was_defaulted", emerald_row)
        self.assertTrue(emerald_row["root_pool_weight_share"])
        self.assertTrue(emerald_row["path_pool_shares_json"])
        self.assertTrue(emerald_row["path_pool_share_product"])
        self.assertEqual(emerald_row["path_explicit_weights_json"], "[125]")
        self.assertEqual(emerald_row["path_explicit_weight_product"], "125")
        self.assertNotIn("path_missing_weight_count", emerald_row)
        self.assertNotIn("path_has_implicit_default_weights", emerald_row)
        self.assertEqual(emerald_row["set_count_min"], "1.0")
        self.assertEqual(emerald_row["set_count_max"], "3.0")

        diamond_block_row = next(
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:pots/trial_chambers/corridor"
            and row["item_id"] == "minecraft:diamond_block"
        )
        self.assertNotIn("root_entry_weight_was_defaulted", diamond_block_row)
        self.assertTrue(diamond_block_row["root_pool_weight_share"])
        self.assertTrue(diamond_block_row["path_pool_shares_json"])
        self.assertTrue(diamond_block_row["path_pool_share_product"])
        self.assertEqual(diamond_block_row["path_explicit_weight_product"], "")
        self.assertNotIn("path_missing_weight_count", diamond_block_row)
        self.assertNotIn("path_has_implicit_default_weights", diamond_block_row)
        self.assertEqual(diamond_block_row["set_count_min"], "1.0")
        self.assertEqual(diamond_block_row["set_count_max"], "1.0")

    def test_spawner_consumables_captures_set_potion(self) -> None:
        potion_rows = [
            row
            for row in self.entries
            if row["table_id"] == "minecraft:spawners/trial_chamber/consumables"
            and row["name"] == "minecraft:potion"
        ]
        self.assertTrue(potion_rows)
        self.assertTrue(all("minecraft:set_potion" in row["function_types"] for row in potion_rows))

    def test_leaf_rows_are_parseable_and_populated(self) -> None:
        sample = next(row for row in self.leaf_rows if row["item_id"])
        chain = json.loads(sample["selection_chain_json"])

        self.assertTrue(sample["root_table_id"])
        self.assertTrue(sample["leaf_kind"])
        self.assertIsInstance(chain, list)
        self.assertTrue(chain)
        self.assertIn("root_entry_weight", sample)
        self.assertIn("root_pool_weight_share", sample)
        self.assertIn("path_pool_shares_json", sample)
        self.assertIn("path_explicit_weights_json", sample)

    def test_raw_tables_include_pool_normalized_weight_fields(self) -> None:
        sample_pool = next(iter(self.pools))
        sample_entry = next(iter(self.entries))
        self.assertNotIn("pool_defaulted_weight_entry_count", sample_pool)
        self.assertNotIn("weight_was_defaulted", sample_entry)
        self.assertIn("pool_weight_share", sample_entry)

    def test_table_role_rows_cover_named_scope(self) -> None:
        self.assertEqual(len(self.table_roles), 65)
        self.assertEqual({row["category"] for row in self.table_roles}, {"chests", "equipment", "pots", "spawners"})

    def test_known_helper_tables_stay_helper_only(self) -> None:
        for table_id in (
            "minecraft:chests/trial_chambers/reward_common",
            "minecraft:chests/trial_chambers/reward_rare",
            "minecraft:chests/trial_chambers/reward_unique",
        ):
            row = next(role for role in self.table_roles if role["table_id"] == table_id)
            self.assertEqual(row["raw_role"], "helper_from_data")
            self.assertEqual(row["effective_role"], "helper_from_data")
            self.assertEqual(row["count_as_direct"], "false")

    def test_known_direct_tables_have_data_side_evidence(self) -> None:
        for table_id in (
            "minecraft:chests/village/village_weaponsmith",
            "minecraft:pots/trial_chambers/corridor",
            "minecraft:spawners/ominous/trial_chamber/key",
        ):
            row = next(role for role in self.table_roles if role["table_id"] == table_id)
            self.assertEqual(row["raw_role"], "direct_from_data")
            self.assertEqual(row["count_as_direct"], "true")
            self.assertGreater(int(row["structure_ref_count"]), 0)

    def test_trial_chamber_equipment_is_helper_from_exact_local_evidence(self) -> None:
        row = next(role for role in self.table_roles if role["table_id"] == "minecraft:equipment/trial_chamber")
        self.assertEqual(row["raw_role"], "helper_from_data")
        self.assertEqual(row["effective_role"], "helper_from_data")
        self.assertEqual(row["count_as_direct"], "false")
        self.assertGreaterEqual(int(row["inbound_loot_ref_count"]), 1)
        self.assertEqual(int(row["structure_ref_count"]), 0)

    def test_known_unknowns_become_assumed_direct_for_tableau(self) -> None:
        for table_id in (
            "minecraft:chests/abandoned_mineshaft",
            "minecraft:chests/desert_pyramid",
            "minecraft:chests/shipwreck_treasure",
            "minecraft:spawners/trial_chamber/key",
        ):
            row = next(role for role in self.table_roles if role["table_id"] == table_id)
            self.assertEqual(row["raw_role"], "unknown_directness")
            self.assertEqual(row["effective_role"], "assumed_direct_for_tableau")
            self.assertEqual(row["count_as_direct"], "true")

    def test_table_role_counts_match_expected_split(self) -> None:
        raw_counts: dict[str, int] = {}
        for row in self.table_roles:
            raw_counts[row["raw_role"]] = raw_counts.get(row["raw_role"], 0) + 1
        self.assertEqual(
            raw_counts,
            {
                "direct_from_data": 35,
                "helper_from_data": 7,
                "unknown_directness": 23,
            },
        )

    def test_structure_evidence_rows_include_absolute_paths(self) -> None:
        village_rows = [
            row
            for row in self.table_role_evidence
            if row["table_id"] == "minecraft:chests/village/village_weaponsmith"
            and row["evidence_type"] == "structure_nbt"
        ]
        self.assertTrue(village_rows)
        self.assertTrue(all(Path(row["source_path"]).is_absolute() for row in village_rows))
        self.assertTrue(all(row["source_object"] for row in village_rows))

    def test_item_classification_rows_join_cleanly(self) -> None:
        arrow = next(row for row in self.item_classification if row["item_id"] == "minecraft:arrow")
        self.assertEqual(arrow["function"], "weapon")
        self.assertEqual(arrow["value"], "common")
        self.assertEqual(arrow["amount_class"], "large")
        self.assertEqual(arrow["classification_status"], "matched")
        self.assertEqual(arrow["classification_version"], "10")

    def test_item_affinities_are_normalized(self) -> None:
        apple_affinities = {
            row["affinity"]
            for row in self.item_affinities
            if row["item_id"] == "minecraft:apple"
        }
        self.assertEqual(apple_affinities, {"food", "household"})

    def test_classification_coverage_flags_vanilla_items_as_classified(self) -> None:
        arrow_row = next(row for row in self.classification_coverage if row["item_id"] == "minecraft:arrow")
        self.assertEqual(arrow_row["has_classification"], "true")
        self.assertEqual(arrow_row["classification_status"], "matched")
        self.assertEqual(arrow_row["function"], "weapon")
        self.assertTrue(all(row["has_classification"] == "true" for row in self.classification_coverage))

    def test_refresh_all_structure_resolution_maps_passes_through_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            ambiguous_path = root / "ambiguous.yaml"
            manual_path = root / "manual.yaml"
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
            exporter.export_loot_tables(
                output_dir=root / "out",
                ambiguous_resolution_config_path=ambiguous_path,
                manual_resolution_config_path=manual_path,
                refresh_all_structure_resolution_maps=True,
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
                all(entry["loot_table_id"] != "minecraft:chests/buried_treasure" for entry in refreshed_manual["entries"])
            )

    def test_clean_structure_resolution_maps_passes_through_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            ambiguous_path = root / "ambiguous.yaml"
            manual_path = root / "manual.yaml"
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
            exporter.export_loot_tables(
                output_dir=root / "out",
                ambiguous_resolution_config_path=ambiguous_path,
                manual_resolution_config_path=manual_path,
                clean_structure_resolution_maps=True,
            )
            cleaned_ambiguous = yaml.safe_load(ambiguous_path.read_text(encoding="utf-8"))
            cleaned_manual = yaml.safe_load(manual_path.read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
