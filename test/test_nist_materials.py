"""Database-level checks for the source-preserving NIST ingestion."""

import csv
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "materials" / "nist"
SPEC = importlib.util.spec_from_file_location("nist_importer", ROOT / "scripts" / "import-nist-materials.py")
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


class NistDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = yaml.safe_load((DATABASE / "manifest.yaml").read_text(encoding="utf-8"))

    def test_index_and_manifest_are_complete(self):
        discovered = IMPORTER.discover((DATABASE / "index.html").read_bytes())
        self.assertEqual(len(discovered), self.manifest["index_entries_discovered"])
        self.assertEqual(len(discovered), self.manifest["general_material_entries"] + self.manifest["regenerator_datasets"])
        self.assertTrue(all(entry["source_url"] for entry in self.manifest["entries"]))

    def test_every_material_has_source_snapshot(self):
        for entry in self.manifest["entries"]:
            if entry["normalization_status"] != "failed":
                self.assertTrue((ROOT / entry["local_path"] / "source.html").is_file(), entry["name"])
        self.assertTrue((DATABASE / "regenerator_materials" / "source.html").is_file())

    def test_local_html_links_resolve_to_nist(self):
        index = (DATABASE / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'<base href="{IMPORTER.INDEX_URL}">', index)
        for entry in self.manifest["entries"]:
            if entry["normalization_status"] == "failed":
                continue
            source = (ROOT / entry["local_path"] / "source.html").read_text(encoding="utf-8")
            self.assertIn(f'<base href="{entry["source_url"]}">', source, entry["name"])

    def test_equation_families_evaluate(self):
        log_series = {"representation": {"family": "log10_poly", "coefficients": [1.0, 2.0]}}
        self.assertAlmostEqual(IMPORTER.evaluate(log_series, 10.0), 1000.0)
        ordinary = {"representation": {"family": "ordinary_poly_low_constant", "coefficients": [1, 2],
                                        "low_temperature_K": 3, "low_temperature_constant": 7}}
        self.assertEqual(IMPORTER.evaluate(ordinary, 2), 7)
        self.assertEqual(IMPORTER.evaluate(ordinary, 4), 9)

    def test_derived_tables_stay_in_range_and_validate(self):
        for entry in self.manifest["entries"]:
            material_path = ROOT / entry["local_path"] / "material.yaml"
            if not material_path.exists():
                continue
            material = yaml.safe_load(material_path.read_text(encoding="utf-8"))
            for series in material["series"]:
                if "derived_table" not in series:
                    continue
                with (material_path.parent / series["derived_table"]).open(encoding="utf-8") as file:
                    rows = list(csv.reader(file))[1:]
                temperatures = [float(row[0]) for row in rows]
                self.assertGreaterEqual(min(temperatures), series["equation_range_K"][0])
                self.assertLessEqual(max(temperatures), series["equation_range_K"][1])
                validation = series["derived_validation"]
                metric = validation.get("max_relative_interpolation_error")
                if metric is None:
                    metric = validation["max_normalized_absolute_interpolation_error"]
                self.assertLess(metric, validation["target"])

    def test_variants_and_unknown_equations_are_preserved(self):
        copper = yaml.safe_load((DATABASE / "copper-ofhc" / "material.yaml").read_text(encoding="utf-8"))
        self.assertEqual({s["conditions"]["rrr"] for s in copper["series"] if "rrr" in s["conditions"]},
                         {50, 100, 150, 300, 500})
        qualified = [s for path in DATABASE.glob("*/material.yaml")
                     for s in yaml.safe_load(path.read_text(encoding="utf-8"))["series"]
                     if s.get("conditions")]
        self.assertTrue(qualified)
        kevlar = yaml.safe_load((DATABASE / "kevlar-49-fiber" / "material.yaml").read_text(encoding="utf-8"))
        self.assertEqual(kevlar["normalization_status"], "manual_required")
        self.assertTrue(all(s["representation"]["family"] == "image_equation_manual_required" for s in kevlar["series"]))

    def test_list_cli_and_regenerator_shape(self):
        result = subprocess.run([sys.executable, ROOT / "scripts" / "list-materials.py", "copper",
                                 "--property", "k"], text=True, capture_output=True, check=True)
        self.assertIn("Copper (OFHC)", result.stdout)
        dataset = yaml.safe_load((DATABASE / "regenerator_materials" / "dataset.yaml").read_text(encoding="utf-8"))
        with (DATABASE / "regenerator_materials" / "volumetric_heat_capacity.csv").open(encoding="utf-8") as file:
            rows = list(csv.reader(file))
        self.assertEqual(len(rows) - 1, dataset["rows"])
        self.assertEqual(len(rows[0]), dataset["columns"])
        self.assertEqual(dataset["columns"] - 1, len(dataset["material_columns"]))


if __name__ == "__main__":
    unittest.main()
