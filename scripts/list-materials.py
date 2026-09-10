#!/usr/bin/env python3
"""List normalized NIST cryogenic material metadata without importing FEniCSx."""

import argparse
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "materials" / "nist" / "manifest.yaml"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="case-insensitive material-name filter")
    parser.add_argument("--property", dest="property_name", help="property name or symbol, e.g. k")
    parser.add_argument("--status", help="normalization status")
    args = parser.parse_args()
    if not MANIFEST.exists():
        parser.error("NIST manifest is missing; run scripts/import-nist-materials.py first")
    entries = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["entries"]
    for entry in entries:
        if args.query and args.query.lower() not in entry["name"].lower():
            continue
        properties = entry["properties_found"]
        aliases = {"k": "thermal_conductivity", "cp": "specific_heat",
                   "alpha": "thermal_expansion_coefficient", "e": "youngs_modulus"}
        requested = aliases.get((args.property_name or "").lower(), args.property_name)
        if requested and requested not in properties:
            continue
        if args.status and args.status != entry["normalization_status"]:
            continue
        material = yaml.safe_load((ROOT / entry["local_path"] / "material.yaml").read_text(encoding="utf-8"))
        ranges = sorted({tuple(series["equation_range_K"]) for series in material["series"]
                         if series.get("equation_range_K")})
        variants = [series["conditions"] for series in material["series"] if series.get("conditions")]
        print(f"{entry['name']} | properties={','.join(properties) or '-'} | variants={variants or '-'} | "
              f"coverage_K={ranges or '-'} | status={entry['normalization_status']} | {entry['local_path']}")
    dataset_path = ROOT / "materials" / "nist" / "regenerator_materials" / "dataset.yaml"
    if dataset_path.exists():
        dataset = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))
        requested = (args.property_name or "").lower()
        show = (not args.query or args.query.lower() in dataset["name"].lower())
        show = show and (not requested or requested in {"volumetric_heat_capacity", "cv"})
        show = show and (not args.status or args.status == dataset["normalization_status"])
        if show:
            print(f"{dataset['name']} | properties=volumetric_heat_capacity | variants={len(dataset['material_columns'])} columns | "
                  f"coverage_K={[tuple(dataset['temperature_range_K'])]} | status={dataset['normalization_status']} | "
                  "materials/nist/regenerator_materials")


if __name__ == "__main__":
    main()
