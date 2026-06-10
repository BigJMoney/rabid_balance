from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import resolve_items_to_table as resolver


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ResolveItemsToTableTests(unittest.TestCase):
    def test_configurable_inputs_support_non_minecraft_namespaces(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            schema_path = root / "Loot Trait Assignments v10.yaml"
            item_ids_path = root / "item_ids.json"
            tags_by_item_path = root / "item_tags_by_item-no_loot_tags.json"
            output_prefix = root / "resolved_loot_v10"

            schema_path.write_text(
                yaml.safe_dump(
                    {
                        "loot_classification_by_trait": {
                            "version": 10,
                            "function_trait_assignment": [
                                {
                                    "id": "foods",
                                    "priority": 10,
                                    "match": ["#c:foods"],
                                    "assign": {
                                        "function": "consumable",
                                        "value": {"default": "common"},
                                        "amount_class": {"default": "small"},
                                    },
                                },
                                {
                                    "id": "magic_items",
                                    "priority": 5,
                                    "match": ["moda:rune"],
                                    "assign": {
                                        "function": "misc_tool",
                                        "value": {"default": "rare"},
                                        "amount_class": {"default": "singleton"},
                                    },
                                },
                                {
                                    "id": "fallback",
                                    "priority": 0,
                                    "match": {"summary": "fallback"},
                                    "assign": {
                                        "function": "nonloot",
                                        "value": {"default": "none"},
                                        "amount_class": {"default": "singleton"},
                                    },
                                },
                            ],
                            "affinity_trait_assignment": [
                                {"id": "food", "priority": 5, "match": ["#c:foods"]},
                                {"id": "treasure", "priority": 4, "match": ["moda:rune"]},
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )
            item_ids_path.write_text(
                json.dumps(["minecraft:apple", "moda:rune"], indent=2),
                encoding="utf-8",
            )
            tags_by_item_path.write_text(
                json.dumps(
                    {
                        "minecraft:apple": ["c:foods"],
                        "moda:rune": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = resolver.resolve_items_to_table(
                schema_path=schema_path,
                item_ids_path=item_ids_path,
                tags_by_item_path=tags_by_item_path,
                output_prefix=output_prefix,
            )

            self.assertEqual(result["classification_version"], "10")

            csv_rows = read_csv_rows(output_prefix.with_suffix(".csv"))
            json_rows = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))
            report_text = output_prefix.with_name("resolved_loot_v10_report.txt").read_text(encoding="utf-8")

            mod_row = next(row for row in csv_rows if row["item_id"] == "moda:rune")
            self.assertEqual(mod_row["function"], "misc_tool")
            self.assertEqual(mod_row["classification_status"], "matched")
            self.assertEqual(mod_row["is_fallback_match"], "false")
            self.assertEqual(mod_row["classification_version"], "10")

            apple_row = next(row for row in csv_rows if row["item_id"] == "minecraft:apple")
            self.assertEqual(apple_row["function"], "consumable")
            self.assertEqual(apple_row["classification_status"], "matched")

            self.assertEqual(json_rows["moda:rune"]["classification_version"], "10")
            self.assertFalse(json_rows["moda:rune"]["is_fallback_match"])
            self.assertIn("classification version: 10", report_text)

    def test_ignored_items_are_reported_separately_from_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            schema_path = root / "Loot Trait Assignments v10.yaml"
            item_ids_path = root / "item_ids.json"
            tags_by_item_path = root / "item_tags_by_item-no_loot_tags.json"
            output_prefix = root / "resolved_loot_v10"

            schema_path.write_text(
                yaml.safe_dump(
                    {
                        "loot_classification_by_trait": {
                            "version": 10,
                            "ignored_items": ["moda:driftwood_scrap"],
                            "function_trait_assignment": [
                                {
                                    "id": "foods",
                                    "priority": 10,
                                    "match": ["#c:foods"],
                                    "assign": {
                                        "function": "consumable",
                                        "value": {"default": "common"},
                                        "amount_class": {"default": "small"},
                                    },
                                },
                                {
                                    "id": "fallback",
                                    "priority": 0,
                                    "match": {"summary": "fallback"},
                                    "assign": {
                                        "function": "unmatched",
                                        "value": {"default": "none"},
                                        "amount_class": {"default": "singleton"},
                                    },
                                },
                            ],
                            "affinity_trait_assignment": [
                                {"id": "food", "priority": 5, "match": ["#c:foods"]},
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )
            item_ids_path.write_text(
                json.dumps(
                    [
                        "minecraft:apple",
                        "moda:driftwood_scrap",
                        "moda:unknown",
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )
            tags_by_item_path.write_text(
                json.dumps(
                    {
                        "minecraft:apple": ["c:foods"],
                        "moda:driftwood_scrap": ["c:foods"],
                        "moda:unknown": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            resolver.resolve_items_to_table(
                schema_path=schema_path,
                item_ids_path=item_ids_path,
                tags_by_item_path=tags_by_item_path,
                output_prefix=output_prefix,
            )

            csv_rows = read_csv_rows(output_prefix.with_suffix(".csv"))
            json_rows = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))
            report_text = output_prefix.with_name("resolved_loot_v10_report.txt").read_text(encoding="utf-8")

            ignored_row = next(row for row in csv_rows if row["item_id"] == "moda:driftwood_scrap")
            self.assertEqual(ignored_row["function"], "ignore")
            self.assertEqual(ignored_row["matched_rule_id"], "ignored_items")
            self.assertEqual(ignored_row["classification_status"], "matched")
            self.assertEqual(ignored_row["is_fallback_match"], "false")

            fallback_row = next(row for row in csv_rows if row["item_id"] == "moda:unknown")
            self.assertEqual(fallback_row["classification_status"], "fallback")
            self.assertEqual(fallback_row["is_fallback_match"], "true")

            self.assertEqual(json_rows["moda:driftwood_scrap"]["function"], "ignore")
            self.assertFalse(json_rows["moda:driftwood_scrap"]["is_fallback_match"])

            self.assertIn("ignored count: 1", report_text)
            self.assertIn("fallback count: 1", report_text)
            self.assertIn("fallback items:\n  moda:unknown", report_text)
            self.assertNotIn("ignored items:", report_text)
            self.assertNotIn("  moda:driftwood_scrap", report_text)

    def test_ignored_items_accept_namespace_wildcard_with_rule_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            schema_path = root / "Loot Trait Assignments v10.yaml"
            item_ids_path = root / "item_ids.json"
            tags_by_item_path = root / "item_tags_by_item-no_loot_tags.json"
            output_prefix = root / "resolved_loot_v10"

            schema_path.write_text(
                """
loot_classification_by_trait:
  version: 10
  ignored_items:
    - "moda:*"
  function_trait_assignment:
    - id: foods
      priority: 10
      match: ["#c:foods"]
      assign:
        function: consumable
        value:
          default: common
        amount_class:
          default: small
    - id: magic_items
      priority: 5
      match: ["moda:rune", "moda:rune_*"]
      assign:
        function: misc_tool
        value:
          default: rare
        amount_class:
          default: singleton
    - id: fallback
      priority: 0
      match:
        summary: fallback
      assign:
        function: unmatched
        value:
          default: none
        amount_class:
          default: singleton
  affinity_trait_assignment:
    - id: food
      priority: 5
      match: ["#c:foods"]
    - id: treasure
      priority: 4
      match: ["moda:rune"]
""",
                encoding="utf-8",
            )
            item_ids_path.write_text(
                json.dumps(
                    [
                        "minecraft:apple",
                        "moda:rune",
                        "moda:rune_alpha",
                        "moda:unknown",
                        "moda:unmatched",
                        "modb:unknown",
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )
            tags_by_item_path.write_text(
                json.dumps(
                    {
                        "minecraft:apple": ["c:foods"],
                        "moda:rune": [],
                        "moda:rune_alpha": [],
                        "moda:unknown": ["c:foods"],
                        "moda:unmatched": [],
                        "modb:unknown": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            resolver.resolve_items_to_table(
                schema_path=schema_path,
                item_ids_path=item_ids_path,
                tags_by_item_path=tags_by_item_path,
                output_prefix=output_prefix,
            )

            csv_rows = read_csv_rows(output_prefix.with_suffix(".csv"))
            json_rows = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))
            report_text = output_prefix.with_name("resolved_loot_v10_report.txt").read_text(encoding="utf-8")

            apple_row = next(row for row in csv_rows if row["item_id"] == "minecraft:apple")
            self.assertEqual(apple_row["function"], "consumable")
            self.assertEqual(apple_row["classification_status"], "matched")

            explicit_override_row = next(row for row in csv_rows if row["item_id"] == "moda:rune")
            self.assertEqual(explicit_override_row["function"], "misc_tool")
            self.assertEqual(explicit_override_row["matched_rule_id"], "magic_items")
            self.assertEqual(explicit_override_row["classification_status"], "matched")
            self.assertEqual(explicit_override_row["affinities"], "['treasure']")

            id_pattern_override_row = next(row for row in csv_rows if row["item_id"] == "moda:rune_alpha")
            self.assertEqual(id_pattern_override_row["function"], "misc_tool")
            self.assertEqual(id_pattern_override_row["matched_rule_id"], "magic_items")
            self.assertEqual(id_pattern_override_row["matched_detail"], "moda:rune_*")
            self.assertEqual(id_pattern_override_row["classification_status"], "matched")

            tag_override_row = next(row for row in csv_rows if row["item_id"] == "moda:unknown")
            self.assertEqual(tag_override_row["function"], "consumable")
            self.assertEqual(tag_override_row["matched_rule_id"], "foods")
            self.assertEqual(tag_override_row["classification_status"], "matched")
            self.assertEqual(tag_override_row["affinities"], "['food']")

            namespace_ignored_row = next(row for row in csv_rows if row["item_id"] == "moda:unmatched")
            self.assertEqual(namespace_ignored_row["function"], "ignore")
            self.assertEqual(namespace_ignored_row["matched_rule_id"], "ignored_items")
            self.assertEqual(namespace_ignored_row["matched_detail"], "moda:*")
            self.assertEqual(namespace_ignored_row["classification_status"], "matched")
            self.assertEqual(namespace_ignored_row["is_fallback_match"], "false")
            self.assertEqual(namespace_ignored_row["affinities"], "[]")

            fallback_row = next(row for row in csv_rows if row["item_id"] == "modb:unknown")
            self.assertEqual(fallback_row["classification_status"], "fallback")

            self.assertEqual(json_rows["moda:rune"]["function"], "misc_tool")
            self.assertEqual(json_rows["moda:rune"]["affinities"], ["treasure"])
            self.assertEqual(json_rows["moda:rune_alpha"]["matched_detail"], "moda:rune_*")
            self.assertEqual(json_rows["moda:unknown"]["function"], "consumable")
            self.assertEqual(json_rows["moda:unmatched"]["matched_detail"], "moda:*")
            self.assertEqual(json_rows["moda:unmatched"]["affinities"], [])

            self.assertIn("ignored count: 1", report_text)
            self.assertIn("fallback count: 1", report_text)

    def test_ignored_items_reject_partial_wildcards(self) -> None:
        raw_schema = {
            "version": 10,
            "ignored_items": ["moda:rune_*"],
            "function_trait_assignment": [
                {
                    "id": "fallback",
                    "priority": 0,
                    "match": {"summary": "fallback"},
                    "assign": {
                        "function": "unmatched",
                        "value": {"default": "none"},
                        "amount_class": {"default": "singleton"},
                    },
                },
            ],
            "affinity_trait_assignment": [
                {"id": "food", "priority": 5, "match": ["#c:foods"]},
            ],
        }

        with self.assertRaisesRegex(ValueError, "explicit item id string or namespace wildcard"):
            resolver.validate_schema(raw_schema)


if __name__ == "__main__":
    unittest.main()
