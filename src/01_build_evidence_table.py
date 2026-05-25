"""Build an evidence-linked preservation chemistry table.

This script is intentionally source-aware rather than a hand-written material list.
It mines or registers evidence from:

1. PubChem PUG-REST for chemical identifiers and simple molecular properties.
2. FDA Inactive Ingredient Database (IID) download page and optional local IID files.
3. FDA GRAS Notice Inventory search pages.
4. eCFR 21 CFR food additive / GRAS regulatory records.
5. Curated preservation-literature seed terms for PubMed expansion in later versions.

The script is conservative: when a regulatory source cannot be parsed automatically,
it still emits a traceable source record marked as `requires_manual_verification`.
This avoids overstating regulatory status while keeping the computational resource
traceable and publication-auditable.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote_plus

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("outputs")
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
RAW_DIR.mkdir(exist_ok=True, parents=True)

PUBCHEM_PROPERTY_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
    "{name}/property/MolecularWeight,XLogP,TPSA,CanonicalSMILES/JSON"
)

FDA_IID_DOWNLOAD_PAGE = (
    "https://www.fda.gov/drugs/drug-approvals-and-databases/"
    "inactive-ingredients-database-download"
)

FDA_GRAS_NOTICE_INVENTORY = "https://www.fda.gov/food/generally-recognized-safe-gras/gras-notice-inventory"

ECFR_21CFR_PARTS = {
    "21CFR172_food_additives": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-172",
    "21CFR182_GRAS_substances": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-182",
    "21CFR184_direct_food_GRAS": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-184",
}

SEED_MATERIALS = [
    "trehalose",
    "sucrose",
    "mannitol",
    "sorbitol",
    "glycerol",
    "dextran",
    "hydroxyethyl starch",
    "alginate",
    "gelatin",
    "hyaluronic acid",
    "polyethylene glycol",
    "polyvinyl alcohol",
    "poloxamer 188",
    "dimethyl sulfoxide",
    "glyoxal",
    "formaldehyde",
    "methanol",
    "ethanol",
    "EDTA",
    "citrate",
    "histidine",
    "HEPES",
    "phosphate",
    "sodium chloride",
    "glutathione",
    "ascorbic acid",
    "RNAlater",
    "PAXgene",
    "silica",
    "calcium phosphate",
    "ZIF-8",
]

PRESERVATION_CONTEXT = {
    "trehalose": "glass-forming lyoprotectant and membrane/protein stabilizer",
    "sucrose": "glass-forming lyoprotectant and protein stabilizer",
    "mannitol": "bulking and cryo/lyo formulation excipient",
    "sorbitol": "osmolyte and protein stabilizer",
    "glycerol": "permeating cryoprotectant and protein stabilizer",
    "dextran": "macromolecular glass former and crowding polymer",
    "hydroxyethyl starch": "macromolecular cryoprotective colloid",
    "alginate": "ionically crosslinkable hydrogel for encapsulation/release",
    "gelatin": "proteinaceous hydrogel and vaccine stabilizer component",
    "hyaluronic acid": "biocompatible hydrogel/matrix polymer",
    "polyethylene glycol": "polymer excipient and crowding/phase-state modifier",
    "polyvinyl alcohol": "ice-recrystallization-inhibiting polymer candidate",
    "poloxamer 188": "interface stabilizer and surfactant excipient",
    "dimethyl sulfoxide": "permeating live-cell cryoprotectant",
    "glyoxal": "fixation-state preservation with RNA-recovery relevance",
    "formaldehyde": "crosslinking fixation for morphology preservation",
    "methanol": "dehydrating fixation compatible with selected single-cell workflows",
    "ethanol": "dehydrating fixation and nucleic-acid-compatible preservation reagent",
    "EDTA": "metal chelator for nuclease inhibition and hydrogel/mineral release",
    "citrate": "buffer/chelator and calcium-mediated gel release agent",
    "histidine": "biopharmaceutical buffer and protein stabilizer",
    "HEPES": "biological buffer for pH state control",
    "phosphate": "buffering and ionic-state control",
    "sodium chloride": "tonicity and ionic-strength control",
    "glutathione": "redox-control antioxidant module",
    "ascorbic acid": "antioxidant module",
    "RNAlater": "commercial RNA stabilization system",
    "PAXgene": "commercial molecular preservation system",
    "silica": "mineralization/silicification shell candidate",
    "calcium phosphate": "biomineralization and mineral-shell candidate",
    "ZIF-8": "MOF biomineralization shell candidate",
}


@dataclass
class EvidenceRecord:
    material_name: str
    synonym: str
    source_type: str
    source_database: str
    source_url_or_reference: str
    evidence_statement: str
    preservation_relevance: str
    assay_relevance: str
    regulatory_relevance: str
    evidence_level: str
    notes: str = ""


def _safe_get(url: str, timeout: int = 25) -> Optional[requests.Response]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "preservation-state-platform/0.1"})
        if r.status_code == 200:
            return r
    except Exception:
        return None
    return None


def query_pubchem(name: str) -> Optional[dict]:
    url = PUBCHEM_PROPERTY_URL.format(name=quote_plus(name))
    r = _safe_get(url)
    if not r:
        return None
    try:
        return r.json()
    except Exception:
        return None


def build_pubchem_records(materials: Iterable[str]) -> list[EvidenceRecord]:
    rows: list[EvidenceRecord] = []
    for material in materials:
        payload = query_pubchem(material)
        props = None
        if payload:
            try:
                props = payload["PropertyTable"]["Properties"][0]
            except Exception:
                props = None

        if props:
            evidence_statement = (
                f"PubChem record found for {material}; CID={props.get('CID')}, "
                f"MW={props.get('MolecularWeight')}, XLogP={props.get('XLogP')}, TPSA={props.get('TPSA')}."
            )
            notes = json.dumps(props, ensure_ascii=False)
            confidence = "L2_database_identifier"
        else:
            evidence_statement = f"No directly parsed PubChem property record found for {material}; retain as curated seed."
            notes = "requires_manual_structure_verification"
            confidence = "L5_curated_seed"

        rows.append(
            EvidenceRecord(
                material_name=material,
                synonym=material,
                source_type="chemical_database",
                source_database="PubChem PUG-REST",
                source_url_or_reference=f"https://pubchem.ncbi.nlm.nih.gov/#query={quote_plus(material)}",
                evidence_statement=evidence_statement,
                preservation_relevance=PRESERVATION_CONTEXT.get(material, "preservation candidate"),
                assay_relevance="descriptor source for downstream assay-risk and compatibility modeling",
                regulatory_relevance="not a regulatory assertion",
                evidence_level=confidence,
                notes=notes,
            )
        )
    return rows


def load_optional_iid_files(iid_path: Optional[Path]) -> pd.DataFrame:
    """Load a local FDA IID CSV/XLS/XLSX if the user downloads one.

    FDA periodically changes file names and formats. This loader accepts local
    files placed under data/raw/ and tries to normalize common columns.
    """
    if iid_path is None or not iid_path.exists():
        return pd.DataFrame()

    if iid_path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(iid_path)
    else:
        df = pd.read_csv(iid_path)

    norm = {c: re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") for c in df.columns}
    df = df.rename(columns=norm)
    return df


def build_fda_iid_records(materials: Iterable[str], iid_path: Optional[Path] = None) -> list[EvidenceRecord]:
    rows: list[EvidenceRecord] = []
    iid_df = load_optional_iid_files(iid_path)

    for material in materials:
        matched = pd.DataFrame()
        if not iid_df.empty:
            candidate_cols = [c for c in iid_df.columns if any(k in c for k in ["ingredient", "name", "inactive"])]
            if candidate_cols:
                mask = False
                for c in candidate_cols:
                    mask = mask | iid_df[c].astype(str).str.contains(material, case=False, na=False)
                matched = iid_df[mask]

        if not matched.empty:
            evidence_statement = f"FDA IID local file contains {len(matched)} row(s) matching {material}."
            regulatory_relevance = "direct FDA IID precedent candidate; route/amount requires row-level verification"
            evidence_level = "L1_regulatory_database_local_match"
            notes = matched.head(5).to_json(orient="records", force_ascii=False)
        else:
            evidence_statement = (
                f"FDA IID download page registered for {material}; no local IID row parsed yet. "
                "Download the current IID file to data/raw/ and rerun with --iid-file for row-level matching."
            )
            regulatory_relevance = "FDA IID source registered; requires row-level verification"
            evidence_level = "L2_regulatory_source_registered"
            notes = "requires_manual_or_local_iid_file_verification"

        rows.append(
            EvidenceRecord(
                material_name=material,
                synonym=material,
                source_type="regulatory_database",
                source_database="FDA Inactive Ingredient Database",
                source_url_or_reference=FDA_IID_DOWNLOAD_PAGE,
                evidence_statement=evidence_statement,
                preservation_relevance=PRESERVATION_CONTEXT.get(material, "preservation candidate"),
                assay_relevance="regulatory precedent does not imply assay compatibility",
                regulatory_relevance=regulatory_relevance,
                evidence_level=evidence_level,
                notes=notes,
            )
        )
    return rows


def build_fda_gras_records(materials: Iterable[str]) -> list[EvidenceRecord]:
    rows: list[EvidenceRecord] = []
    for material in materials:
        search_url = FDA_GRAS_NOTICE_INVENTORY + f"?search={quote_plus(material)}"
        # FDA pages are often dynamic; we register a traceable search URL and try a lightweight text check.
        r = _safe_get(search_url)
        text_hit = False
        if r is not None:
            text_hit = material.lower() in r.text.lower()

        rows.append(
            EvidenceRecord(
                material_name=material,
                synonym=material,
                source_type="regulatory_database",
                source_database="FDA GRAS Notice Inventory",
                source_url_or_reference=search_url,
                evidence_statement=(
                    f"GRAS inventory search URL generated for {material}; "
                    + ("page text contains the material string." if text_hit else "automatic page text match not confirmed.")
                ),
                preservation_relevance=PRESERVATION_CONTEXT.get(material, "preservation candidate"),
                assay_relevance="GRAS status is a safety/food-use precedent, not assay compatibility evidence",
                regulatory_relevance="GRAS notice candidate; requires notice-level review before regulatory scoring",
                evidence_level="L2_GRAS_source_registered" if not text_hit else "L1_or_L2_GRAS_text_match",
                notes="dynamic FDA search page; verify notice number and intended use manually before final database release",
            )
        )
    return rows


def build_21cfr_records(materials: Iterable[str]) -> list[EvidenceRecord]:
    rows: list[EvidenceRecord] = []
    part_text: dict[str, str] = {}
    for label, url in ECFR_21CFR_PARTS.items():
        r = _safe_get(url)
        if r is not None:
            soup = BeautifulSoup(r.text, "lxml")
            part_text[label] = soup.get_text(" ", strip=True).lower()
        else:
            part_text[label] = ""

    for material in materials:
        hits = [label for label, text in part_text.items() if material.lower() in text]
        if hits:
            evidence_statement = f"Material string '{material}' detected in eCFR parts: {', '.join(hits)}."
            evidence_level = "L1_regulatory_text_string_match"
            regulatory_relevance = "21 CFR text candidate; section and use context require manual confirmation"
        else:
            evidence_statement = f"No automatic eCFR string match for {material} in 21 CFR 172/182/184 text snapshot."
            evidence_level = "L2_regulatory_source_checked_no_string_match"
            regulatory_relevance = "no automatic 21 CFR text match"

        rows.append(
            EvidenceRecord(
                material_name=material,
                synonym=material,
                source_type="regulatory_text",
                source_database="eCFR 21 CFR Parts 172/182/184",
                source_url_or_reference="; ".join(ECFR_21CFR_PARTS.values()),
                evidence_statement=evidence_statement,
                preservation_relevance=PRESERVATION_CONTEXT.get(material, "preservation candidate"),
                assay_relevance="regulatory text does not determine downstream assay compatibility",
                regulatory_relevance=regulatory_relevance,
                evidence_level=evidence_level,
                notes="string-match only; final curation must record CFR section, use context, and restrictions",
            )
        )
    return rows


def build_commercial_preservation_records() -> list[EvidenceRecord]:
    commercial = [
        ("RNAlater", "Thermo Fisher RNAlater", "commercial RNA stabilization system"),
        ("PAXgene", "QIAGEN/PreAnalytiX PAXgene", "commercial molecular preservation system"),
        ("methanol", "methanol fixation", "single-cell fixation workflow candidate"),
        ("glyoxal", "glyoxal fixation", "RNA-compatible fixation-state candidate"),
        ("formaldehyde", "PFA/formaldehyde fixation", "morphology-preserving crosslinking fixation"),
        ("dimethyl sulfoxide", "DMSO cryopreservation", "live-cell cryopreservation state"),
    ]
    return [
        EvidenceRecord(
            material_name=name,
            synonym=syn,
            source_type="commercial_or_protocol_system",
            source_database="curated preservation workflow source",
            source_url_or_reference="to_be_resolved_with_product_or_protocol_reference",
            evidence_statement=f"{syn} registered as {statement}.",
            preservation_relevance=statement,
            assay_relevance="assay-conditional; must be encoded in assay_risk_rules.yaml",
            regulatory_relevance="commercial/protocol precedent; not equivalent to regulatory approval for new use",
            evidence_level="L3_curated_protocol_system",
            notes="replace source_url_or_reference with product insert, protocol, DOI, or PMID during final curation",
        )
        for name, syn, statement in commercial
    ]


def build_evidence_table(iid_file: Optional[str] = None) -> pd.DataFrame:
    iid_path = Path(iid_file) if iid_file else None
    records: list[EvidenceRecord] = []
    records.extend(build_pubchem_records(SEED_MATERIALS))
    records.extend(build_fda_iid_records(SEED_MATERIALS, iid_path=iid_path))
    records.extend(build_fda_gras_records(SEED_MATERIALS))
    records.extend(build_21cfr_records(SEED_MATERIALS))
    records.extend(build_commercial_preservation_records())

    df = pd.DataFrame([asdict(r) for r in records])
    df.insert(0, "evidence_id", [f"EVID:{i:05d}" for i in range(len(df))])
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Build evidence-linked preservation chemistry table.")
    parser.add_argument(
        "--iid-file",
        default=None,
        help="Optional local FDA IID CSV/XLSX file downloaded into data/raw/ for row-level matching.",
    )
    parser.add_argument("--output", default=str(OUTPUT_DIR / "evidence_table.csv"))
    args = parser.parse_args()

    df = build_evidence_table(iid_file=args.iid_file)
    out = Path(args.output)
    out.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(out, index=False)
    print(f"Generated {out} with {len(df)} evidence records")


if __name__ == "__main__":
    main()
