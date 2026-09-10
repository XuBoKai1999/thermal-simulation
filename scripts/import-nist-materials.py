#!/usr/bin/env python3
"""Mirror and normalize the official NIST cryogenic materials index."""

from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import math
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from datetime import date

import yaml


INDEX_URL = "https://trc.nist.gov/cryogenics/materials/materialproperties.htm"
ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "materials" / "nist"
USER_AGENT = "thermal-simulation NIST mirror/1.0 (source-preserving research tool)"
COEFFICIENTS = tuple("abcdefghijkl")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = []
        self.images = []
        self.tables = []
        self.title = []
        self.text = []
        self._anchor = None
        self._image = None
        self._table = None
        self._table_depth = 0
        self._row = None
        self._cell = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self._anchor = [attrs["href"], []]
        elif tag == "img" and attrs.get("src"):
            self.images.append((attrs["src"], attrs.get("alt", "")))
        elif tag == "table":
            if self._table is None:
                self._table = []
            self._table_depth += 1
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag == "title":
            self._in_title = True

    def handle_data(self, data):
        self.text.append(data)
        if self._anchor is not None:
            self._anchor[1].append(data)
        if self._cell is not None:
            self._cell.append(data)
        if self._in_title:
            self.title.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor is not None:
            self.anchors.append((self._anchor[0], clean(" ".join(self._anchor[1]))))
            self._anchor = None
        elif tag in {"td", "th"} and self._cell is not None:
            self._row.append(clean(" ".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self._table_depth -= 1
            if self._table_depth == 0:
                if self._table:
                    self.tables.append(self._table)
                self._table = None
        elif tag == "title":
            self._in_title = False


def clean(value):
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def decode(raw):
    for encoding in ("utf-8", "windows-1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError("Cannot decode NIST page")


def navigable_snapshot(raw, source_url):
    """Preserve page content while making relative links resolve to NIST, not C:."""
    text = decode(raw)
    base = f'<base href="{source_url}">'
    if re.search(r"<base\b", text, re.I):
        text = re.sub(r"<base\b[^>]*>", base, text, count=1, flags=re.I)
    elif re.search(r"<head\b[^>]*>", text, re.I):
        text = re.sub(r"(<head\b[^>]*>)", rf"\1\n  {base}", text, count=1, flags=re.I)
    else:
        text = base + "\n" + text
    return text.encode("utf-8")


def fetch(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=45) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Cannot download {url}: {error}") from error


def parse(raw):
    parser = PageParser()
    parser.feed(decode(raw))
    return parser


def slugify(name):
    value = name.lower().replace("/", " ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or hashlib.sha256(name.encode()).hexdigest()[:12]


def discover(index_raw):
    entries = []
    seen = set()
    for href, name in parse(index_raw).anchors:
        url = quote(urljoin(INDEX_URL, href), safe=":/?&=%#")
        path = unquote(urlparse(url).path).lower()
        if (not name or url in seen or "/materials/" not in path
                or path.endswith("materialproperties.htm") or "reference" in path):
            continue
        if not path.endswith((".htm", ".html")):
            continue
        seen.add(url)
        entries.append({"name": name, "url": url})
    return entries


def page_identity(parser, fallback):
    text = clean(" ".join(parser.title))
    title = text or fallback
    match = re.search(r"Material Properties:\s*(.*)", title, re.I)
    name = clean(match.group(1)) if match else fallback
    uns = None
    visible_text = clean(" ".join(parser.text))
    match = re.search(r"\bUNS\s+([A-Z][A-Z0-9/ ]+?)(?:\)|Data|$)", visible_text, re.I)
    if match:
        uns = clean(match.group(1)).rstrip(")")
    revision = None
    match = re.search(r"rev(?:ised|ision|\.)?\s*([0-9][0-9/\-]+)", visible_text, re.I)
    if match:
        revision = match.group(1)
    return title, uns, revision


def number(value):
    value = clean(value).replace("−", "-").replace("–", "-")
    value = re.sub(r"(?<=\d)\s*[Kk]$", "", value)
    return float(value)


def range_pair(value):
    values = re.findall(r"\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?", value)
    return [float(values[0]), float(values[1])] if len(values) >= 2 else None


PROPERTY_MAP = {
    "thermal conductivity": ("thermal_conductivity", "k"),
    "specific heat": ("specific_heat", "cp"),
    "linear expansion": ("linear_expansion", "delta_l_over_l"),
    "expansion coefficient": ("thermal_expansion_coefficient", "alpha"),
    "thermal expansion coefficient": ("thermal_expansion_coefficient", "alpha"),
    "young's modulus": ("youngs_modulus", "E"),
    "youngs modulus": ("youngs_modulus", "E"),
}


def property_name(header):
    value = clean(re.sub(r"RRR\s*=.*", "", header, flags=re.I)).lower()
    for label, result in sorted(PROPERTY_MAP.items(), key=lambda item: -len(item[0])):
        if label in value:
            return result
    return None


def series_conditions(header, property_id):
    conditions = {}
    canonical = property_id.replace("_", " ")
    if clean(header).lower() != canonical:
        conditions["source_label"] = header
    density = re.search(r"density\s*[:=]?\s*([0-9.]+)\s*kg\s*/\s*m", header, re.I)
    if density:
        conditions["density_kg_m3"] = float(density.group(1))
    direction = re.search(r"\b(normal|warp|parallel|perpendicular|longitudinal|transverse)\b(?:\s+direction)?", header, re.I)
    if direction:
        conditions["direction"] = direction.group(1).lower()
    gas = re.search(r"\b(helium|nitrogen|freon|CO\s*2|air|He)\b(?:\s+(?:fill|filled|blown))?", header, re.I)
    if gas:
        conditions["fill_gas"] = clean(gas.group(0))
    return conditions


def normalize_standard_tables(parser, page_text, slug):
    series = []
    for table_index, rows in enumerate(parser.tables):
        units_rows = [i for i, row in enumerate(rows) if row and "UNITS" in row[0].upper()]
        for segment, units_row in enumerate(units_rows):
            if units_row == 0:
                continue
            stop = units_rows[segment + 1] if segment + 1 < len(units_rows) else len(rows)
            headers = rows[units_row - 1][1:]
            units = rows[units_row][1:]
            width = min(len(headers), len(units))
            for column in range(width):
                prop = property_name(headers[column])
                if not prop:
                    continue
                coefficients = []
                data_range = equation_range = fit_error = None
                low_temperature = low_constant = None
                for row in rows[units_row + 1:stop]:
                    if len(row) <= column + 1:
                        continue
                    key, value = row[0].lower(), row[column + 1]
                    coefficient_key = re.fullmatch(r"([a-l])[^a-z]*", key)
                    if coefficient_key:
                        try:
                            parsed = number(value)
                        except ValueError:
                            parsed = None
                        if coefficient_key.group(1) == "f" and prop[0] in {"linear_expansion", "youngs_modulus"} and ">" in key:
                            low_constant = parsed
                        else:
                            coefficients.append(parsed)
                    elif "t low" in key or "tlow" in key:
                        try:
                            low_temperature = number(value)
                        except ValueError:
                            pass
                    elif "data range" in key:
                        data_range = range_pair(value)
                    elif "equation range" in key or key == "low range":
                        found = range_pair(value)
                        if found:
                            equation_range = found
                    elif "error" in key:
                        fit_error = clean(value)
                # OFHC tables express low/high in separate rows.
                if equation_range is None:
                    low_row = next((row for row in rows if row and row[0].lower() == "low range"), None)
                    high_row = next((row for row in rows if row and row[0].lower() == "high range"), None)
                    if low_row and high_row and len(low_row) > column + 1 and len(high_row) > column + 1:
                        equation_range = [number(low_row[column + 1]), number(high_row[column + 1])]
                        data_range = list(equation_range)
                if not coefficients or equation_range is None or any(v is None for v in coefficients):
                    continue
                header = headers[column]
                conditions = series_conditions(header, prop[0])
                rrr = re.search(r"RRR\s*=\s*(\d+)", header, re.I)
                if rrr:
                    conditions["rrr"] = int(rrr.group(1))
                if slug == "copper-ofhc" and prop[0] == "thermal_conductivity":
                    family = "ofhc_copper_conductivity"
                elif prop[0] in {"linear_expansion", "youngs_modulus"}:
                    family = "ordinary_poly_low_constant" if low_temperature is not None else "ordinary_poly"
                else:
                    family = "log10_poly"
                representation = {"family": family, "coefficients": coefficients}
                if low_temperature is not None:
                    representation.update({"low_temperature_K": low_temperature,
                                           "low_temperature_constant": low_constant})
                series_id = f"{prop[1]}-{table_index + 1}-{segment + 1}-{column + 1}"
                if rrr:
                    series_id = f"k-rrr-{rrr.group(1)}"
                series.append({
                "id": series_id,
                "property": prop[0],
                "symbol": prop[1],
                "unit": units[column],
                "conditions": conditions,
                "representation": representation,
                "data_range_K": data_range,
                "equation_range_K": equation_range,
                "source_fit_error": fit_error,
                })
    return series


def evaluate(series, temperature):
    coefficients = series["representation"]["coefficients"]
    family = series["representation"]["family"]
    if family == "log10_poly":
        x = math.log10(temperature)
        return 10 ** sum(coefficient * x ** power for power, coefficient in enumerate(coefficients))
    if family == "ofhc_copper_conductivity":
        c = coefficients + [0.0] * (9 - len(coefficients))
        root = math.sqrt(temperature)
        numerator = c[0] + c[2] * root + c[4] * temperature + c[6] * temperature * root + c[8] * temperature ** 2
        denominator = 1 + c[1] * root + c[3] * temperature + c[5] * temperature * root + c[7] * temperature ** 2
        return 10 ** (numerator / denominator)
    if family in {"ordinary_poly", "ordinary_poly_low_constant"}:
        if family == "ordinary_poly_low_constant" and temperature < series["representation"]["low_temperature_K"]:
            return series["representation"]["low_temperature_constant"]
        return sum(coefficient * temperature ** power for power, coefficient in enumerate(coefficients))
    raise ValueError(f"Unsupported equation family {family}")


def derived_table(series, directory):
    low, high = series["equation_range_K"]
    family = series["representation"]["family"]
    if low < 0 or high <= low or (low == 0 and family not in {"ordinary_poly", "ordinary_poly_low_constant"}):
        return None, "equation range is incompatible with this equation family"
    points = 65
    while points <= 4097:
        temperatures = ([low + (high - low) * i / (points - 1) for i in range(points)]
                        if low == 0 else
                        [low * (high / low) ** (i / (points - 1)) for i in range(points)])
        values = [evaluate(series, temperature) for temperature in temperatures]
        worst = 0.0
        property_scale = max(abs(value) for value in values)
        relative_metric = series["property"] not in {"linear_expansion", "thermal_expansion_coefficient"}
        for i in range(points - 1):
            for fraction in (0.25, 0.5, 0.75):
                temperature = (temperatures[i] + (temperatures[i + 1] - temperatures[i]) * fraction
                               if temperatures[i] == 0 else
                               temperatures[i] * (temperatures[i + 1] / temperatures[i]) ** fraction)
                exact = evaluate(series, temperature)
                linear = values[i] + (values[i + 1] - values[i]) * (
                    (temperature - temperatures[i]) / (temperatures[i + 1] - temperatures[i])
                )
                denominator = abs(exact) if relative_metric else property_scale
                worst = max(worst, abs(linear - exact) / denominator if denominator else abs(linear - exact))
        if worst < 0.001:
            break
        points = points * 2 - 1
    if worst >= 0.001:
        return None, f"interpolation error {worst:.6%} exceeds 0.1%"
    filename = f"{series['id']}.csv"
    path = directory / filename
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["temperature_K", f"value_{series['unit']}"])
        writer.writerows(zip((f"{v:.12g}" for v in temperatures), (f"{v:.12g}" for v in values)))
    series["derived_table"] = filename
    series["derived_validation"] = {
        "method": ("dense quarter-point maximum relative error" if relative_metric else
                   "dense quarter-point maximum absolute error normalized by peak magnitude"),
        "max_relative_interpolation_error": float(worst) if relative_metric else None,
        "max_normalized_absolute_interpolation_error": None if relative_metric else float(worst),
        "target": 0.001,
        "sample_count": points,
    }
    return filename, None


def save_equation_assets(parser, source_url, directory, include_all=False):
    saved = []
    for src, alt in parser.images:
        label = (src + " " + alt).lower()
        if any(word in label for word in ("plot", "logo", "button", "return")):
            continue
        if not include_all and not any(word in label for word in ("equ", "formula", "image")):
            continue
        url = urljoin(source_url, src)
        suffix = Path(urlparse(url).path).suffix.lower() or ".bin"
        name = f"equation-{len(saved) + 1}{suffix}"
        try:
            (directory / name).write_bytes(fetch(url))
            saved.append({"file": name, "source_url": url})
        except RuntimeError:
            pass
    return saved


def normalize_material(entry, raw, directory, retrieved):
    for path in (*directory.glob("*.csv"), *directory.glob("equation-*")):
        path.unlink()
    for stale in directory.glob("*.csv"):
        stale.unlink()
    for stale in directory.glob("equation-*"):
        stale.unlink()
    parser = parse(raw)
    title, uns, revision = page_identity(parser, entry["name"])
    page_text = decode(raw)
    slug = directory.name
    series = normalize_standard_tables(parser, page_text, slug)
    standard_log = bool(re.search(r"log\s*<sub>\s*10\s*</sub>\s*(?:<[^>]+>)*\s*y", page_text, re.I))
    special_image_equation = bool(parser.images and "equation" in page_text.lower() and not standard_log
                                  and slug != "copper-ofhc")
    if special_image_equation:
        for item in series:
            if item["representation"]["family"] == "log10_poly":
                item["representation"]["family"] = "image_equation_manual_required"
    failures = []
    for item in series:
        if item["representation"]["family"] == "image_equation_manual_required":
            failures.append(f"{item['id']}: equation is image-only; coefficients preserved but not evaluated")
            continue
        _, error = derived_table(item, directory)
        if error:
            failures.append(f"{item['id']}: {error}")
    equation_images = special_image_equation
    assets = save_equation_assets(parser, entry["url"], directory, include_all=True) if equation_images else []
    if not series or special_image_equation:
        status = "manual_required"
        if not series:
            failures.append("no unambiguous supported equation parsed from HTML")
    elif equation_images or failures:
        status = "partially_normalized"
        if equation_images:
            failures.append("one or more equations are image-only and were not guessed")
    else:
        status = "fully_normalized"
    material = {
        "id": f"nist.{slug}",
        "name": entry["name"],
        "source": {
            "organization": "NIST",
            "url": entry["url"],
            "retrieved": retrieved,
            "sha256": hashlib.sha256(navigable_snapshot(raw, entry["url"])).hexdigest(),
            "official_content_sha256": hashlib.sha256(raw).hexdigest(),
            "page_title": title,
            "revision": revision,
        },
        "identity": {"uns": uns, "grade": None},
        "normalization_status": status,
        "normalization_notes": failures,
        "equation_assets": assets,
        "series": series,
    }
    (directory / "material.yaml").write_text(
        yaml.safe_dump(material, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return material


def normalize_regenerator(entry, raw, directory, retrieved):
    for path in directory.glob("*.csv"):
        path.unlink()
    parser = parse(raw)
    candidates = [table for table in parser.tables if any(
        row and "Temperature" in row[0] and len(row) > 10 for row in table
    )]
    if not candidates:
        raise ValueError("Regenerator table not found")
    table = max(candidates, key=len)
    header_index = next(i for i, row in enumerate(table) if row and "Temperature" in row[0] and len(row) > 10)
    headers = table[header_index]
    rows = []
    for row in table[header_index + 1:]:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        try:
            float(row[0])
        except (ValueError, IndexError):
            continue
        rows.append(row[:len(headers)])
    output = directory / "volumetric_heat_capacity.csv"
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
    temperatures = [float(row[0]) for row in rows]
    missing = sum(value == "" for row in rows for value in row[1:])
    dataset = {
        "id": "nist.regenerator-materials",
        "name": entry["name"],
        "source": {"organization": "NIST", "url": entry["url"], "retrieved": retrieved,
                   "sha256": hashlib.sha256(navigable_snapshot(raw, entry["url"])).hexdigest(),
                   "official_content_sha256": hashlib.sha256(raw).hexdigest()},
        "property": "volumetric_heat_capacity",
        "temperature_unit": "K",
        "original_unit": "J/(cm^3 K)",
        "material_columns": headers[1:],
        "missing_value_semantics": "blank cell means NIST provides no value; it is not zero",
        "rows": len(rows),
        "columns": len(headers),
        "temperature_range_K": [min(temperatures), max(temperatures)],
        "missing_cells": missing,
        "derived_table": output.name,
        "normalization_status": "fully_normalized",
    }
    (directory / "dataset.yaml").write_text(
        yaml.safe_dump(dataset, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return dataset


def previous_retrieved(metadata_path, checksum):
    if metadata_path.exists():
        data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        source = data.get("source", {})
        if source.get("official_content_sha256", source.get("sha256")) == checksum and source.get("retrieved"):
            return str(source["retrieved"])
    return date.today().isoformat()


def write_readme(manifest, regenerator):
    entries = manifest["entries"]
    counts = {status: sum(e["normalization_status"] == status for e in entries)
              for status in ("fully_normalized", "partially_normalized", "manual_required", "failed")}
    property_counts = {}
    csv_count = 1 if regenerator else 0
    worst = 0.0
    for entry in entries:
        for prop, count in entry.get("property_series_counts", {}).items():
            property_counts[prop] = property_counts.get(prop, 0) + count
        csv_count += entry.get("derived_csv_count", 0)
        worst = max(worst, entry.get("worst_interpolation_error", 0.0))
    flagged = [e for e in entries if e["normalization_status"] in {"manual_required", "failed"}]
    lines = [
        "# NIST Cryogenic Materials Database",
        "",
        "Source-preserving mirror of the official NIST Cryogenic Materials Database. Original",
        "`source.html` snapshots are authoritative and contain only one injected `<base>` tag for",
        "working links. Metadata records both the official response checksum and snapshot checksum; generated CSV files",
        "are derived caches restricted to each NIST equation range. No external densities or",
        "extrapolated values are included.",
        "",
        "## Ingestion summary",
        "",
        f"- Index URL: {INDEX_URL}",
        f"- Index entries discovered: {manifest['index_entries_discovered']}",
        f"- General material pages downloaded: {manifest['downloaded']}",
        f"- Failed downloads: {manifest['failed']}",
        f"- Fully normalized: {counts['fully_normalized']}",
        f"- Partially normalized: {counts['partially_normalized']}",
        f"- Manual required: {counts['manual_required']}",
        f"- Derived CSV files: {csv_count}",
        f"- Worst validated interpolation metric: {worst:.6%}",
        "",
        "## Property series counts",
        "",
    ]
    lines += [f"- {name}: {count}" for name, count in sorted(property_counts.items())]
    lines += ["", "## Manual-required or failed pages", ""]
    lines += ([f"- {e['name']}: {e['normalization_status']} — {'; '.join(e.get('notes', []))}"
               for e in flagged] or ["- None"])
    lines += [
        "", "## Solver integration", "",
        "The database exists, but `case.yaml` external material references are not implemented.",
        "Select and review a series explicitly before copying it into a case-local solver input.",
    ]
    (DATABASE / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    global INDEX_URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-url", default=INDEX_URL)
    args = parser.parse_args()
    INDEX_URL = args.index_url
    DATABASE.mkdir(parents=True, exist_ok=True)
    index_raw = fetch(INDEX_URL)
    index_snapshot = navigable_snapshot(index_raw, INDEX_URL)
    (DATABASE / "index.html").write_bytes(index_snapshot)
    discovered = discover(index_raw)
    manifest_entries = []
    regenerator = None
    for entry in discovered:
        is_regenerator = "regenerator" in entry["name"].lower()
        slug = "regenerator_materials" if is_regenerator else slugify(entry["name"])
        directory = DATABASE / slug
        directory.mkdir(parents=True, exist_ok=True)
        metadata_path = directory / ("dataset.yaml" if is_regenerator else "material.yaml")
        try:
            raw = fetch(entry["url"])
            checksum = hashlib.sha256(raw).hexdigest()
            retrieved = previous_retrieved(metadata_path, checksum)
            (directory / "source.html").write_bytes(navigable_snapshot(raw, entry["url"]))
            if is_regenerator:
                regenerator = normalize_regenerator(entry, raw, directory, retrieved)
                continue
            material = normalize_material(entry, raw, directory, retrieved)
            validations = [v for s in material["series"] for v in (
                s.get("derived_validation", {}).get("max_relative_interpolation_error"),
                s.get("derived_validation", {}).get("max_normalized_absolute_interpolation_error"),
            ) if v is not None]
            manifest_entries.append({
                "id": material["id"], "name": material["name"], "source_url": entry["url"],
                "local_path": str(directory.relative_to(ROOT)).replace("\\", "/"),
                "normalization_status": material["normalization_status"],
                "properties_found": sorted({s["property"] for s in material["series"]}),
                "property_series_counts": {
                    name: sum(s["property"] == name for s in material["series"])
                    for name in sorted({s["property"] for s in material["series"]})
                },
                "variants_found": [s["conditions"] for s in material["series"] if s["conditions"]],
                "derived_csv_count": sum("derived_table" in s for s in material["series"]),
                "worst_interpolation_error": max(validations, default=0.0),
                "notes": material["normalization_notes"],
            })
        except Exception as error:
            manifest_entries.append({
                "id": f"nist.{slug}", "name": entry["name"], "source_url": entry["url"],
                "local_path": str(directory.relative_to(ROOT)).replace("\\", "/"),
                "normalization_status": "failed", "properties_found": [], "variants_found": [],
                "property_series_counts": {},
                "derived_csv_count": 0, "worst_interpolation_error": 0.0, "notes": [str(error)],
            })
            print(f"ERROR {entry['name']}: {error}", file=sys.stderr)
    manifest = {
        "source": {"organization": "NIST", "index_url": INDEX_URL,
                   "retrieved": date.today().isoformat(),
                   "sha256": hashlib.sha256(index_snapshot).hexdigest(),
                   "official_content_sha256": hashlib.sha256(index_raw).hexdigest()},
        "index_entries_discovered": len(discovered),
        "general_material_entries": len(manifest_entries),
        "regenerator_datasets": 1 if regenerator else 0,
        "downloaded": sum(e["normalization_status"] != "failed" for e in manifest_entries),
        "failed": sum(e["normalization_status"] == "failed" for e in manifest_entries),
        "entries": manifest_entries,
    }
    (DATABASE / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    write_readme(manifest, regenerator)
    print(f"Discovered {len(discovered)} index entries; material pages: {len(manifest_entries)}; failures: {manifest['failed']}")


if __name__ == "__main__":
    main()
