#!/usr/bin/env python3
"""
ADR01 paper downloader

Attempts all 11 ADR01 references.

Strategy for each paper:
1. Try known direct/open URLs encoded below.
2. If a DOI exists, query OpenAlex for OA PDF locations.
3. Query Crossref for publisher-provided resource links.
4. Resolve the DOI landing page and extract likely PDF links.
5. Try each unique candidate, verify that the downloaded file is actually a PDF.

This does NOT bypass paywalls or authentication. If a paper is not legally accessible
without institutional credentials, it will be reported as FAILED rather than silently
saving an HTML/paywall page as a PDF.
"""

from __future__ import annotations

import csv
import hashlib
import html.parser
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urljoin

try:
    import requests
except ImportError:
    print("Missing dependency: requests")
    print("Install it with:")
    print("    python -m pip install requests")
    raise SystemExit(2)


OUT_DIR = Path("ADR01_papers")
STATUS_CSV = OUT_DIR / "download-status.csv"
LOG_FILE = OUT_DIR / "download.log"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/152.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}

TIMEOUT = (20, 180)  # connect, read seconds
MIN_PDF_BYTES = 1024


@dataclass(frozen=True)
class Paper:
    item: str
    title: str
    doi: str | None
    direct_urls: tuple[str, ...] = ()


PAPERS: tuple[Paper, ...] = (
    Paper(
        item="01_Hust_Lankford_1984_NBSIR84-3007.pdf",
        title="Thermal conductivity of aluminum, copper, iron, and tungsten for temperatures from 1 K to the melting point",
        doi=None,
        direct_urls=(
            "https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nbsir84-3007.pdf",
        ),
    ),
    Paper(
        item="02_White_Collocott_1984_Cu_W_heat_capacity.pdf",
        title="Heat Capacity of Reference Materials: Cu and W",
        doi="10.1063/1.555728",
        direct_urls=(
            "https://pubs.aip.org/jpr/article-pdf/13/4/1251/12647720/1251_1_online.pdf",
            "https://srd.nist.gov/jpcrdreprint/1.555728.pdf",
        ),
    ),
    Paper(
        item="03_Simon_Drexler_Reed_1992_NIST_Monograph177.pdf",
        title="Properties of Copper and Copper Alloys at Cryogenic Temperatures",
        doi=None,
        direct_urls=(
            "https://nvlpubs.nist.gov/nistpubs/Legacy/MONO/nistmonograph177.pdf",
        ),
    ),
    Paper(
        item="04_Runyan_Jones_2008_lowT_support_materials.pdf",
        title=(
            "Thermal Conductivity of Thermally-Isolating Polymeric and Composite "
            "Structural Support Materials Between 0.3 and 4 K"
        ),
        doi="10.1016/j.cryogenics.2008.06.002",
        direct_urls=(
            "https://arxiv.org/pdf/0806.1921",
            "https://export.arxiv.org/pdf/0806.1921",
        ),
    ),
    Paper(
        item="05_DiPirro_Shirron_2014_heat_switches_for_ADRs.pdf",
        title="Heat switches for ADRs",
        doi="10.1016/j.cryogenics.2014.03.017",
        direct_urls=(
            "https://ntrs.nasa.gov/api/citations/20150008253/downloads/20150008253.pdf",
            "https://files.core.ac.uk/download/pdf/42712036.pdf",
            "https://files01.core.ac.uk/download/pdf/42712036.pdf",
        ),
    ),
    Paper(
        item="06_Fisher_Brodale_Hornung_Giauque_1973_GGG_magnetothermodynamics.pdf",
        title=(
            "Magnetothermodynamics of gadolinium gallium garnet. I. "
            "Heat capacity, entropy, magnetic moment from 0.5 to 4.2 K, "
            "with fields to 90 kG along the [100] axis"
        ),
        doi="10.1063/1.1680677",
        direct_urls=(
            "https://pubs.aip.org/jcp/article-pdf/59/9/4652/18876141/4652_1_online.pdf",
        ),
    ),
    Paper(
        item="07_Daudin_Lagnier_Salce_1982_GGG_thermodynamic_properties.pdf",
        title=(
            "Thermodynamic properties of the gadolinium gallium garnet, "
            "Gd3Ga5O12, between 0.05 and 25 K"
        ),
        doi="10.1016/0304-8853(82)90092-0",
        direct_urls=(
            "https://www.sciencedirect.com/science/article/pii/0304885382900920/pdfft",
        ),
    ),
    Paper(
        item="08_Slack_Oliver_1971_garnet_thermal_conductivity.pdf",
        title="Thermal Conductivity of Garnets and Phonon Scattering by Rare-Earth Ions",
        doi="10.1103/PhysRevB.4.592",
        direct_urls=(
            "https://journals.aps.org/prb/pdf/10.1103/PhysRevB.4.592",
        ),
    ),
    Paper(
        item="09_Walker_Anderson_1981_G10_G10CR.pdf",
        title=(
            "Thermal conductivity and specific heat of a glass-epoxy composite "
            "at temperatures below 4 K"
        ),
        doi="10.1063/1.1136614",
        direct_urls=(
            "https://pubs.aip.org/rsi/article-pdf/52/3/471/19288335/471_1_online.pdf",
        ),
    ),
    Paper(
        item="10_Catarino_Paine_2011_3He_gas_gap_heat_switch.pdf",
        title="3He gas gap heat switch",
        doi="10.1016/j.cryogenics.2010.10.009",
        direct_urls=(
            "https://www.sciencedirect.com/science/article/pii/S0011227510002018/pdfft",
        ),
    ),
    Paper(
        item="11_Mashimo_et_al_2006_GGG_density.pdf",
        title=(
            "Transition to a virtually incompressible oxide phase at a shock "
            "pressure of 120 GPa (1.2 Mbar): Gd3Ga5O12"
        ),
        doi="10.1103/PhysRevLett.96.105504",
        direct_urls=(
            "https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.96.105504",
        ),
    ),
)


