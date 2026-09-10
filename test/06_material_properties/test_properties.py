"""Unit tests for constant, table, and Python material properties."""

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.materials import load_property
from lib.case import load_case


class PropertyTests(unittest.TestCase):
    def test_constant(self):
        prop = load_property(10.0, ".", "k")
        self.assertEqual(prop.evaluate(1.0), 10.0)
        self.assertEqual(prop.evaluate(100.0), 10.0)
        explicit = load_property({"type": "constant", "value": 12.0}, ".", "rho")
        self.assertEqual(explicit.evaluate(3.0), 12.0)

    def test_table(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "values.csv").write_text(
                "T_K,k_W_mK\n1,10\n2,20\n4,40\n", encoding="utf-8"
            )
            definition = {
                "type": "table", "file": "values.csv",
                "x": "T_K", "y": "k_W_mK",
            }
            prop = load_property(definition, root, "k")
            self.assertEqual(prop.evaluate(1.0), 10.0)
            self.assertEqual(prop.evaluate(2.0), 20.0)
            self.assertEqual(prop.evaluate(3.0), 30.0)
            for value in (0.9, 4.1, np.nan):
                with self.assertRaises(ValueError):
                    prop.evaluate(value)

    def test_invalid_table_data(self):
        cases = {
            "duplicate.csv": "T,p\n1,10\n1,20\n",
            "nonfinite_x.csv": "T,p\n1,10\nnan,20\n",
            "nonfinite_y.csv": "T,p\n1,10\n2,inf\n",
            "nonpositive.csv": "T,p\n1,10\n2,0\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename, content in cases.items():
                (root / filename).write_text(content, encoding="utf-8")
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    load_property(
                        {"type": "table", "file": filename, "x": "T", "y": "p"},
                        root, "cp",
                    )

    def test_python_callable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "valid.py").write_text(
                "def cp(T):\n    return 2 * T\n", encoding="utf-8"
            )
            prop = load_property(
                {"type": "python", "file": "valid.py", "function": "cp"},
                root, "cp",
            )
            self.assertEqual(prop.evaluate(3.0), 6.0)

            (root / "missing.py").write_text("x = 1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_property(
                    {"type": "python", "file": "missing.py", "function": "cp"},
                    root, "cp",
                )

            for filename, expression in (
                ("nan.py", "float('nan')"),
                ("zero.py", "0"),
                ("text.py", "'invalid'"),
            ):
                (root / filename).write_text(
                    f"def cp(T, **state):\n    return {expression}\n", encoding="utf-8"
                )
                prop = load_property(
                    {"type": "python", "file": filename, "function": "cp"},
                    root, "cp",
                )
                with self.assertRaises(ValueError):
                    prop.evaluate(3.0)

    def test_python_import_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Cannot import"):
                load_property(
                    {"type": "python", "file": "absent.py", "function": "cp"},
                    directory, "cp",
                )

    def test_temperature_dependent_transient_is_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "k.csv").write_text("T,k\n1,10\n4,20\n", encoding="utf-8")
            (root / "case.yaml").write_text(
                """model: {type: transient_conduction}
materials:
  sample:
    k: {type: table, file: k.csv, x: T, y: k}
    rho: 1000
    cp: 100
regions:
  bar: {material: sample}
boundary_conditions:
  hot_end: {type: fixed_temperature, value_K: 4}
  cold_end: {type: fixed_temperature, value_K: 1}
time:
  initial_condition: {split_x_m: 0.5, left_T_K: 4, right_T_K: 1}
  dt_s: 1
  end_s: 2
""",
                encoding="utf-8",
            )
            loaded = load_case(root / "case.yaml")
            self.assertFalse(
                loaded["_region_properties"]["bar"]["k"].is_constant
            )

    def test_uniform_initial_condition_and_boundary_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "case.yaml").write_text(
                """model: {type: transient_conduction}
regions:
  solid: {k: 10, rho: 1000, cp: 100}
boundary_conditions:
  fixed_surface: {type: fixed_temperature, value_K: 4}
time:
  initial_condition: {type: uniform, value_K: 2}
  dt_s: 1
  end_s: 2
""",
                encoding="utf-8",
            )
            loaded = load_case(root / "case.yaml")
            self.assertEqual(loaded["time"]["initial_condition"]["type"], "uniform")
            loaded["time"]["initial_condition"]["type"] = "unknown"
            (root / "case.yaml").write_text(
                """model: {type: transient_conduction}
regions:
  solid: {k: 10, rho: 1000, cp: 100}
boundary_conditions:
  fixed_surface: {type: fixed_temperature, value_K: 4}
time:
  initial_condition: {type: unknown, value_K: 2}
  dt_s: 1
  end_s: 2
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Unsupported.*initial_condition"):
                load_case(root / "case.yaml")


if __name__ == "__main__":
    unittest.main()
