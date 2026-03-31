from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import export_vanilla_loot_tables as exporter


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ExportVanillaLootTablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.tempdir.name)
        exporter.export_loot_tables(output_dir=cls.output_dir)

        cls.scope_report = json.loads((cls.output_dir / "scope_report.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((cls.output_dir / "manifest.json").read_text(encoding="utf-8"))
        cls.tables = read_csv_rows(cls.output_dir / "tables.csv")
        cls.pools = read_csv_rows(cls.output_dir / "pools.csv")
        cls.entries = read_csv_rows(cls.output_dir / "entries.csv")
        cls.leaf_rows = read_csv_rows(cls.output_dir / "leaf_candidates.csv")
        cls.table_roles = read_csv_rows(cls.output_dir / "table_role_summary.csv")
        cls.table_role_evidence = read_csv_rows(cls.output_dir / "table_role_evidence.csv")

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
            "scope_report.json",
            "manifest.json",
            "README.md",
        }
        found = {path.name for path in self.output_dir.iterdir()}
        self.assertTrue(expected.issubset(found))

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

    def test_pots_corridor_preserves_weight_and_literal_count(self) -> None:
        emerald_row = next(
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:pots/trial_chambers/corridor"
            and row["item_id"] == "minecraft:emerald"
        )
        self.assertEqual(emerald_row["leaf_weight"], "125")
        self.assertEqual(emerald_row["set_count_min"], "1.0")
        self.assertEqual(emerald_row["set_count_max"], "3.0")

        diamond_block_row = next(
            row
            for row in self.leaf_rows
            if row["root_table_id"] == "minecraft:pots/trial_chambers/corridor"
            and row["item_id"] == "minecraft:diamond_block"
        )
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


if __name__ == "__main__":
    unittest.main()