def log(message: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp}\t{message}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < MIN_PDF_BYTES:
        return False
    try:
        with path.open("rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def looks_like_pdf_link(url: str) -> bool:
    s = url.lower()
    return (
        ".pdf" in s
        or "/pdf/" in s
        or "/pdf?" in s
        or "article-pdf" in s
        or "pdfft" in s
        or "download/pdf" in s
        or "download?filename=" in s
    )


def openalex_candidates(session: requests.Session, doi: str) -> list[str]:
    api = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='')}"
    try:
        r = session.get(api, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            log(f"OPENALEX HTTP {r.status_code} for DOI {doi}")
            return []
        data = r.json()
    except Exception as e:
        log(f"OPENALEX error for DOI {doi}: {e}")
        return []

    urls: list[str] = []
    for loc_key in ("best_oa_location", "primary_location"):
        loc = data.get(loc_key) or {}
        if loc.get("pdf_url"):
            urls.append(loc["pdf_url"])

    for loc in data.get("locations") or []:
        if loc.get("pdf_url"):
            urls.append(loc["pdf_url"])

    return dedupe(urls)


def crossref_candidates(session: requests.Session, doi: str) -> list[str]:
    api = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    try:
        r = session.get(api, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            log(f"CROSSREF HTTP {r.status_code} for DOI {doi}")
            return []
        msg = r.json().get("message", {})
    except Exception as e:
        log(f"CROSSREF error for DOI {doi}: {e}")
        return []

    urls: list[str] = []
    for link in msg.get("link") or []:
        url = link.get("URL")
        ctype = (link.get("content-type") or "").lower()
        if url and ("pdf" in ctype or looks_like_pdf_link(url)):
            urls.append(url)

    return dedupe(urls)


def doi_page_pdf_candidates(session: requests.Session, doi: str) -> list[str]:
    doi_url = f"https://doi.org/{doi}"
    try:
        r = session.get(
            doi_url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        if r.status_code >= 400:
            log(f"DOI LANDING HTTP {r.status_code} for DOI {doi}")
            return []
        ctype = (r.headers.get("content-type") or "").lower()
        if "application/pdf" in ctype:
            return [r.url]

        parser = LinkParser()
        parser.feed(r.text)
        urls = [
            urljoin(r.url, href)
            for href in parser.links
            if looks_like_pdf_link(urljoin(r.url, href))
        ]
        return dedupe(urls)
    except Exception as e:
        log(f"DOI LANDING error for DOI {doi}: {e}")
        return []


def build_candidates(session: requests.Session, paper: Paper) -> list[str]:
    candidates: list[str] = list(paper.direct_urls)

    if paper.doi:
        # Dynamic discovery can recover OA repository copies that were not known when
        # this script was written.
        candidates.extend(openalex_candidates(session, paper.doi))
        candidates.extend(crossref_candidates(session, paper.doi))
        candidates.extend(doi_page_pdf_candidates(session, paper.doi))

    return dedupe(candidates)


def download_url(
    session: requests.Session,
    url: str,
    dest: Path,
) -> tuple[bool, str]:
    part = dest.with_suffix(dest.suffix + ".part")
    part.unlink(missing_ok=True)

    try:
        log(f"GET    {url}")
        with session.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as r:
            final_url = r.url
            status = r.status_code
            ctype = r.headers.get("content-type", "")

            if status >= 400:
                return False, f"HTTP {status}; final={final_url}"

            with part.open("wb") as f:
                for chunk in r.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        f.write(chunk)

        if not is_pdf(part):
            size = part.stat().st_size if part.exists() else 0
            part.unlink(missing_ok=True)
            return (
                False,
                f"not PDF; content-type={ctype!r}; bytes={size}; final={final_url}",
            )

        part.replace(dest)
        return (
            True,
            f"content-type={ctype!r}; final={final_url}",
        )

    except requests.exceptions.SSLError as e:
        part.unlink(missing_ok=True)
        return False, f"SSL error: {e}"
    except requests.exceptions.Timeout as e:
        part.unlink(missing_ok=True)
        return False, f"timeout: {e}"
    except requests.exceptions.RequestException as e:
        part.unlink(missing_ok=True)
        return False, f"request error: {e}"
    except OSError as e:
        part.unlink(missing_ok=True)
        return False, f"file error: {e}"


def write_status(rows: Iterable[dict[str, object]]) -> None:
    fields = (
        "item",
        "status",
        "bytes",
        "sha256",
        "title",
        "doi",
        "source",
        "candidates_tried",
        "note",
    )
    with STATUS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("", encoding="utf-8")
    rows: list[dict[str, object]] = []

    with requests.Session() as session:
        for idx, paper in enumerate(PAPERS, start=1):
            print()
            log(f"=== [{idx}/{len(PAPERS)}] {paper.title} ===")
            dest = OUT_DIR / paper.item

            if is_pdf(dest):
                rows.append(
                    {
                        "item": paper.item,
                        "status": "EXISTS",
                        "bytes": dest.stat().st_size,
                        "sha256": sha256(dest),
                        "title": paper.title,
                        "doi": paper.doi or "",
                        "source": "existing file",
                        "candidates_tried": 0,
                        "note": "",
                    }
                )
                log(f"EXISTS {paper.item}")
                write_status(rows)
                continue

            candidates = build_candidates(session, paper)
            log(f"CANDIDATES {len(candidates)}")

            errors: list[str] = []
            success = False

            for n, url in enumerate(candidates, start=1):
                log(f"TRY {n}/{len(candidates)}")
                ok, note = download_url(session, url, dest)
                if ok:
                    rows.append(
                        {
                            "item": paper.item,
                            "status": "DOWNLOADED",
                            "bytes": dest.stat().st_size,
                            "sha256": sha256(dest),
                            "title": paper.title,
                            "doi": paper.doi or "",
                            "source": url,
                            "candidates_tried": n,
                            "note": note,
                        }
                    )
                    log(f"OK     {paper.item} <= {url}")
                    success = True
                    break

                log(f"FAILED {url} -> {note}")
                errors.append(f"{url} -> {note}")

            if not success:
                doi_note = (
                    f" DOI: https://doi.org/{paper.doi}"
                    if paper.doi else ""
                )
                rows.append(
                    {
                        "item": paper.item,
                        "status": "FAILED",
                        "bytes": 0,
                        "sha256": "",
                        "title": paper.title,
                        "doi": paper.doi or "",
                        "source": "",
                        "candidates_tried": len(candidates),
                        "note": (
                            "All discovered download candidates failed."
                            + doi_note
                            + " | "
                            + " | ".join(errors)
                        ),
                    }
                )

            # Preserve progress even if later downloads are interrupted.
            write_status(rows)

    print()
    print("=== ADR01 downloader finished ===")
    print(f"Output : {OUT_DIR.resolve()}")
    print(f"Status : {STATUS_CSV.resolve()}")
    print(f"Log    : {LOG_FILE.resolve()}")
    print()
    print(f"{'STATUS':12} {'BYTES':>12}  ITEM")
    print("-" * 100)
    for row in rows:
        print(f"{str(row['status']):12} {int(row['bytes']):>12}  {row['item']}")

    failed = sum(row["status"] == "FAILED" for row in rows)
    downloaded = sum(row["status"] == "DOWNLOADED" for row in rows)
    existing = sum(row["status"] == "EXISTS" for row in rows)

    print()
    print(
        f"Downloaded={downloaded}, Existing={existing}, "
        f"Failed={failed}, Total={len(rows)}"
    )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
