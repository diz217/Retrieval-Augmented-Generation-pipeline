# Retrieval-Augmented-Generation-pipeline
A LLM pipeline for generating structured Domain-Speicfic Language (DSL) configurations using retrieval, validation, and automatic repair.

## Overview 
The system converts a natural language query into a structured configuration
through a multi-stage pipeline:

```
Query
 ↓
Retrieval (rules + examples)
 ↓
LLM Generation
 ↓
Validation
 ↓
Repair Loop
 ↓
Final Config
```
- **Retrieval** – retrieve relevant rules and examples.
- **Generation** – the LLM generates an initial DSL config.
- **Validation** – deterministic checks detect structural errors.
- **Repair** – the LLM patches only the detected issues.

## Repo Structure
```
rag-structured-generation/
│
├─ llm/
│   ├─ client.py          # LLM API wrapper
│   ├─ prompts.py         # prompt construction: hard requirements, field policies, user query, and context. 
│   ├─ repair.py          # repair prompt logic
|   ├─ validator.py       # placeholder for domain-specific validators
│   └─ prompts/
│       ├─ system_generate.txt
|       └─ system_repair.txt
├─ rag/
|   ├─ make_chunks.py         # build the json dictionaries from raw input 
│   ├─ build_index.py         # embed the json dictionaries to vector dimension
│   └─ retrieve.py            # embed the query and retrieve top k relevant examples and mandatory rules. 
| 
├─ index/
│   └─ README.md          # placeholder for rules/examples
│
├─ knowledge/
|   ├─ processed/
│       └─ README.md      # placeholder for json dictionaries
|   └─ raw/
|       └─ README.md      # placeholder for raw example configurations
│
├─ app.py                 # entry point of config generation 
└─ README.md
```
## Key Features
- **Retrieval-augmented generation**
  combines rules and examples for structured generation.

- **Validation-repair loop**
  deterministic validation ensures correctness and triggers targeted fixes.

- **Patch-based repair**
  the LLM modifies only erroneous lines instead of regenerating the entire config.

- **Modular architecture**
  retrieval, generation, validation, and repair are separated components.

## Installation
1. Clone the repository:
```
git clone https://github.com/diz217/Retrieval-Augmented-Generation-pipeline.git
cd Retrieval-Augmented-Generation-pipeline
```
2. Install dependencies:
```
pip install -r requirements.txt
```
## Usage
Run the pipeline:
```
python app.py
```

## Notes on Omitted Components
Some components are intentionally not included in this repository.

The original project was developed in a production environment and relies on domain-specific rules, validation logic, and example configurations that are considered proprietary to the organization.

To comply with company confidentiality and intellectual property policies, the following elements have been removed or replaced with placeholders:
- production validation rules
- internal DSL specifications
- example configurations derived from company workflows

This repository focuses on the **pipeline architecture** rather than the domain-specific knowledge. The included code demonstrates the engineering design of the retrieval → generation → validation → repair workflow.

## Design Insight
Structured generation tasks require deterministic correctness,while LLM outputs are probabilistic.

This pipeline addresses the problem by combining:
- retrieval for contextual grounding
- validation for deterministic checks
- repair loops for targeted corrections

The result is a more reliable generation workflow.

