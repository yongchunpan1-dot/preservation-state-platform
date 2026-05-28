"""Build an evidence-linked preservation chemistry table.

This script is intentionally source-aware rather than a hand-written material list.
It mines or registers evidence from PubChem, FDA IID, FDA GRAS, eCFR 21 CFR,
commercial preservation systems, and curated high-priority preservation papers.
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
    "trehalose", "sucrose", "mannitol", "sorbitol", "glycerol", "dextran",
    "hydroxyethyl starch", "alginate", "gelatin", "hyaluronic acid",
    "polyethylene glycol", "polyvinyl alcohol", "poloxamer 188",
    "dimethyl sulfoxide", "glyoxal", "formaldehyde", "methanol", "ethanol",
    "EDTA", "citrate", "histidine", "HEPES", "phosphate", "sodium chloride",
    "glutathione", "ascorbic acid", "RNAlater", "PAXgene",
    "silica", "silicic acid", "calcium phosphate", "ZIF-8",
    "arginine", "lysine", "glycine", "proline", "betaine",
    "ectoine", "hydroxyectoine", "taurine",
    "raffinose", "pullulan", "polyvinylpyrrolidone",
    "methylcellulose", "hydroxypropyl methylcellulose",
    "polysorbate 20", "polysorbate 80",
    "albumin", "bovine serum albumin",
    "catalase", "superoxide dismutase",
    "N-acetylcysteine", "tocopherol",
    "magnesium chloride", "calcium chloride",
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
    "silica": "condensed silica final-product reference state",
    "silicic acid": "silica-forming preservation chemistry module",
    "calcium phosphate": "biomineralization and mineral-shell candidate",
    "ZIF-8": "MOF biomineralization shell candidate",
    "arginine": "protein aggregation-suppression excipient candidate",
    "lysine": "amino-acid osmolyte and protein-stabilization candidate",
    "glycine": "amino-acid osmolyte and buffer candidate",
    "proline": "osmolyte and stress-protection amino acid candidate",
    "betaine": "compatible osmolyte and protein stabilization candidate",
    "ectoine": "compatible-solute osmolyte and stress-protection candidate",
    "hydroxyectoine": "compatible-solute osmolyte and stress-protection candidate",
    "taurine": "osmolyte and membrane-stress protection candidate",
    "raffinose": "oligosaccharide glass-forming stabilizer candidate",
    "pullulan": "polysaccharide glass/matrix-forming stabilizer candidate",
    "polyvinylpyrrolidone": "polymer excipient and matrix-forming stabilizer candidate",
    "methylcellulose": "cellulose-derived matrix and viscosity-modulation candidate",
    "hydroxypropyl methylcellulose": "matrix-forming cellulose derivative candidate",
    "polysorbate 20": "surfactant and interface stabilization excipient candidate",
    "polysorbate 80": "surfactant and interface stabilization excipient candidate",
    "albumin": "proteinaceous crowding and interface-protection excipient",
    "bovine serum albumin": "proteinaceous crowding and interface-protection excipient",
    "catalase": "enzymatic oxidative-stress suppression candidate",
    "superoxide dismutase": "enzymatic oxidative-stress suppression candidate",
    "N-acetylcysteine": "thiol antioxidant and redox-control candidate",
    "tocopherol": "lipid-phase antioxidant candidate",
    "magnesium chloride": "ionic-state and enzyme-cofactor modulation candidate",
    "calcium chloride": "ionic-state and matrix-crosslinking modulation candidate",
}

CURATED_LITERATURE = [
    {
        "material_name": "silicic acid",
        "synonym": "silicic acid",
        "source_database": "ACS Nano DOI",
        "source_url_or_reference": "https://pubs.acs.org/doi/10.1021/acsnano.1c08103",
        "evidence_statement": "High-priority silicic-acid preservation evidence; add to silica-forming preservation module for manual extraction of mechanism and assay data.",
        "preservation_relevance": "supports silicic-acid chemistry for biomolecular or cellular preservation-state engineering",
    },
    {
        "material_name": "silicic acid",
        "synonym": "silicic acid",
        "source_database": "PNAS DOI",
        "source_url_or_reference": "https://www.pnas.org/doi/10.1073/pnas.2322418121",
        "evidence_statement": "High-priority silicic-acid preservation evidence; add as curated evidence pending full-text extraction.",
        "preservation_relevance": "supports evaluating silicic-acid chemistry as a strong preservation-state module",
    },
    {
        "material_name": "silicic acid",
        "synonym": "silicic acid",
        "source_database": "PNAS DOI",
        "source_url_or_reference": "https://www.pnas.org/doi/full/10.1073/pnas.2408273121",
        "evidence_statement": "High-priority silicic-acid preservation evidence; add as curated evidence pending full-text extraction.",
        "preservation_relevance": "supports evaluating silicic-acid chemistry as a strong preservation-state module",
    },
]


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
    rows = []
    for material in materials:
        payload = query_pubchem(material)
        props = None
        if payload:
            try:
                props = payload["PropertyTable"]["Properties"][0]
            except Exception:
                props = None
        if props:
            statement = f"PubChem record found for {material}; CID={props.get('CID')}, MW={props.get('MolecularWeight')}, XLogP={props.get('XLogP')}, TPSA={props.get('TPSA')}."
            notes = json.dumps(props, ensure_ascii=False)
            confidence = "L2_database_identifier"
        else:
            statement = f"No directly parsed PubChem property record found for {material}; retain as curated seed."
            notes = "requires_manual_structure_verification"
            confidence = "L5_curated_seed"
        rows.append(EvidenceRecord(material, material, "chemical_database", "PubChem PUG-REST", f"https://pubchem.ncbi.nlm.nih.gov/#query={quote_plus(material)}", statement, PRESERVATION_CONTEXT.get(material, "preservation candidate"), "descriptor source for downstream assay-risk and compatibility modeling", "not a regulatory assertion", confidence, notes))
    return rows


def load_optional_iid_files(iid_path: Optional[Path]) -> pd.DataFrame:
    if iid_path is None or not iid_path.exists():
        return pd.DataFrame()
    if iid_path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(iid_path)
    else:
        df = pd.read_csv(iid_path)
    norm = {c: re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") for c in df.columns}
    return df.rename(columns=norm)


def build_fda_iid_records(materials: Iterable[str], iid_path: Optional[Path] = None) -> list[EvidenceRecord]:
    rows = []
    iid_df = load_optional_iid_files(iid_path)
    for material in materials:
        matched = pd.DataFrame()
        if not iid_df.empty:
            cols = [c for c in iid_df.columns if any(k in c for k in ["ingredient", "name", "inactive"])]
            if cols:
                mask = False
                for c in cols:
                    mask = mask | iid_df[c].astype(str).str.contains(material, case=False, na=False)
                matched = iid_df[mask]
        if not matched.empty:
            statement = f"FDA IID local file contains {len(matched)} row(s) matching {material}."
            regulatory = "direct FDA IID precedent candidate; route/amount requires row-level verification"
            level = "L1_regulatory_database_local_match"
            notes = matched.head(5).to_json(orient="records", force_ascii=False)
        else:
            statement = f"FDA IID download page registered for {material}; no local IID row parsed yet."
            regulatory = "FDA IID source registered; requires row-level verification"
            level = "L2_regulatory_source_registered"
            notes = "requires_manual_or_local_iid_file_verification"
        rows.append(EvidenceRecord(material, material, "regulatory_database", "FDA Inactive Ingredient Database", FDA_IID_DOWNLOAD_PAGE, statement, PRESERVATION_CONTEXT.get(material, "preservation candidate"), "regulatory precedent does not imply assay compatibility", regulatory, level, notes))
    return rows


def build_fda_gras_records(materials: Iterable[str]) -> list[EvidenceRecord]:
    rows = []
    for material in materials:
        search_url = FDA_GRAS_NOTICE_INVENTORY + f"?search={quote_plus(material)}"
        r = _safe_get(search_url)
        hit = bool(r is not None and material.lower() in r.text.lower())
        rows.append(EvidenceRecord(material, material, "regulatory_database", "FDA GRAS Notice Inventory", search_url, f"GRAS inventory search URL generated for {material}; " + ("page text contains the material string." if hit else "automatic page text match not confirmed."), PRESERVATION_CONTEXT.get(material, "preservation candidate"), "GRAS status is safety/food-use precedent, not assay compatibility evidence", "GRAS notice candidate; requires notice-level review", "L1_or_L2_GRAS_text_match" if hit else "L2_GRAS_source_registered", "verify notice number and intended use manually"))
    return rows


def build_21cfr_records(materials: Iterable[str]) -> list[EvidenceRecord]:
    rows = []
    part_text = {}
    for label, url in ECFR_21CFR_PARTS.items():
        r = _safe_get(url)
        part_text[label] = BeautifulSoup(r.text, "lxml").get_text(" ", strip=True).lower() if r is not None else ""
    for material in materials:
        hits = [label for label, text in part_text.items() if material.lower() in text]
        if hits:
            statement = f"Material string '{material}' detected in eCFR parts: {', '.join(hits)}."
            level = "L1_regulatory_text_string_match"
            regulatory = "21 CFR text candidate; section and use context require manual confirmation"
        else:
            statement = f"No automatic eCFR string match for {material} in 21 CFR 172/182/184 text snapshot."
            level = "L2_regulatory_source_checked_no_string_match"
            regulatory = "no automatic 21 CFR text match"
        rows.append(EvidenceRecord(material, material, "regulatory_text", "eCFR 21 CFR Parts 172/182/184", "; ".join(ECFR_21CFR_PARTS.values()), statement, PRESERVATION_CONTEXT.get(material, "preservation candidate"), "regulatory text does not determine downstream assay compatibility", regulatory, level, "string-match only; final curation must record CFR section and restrictions"))
    return rows


def build_commercial_preservation_records() -> list[EvidenceRecord]:
    commercial = [("RNAlater", "Thermo Fisher RNAlater", "commercial RNA stabilization system"), ("PAXgene", "QIAGEN/PreAnalytiX PAXgene", "commercial molecular preservation system"), ("methanol", "methanol fixation", "single-cell fixation workflow candidate"), ("glyoxal", "glyoxal fixation", "RNA-compatible fixation-state candidate"), ("formaldehyde", "PFA/formaldehyde fixation", "morphology-preserving crosslinking fixation"), ("dimethyl sulfoxide", "DMSO cryopreservation", "live-cell cryopreservation state")]
    return [EvidenceRecord(name, syn, "commercial_or_protocol_system", "curated preservation workflow source", "to_be_resolved_with_product_or_protocol_reference", f"{syn} registered as {statement}.", statement, "assay-conditional; must be encoded in assay_risk_rules.yaml", "commercial/protocol precedent; not equivalent to regulatory approval for new use", "L3_curated_protocol_system", "replace reference with product insert, DOI, or PMID during final curation") for name, syn, statement in commercial]


def build_curated_literature_records() -> list[EvidenceRecord]:
    return [EvidenceRecord(item["material_name"], item["synonym"], "curated_literature", item["source_database"], item["source_url_or_reference"], item["evidence_statement"], item["preservation_relevance"], "assay compatibility and cleanup burden must be extracted from full text and encoded separately", "not a regulatory assertion", "L3_user_curated_high_priority_literature", "high-priority silicic-acid module; pending structured extraction") for item in CURATED_LITERATURE]


def build_evidence_table(iid_file: Optional[str] = None) -> pd.DataFrame:
    iid_path = Path(iid_file) if iid_file else None
    records = []
    records.extend(build_pubchem_records(SEED_MATERIALS))
    records.extend(build_fda_iid_records(SEED_MATERIALS, iid_path=iid_path))
    records.extend(build_fda_gras_records(SEED_MATERIALS))
    records.extend(build_21cfr_records(SEED_MATERIALS))
    records.extend(build_commercial_preservation_records())
    records.extend(build_curated_literature_records())
    df = pd.DataFrame([asdict(r) for r in records])
    df.insert(0, "evidence_id", [f"EVID:{i:05d}" for i in range(len(df))])
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Build evidence-linked preservation chemistry table.")
    parser.add_argument("--iid-file", default=None)
    parser.add_argument("--output", default=str(OUTPUT_DIR / "evidence_table.csv"))
    args = parser.parse_args()
    df = build_evidence_table(iid_file=args.iid_file)
    out = Path(args.output)
    out.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(out, index=False)
    print(f"Generated {out} with {len(df)} evidence records")


if __name__ == "__main__":
    main()
