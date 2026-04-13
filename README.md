# CRIS-SME

**Cloud Risk Intelligence System for Small & Medium Enterprises**

---

## Overview

CRIS-SME is an AI-assisted cloud governance and compliance risk intelligence framework designed to help small and medium enterprises (SMEs) identify, assess, and manage risks in Microsoft Azure environments.

The project focuses on bridging the gap between enterprise-grade cloud security tools and the practical needs of SMEs by providing a lightweight, explainable, and scalable approach to cloud risk assessment.

---

## Problem Statement

Many SMEs migrating to cloud platforms lack structured governance frameworks, automated compliance validation, and risk intelligence capabilities. Existing solutions are often complex, costly, and not tailored to SME environments.

CRIS-SME addresses this gap by introducing an accessible framework that combines:

* Governance control validation
* Risk scoring and prioritisation
* Compliance mapping
* AI-assisted risk intelligence

---

## Key Features

* **Cloud Governance Control Checks**
  Detect misconfigurations across identity, network, data, monitoring, and governance layers

* **Risk Scoring Engine**
  Quantifies risk using severity, exposure, data sensitivity, and confidence factors

* **AI-Assisted Prioritisation** *(Planned)*
  Enhances decision-making by ranking risks based on predicted impact

* **Compliance Mapping**
  Maps findings to standards such as GDPR, ISO 27001, and CIS benchmarks

* **Explainable Risk Outputs**
  Provides transparent reasoning behind each risk score

* **SME-Focused Design**
  Built specifically for simplicity, usability, and cost-awareness

---

## System Architecture

CRIS-SME follows a modular architecture:

1. **Collectors**
   Extract cloud configuration data (Azure / mock data)

2. **Control Engine**
   Applies governance rules and generates findings

3. **Risk Engine**
   Calculates risk scores and prioritises issues

4. **Reporting Layer**
   Produces structured outputs (JSON, HTML, summaries)

📄 See: `docs/architecture.md`

---

## Methodology

The framework is based on:

* Rule-based governance validation
* Weighted risk scoring model
* Category-based risk aggregation
* Explainable AI-assisted prioritisation (future phase)

📄 See: `docs/methodology.md`
📄 See: `docs/scoring-model.md`

---

## Repository Structure

```
src/cris_sme/
  ├── collectors/       # Azure and mock data collectors
  ├── controls/         # Governance rule definitions
  ├── models/           # Data structures (findings, results)
  ├── engine/           # Risk scoring and aggregation
  ├── reporting/        # Output generation
  └── utils/            # Helper functions

docs/                   # Research and architecture documentation  
data/                   # Sample datasets and control mappings  
notebooks/              # Experiments and analysis  
tests/                  # Unit tests  
```

---

## Current Status

🚧 MVP in development

Completed:

* Project structure
* Risk model design

In progress:

* Finding schema
* Risk scoring engine
* Mock data integration

Planned:

* Azure integration
* AI-based prioritisation
* Dashboard visualisation

---

## Roadmap

### Phase 1: Foundation

* Define data models
* Implement scoring engine
* Generate mock findings

### Phase 2: Core Engine

* Implement governance controls
* Build aggregation and reporting

### Phase 3: Azure Integration

* Connect to Azure APIs
* Perform real configuration scans

### Phase 4: Intelligence Layer

* Add AI-based prioritisation
* Introduce predictive risk modelling

### Phase 5: Research & Publication

* Produce academic paper
* Present at conferences
* Extend compliance mapping

---

## Research Contribution

CRIS-SME contributes to the field of cloud computing and governance by:

* Introducing an SME-focused cloud risk intelligence model
* Providing an explainable and scalable governance framework
* Bridging the gap between research and practical implementation
* Enabling accessible cloud security assessment

---

## Use Cases

* SME cloud risk assessment
* Governance auditing for Azure environments
* Academic research in cloud security and risk modelling
* Teaching and demonstration of cloud governance concepts

---

## Getting Started

### Requirements

* Python 3.10+

### Installation

```bash
git clone https://github.com/your-username/cris-sme.git
cd cris-sme
pip install -r requirements.txt
```

### Run (example)

```bash
python src/cris_sme/main.py
```

---

## Future Enhancements

* Integration with Microsoft Defender for Cloud
* Real-time monitoring capabilities
* Multi-cloud support (AWS, GCP)
* Advanced machine learning models
* SME benchmarking dataset

---

## Author

Muhammad Ibrahim
Academic Leader | Cloud & Digital Systems Researcher

---

## License

MIT License

---

## Acknowledgements

This project is developed as part of ongoing research into cloud governance, risk intelligence, and SME digital resilience.
