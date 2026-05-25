# Preservation-State Platform

A computational and experimental infrastructure for AI-guided preservation-state engineering.

## Concept

The platform is designed around the idea that biological systems should be preserved as recoverable informational states rather than as isolated molecular entities.

The framework explicitly separates:

- preservation performance
- downstream assay compatibility
- recoverability / cleanup burden
- translational feasibility

This distinction forms the conceptual basis of the platform.

## Repository Structure

```text
src/
├── 01_build_evidence_table.py
├── 02_generate_core_library.py
├── 03_compute_descriptors.py
├── 04_generate_virtual_formulation_universe.py
├── 05_build_assay_risk_engine.py
├── 09_deep_learning_model.py
```

## Workflow

```text
Literature + Regulatory Mining
        ↓
Descriptor Engineering
        ↓
Virtual Preservation-State Universe
        ↓
Assay-Risk / Cleanup Modeling
        ↓
Bayesian / AI Candidate Ranking
        ↓
Experimental Testing
        ↓
Closed-Loop Model Updating
```

## Current Status

The repository currently contains:

- FDA IID / GRAS source-aware mining scaffold
- PubChem descriptor mining
- preservation-state ontology scaffold
- virtual formulation universe generation
- assay compatibility modeling
- cleanup/recoverability modeling
- multi-task deep learning scaffold

## Planned Additions

- Bayesian optimization engine
- interaction graph learning
- graph neural network expansion
- active learning acquisition functions
- preservation-state embeddings
- benchmark experimental workflows
- temporal fidelity scoring system

## Example Workflow

```bash
python src/01_build_evidence_table.py
python src/03_compute_descriptors.py
python src/04_generate_virtual_formulation_universe.py
python src/05_build_assay_risk_engine.py
python src/09_deep_learning_model.py
```

## Outputs

Representative generated outputs include:

- evidence_table.csv
- descriptor_table.csv
- preservation_universe_virtual.csv
- formulation_assay_compatibility.csv
- top_ranked_experimental_candidates.csv
- deep_learning_recommended_formulations.csv

## Positioning

This repository is not intended as a simple formulation screen or additive catalog.
Instead, it is being developed as a generalized preservation-state engineering platform for maintaining temporal fidelity across biological hierarchies.
