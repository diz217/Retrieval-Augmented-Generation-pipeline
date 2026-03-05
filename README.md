# Retrieval-Augmented-Generation-pipeline
A LLM architecture for generating structured Domain-Speicfic Language (DSL) configurations using retrieval, validation, and automatic repair.

## Overview 
The goal of this system is to convert natural language queries into structured DSL configurations while maintaining deterministic correctness.

Since LLM generation is inherently probabilistic, the pipeline is designed as a multi-stage workflow that separates semantic reasoning from deterministic validation.
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
│   ├─ client.py                 # LLM API wrapper
│   ├─ prompts.py                # prompt construction (system + user input)
│   ├─ repair.py                 # build repair prompts from validation reports
|   ├─ validator.py              # placeholder for domain-specific validators
│   └─ prompts/
│       ├─ system_generate.txt   # hard requirements, field policies
|       └─ system_repair.txt    
├─ rag/
|   ├─ make_chunks.py            # convert raw configs into structured JSON chunks 
│   ├─ build_index.py            # embed chunks and build vector index
│   └─ retrieve.py               # embed query and retrieve top k relevant examples and mandatory rules. 
| 
├─ index/
│   └─ README.md                 # placeholder for vector index files
│
├─ knowledge/
|   ├─ processed/
│       └─ README.md             # placeholder for processed JSON chunks
|   └─ raw/
|       └─ README.md             # placeholder for raw example configurations
|
├─ runs/
|   └─ README.md                 # placeholder for user-generated run logs
|
├─ app.py                        # entry point for config generation 
└─ README.md
```
## Design Principles

This project is designed as a **reliable structured-generation system**, not a one-shot RAG demo.
The key challenge is turning **probabilistic LLM outputs** into **deterministic, structured configs**.

#### 1) Separation of concerns
The pipeline isolates responsibilities into clear stages:

- **Retrieval**: fetch relevant rules and examples (context grounding)
- **Generation**: translate the user request into an initial candidate config
- **Validation**: deterministically check structural constraints and emit a structured report
- **Repair**: apply minimal patches based on the validation report (instead of regenerating)

This separation makes the system easier to debug and extend.

#### 2) Rules-first, examples-second
Retrieved context may contain both rules and examples. The system enforces a strict precedence:

- **RULES override EXAMPLES** if there is any conflict.

This prevents pattern imitation from violating hard constraints.

#### 3) Patch-based repair for stability
Rather than re-generating the entire config after validation failures, the repair step operates in **PATCH mode**:

- keep unchanged lines as-is  
- edit only the smallest set of lines needed to resolve validation errors

This reduces drift and improves reproducibility across runs.

#### 4) Deterministic interface boundaries
The pipeline communicates across stages using explicit artifacts:

- retrieved chunks (structured)
- rendered context (text)
- candidate config (DSL text)
- validation report (structured)

These boundaries make behavior observable and allow swapping implementations
(e.g., different retrievers, different validators, different LLMs).

## Installation
**1) Clone the repository:**
```bash
git clone https://github.com/diz217/Retrieval-Augmented-Generation-pipeline.git
cd Retrieval-Augmented-Generation-pipeline
```
**2) Install dependencies:**
```bash
pip install -r requirements.txt
```
Python version recommended:
```bash
Python >=3.9
```
**3) Configure API credentials:**
 
This project relies on external APIs for embedding and LLM inference.

Create a .env file or export environment variables.

Example:
```bash
export HF_TOKEN=your_huggingface_token
export OPENAI_API_KEY=your_openai_key
```
Supported providers include:
- HuggingFace (recommended for embedding models)
- OpenAI
- other compatible LLM API providers

These tokens are not required for repository installation, but are required for running the full pipeline.

**4) Provide domain configuration:**

For legal and intellectual-property reasons, this repository **does not include domain-specific rules or proprietary data**.

Users must provide their own configuration:

Required components include:
- **Raw input data** (knowledge preparation)
- **Domain rules** (used during retrieval)
- **Validation logic** (used to check generated outputs)

## Usage
### Prepare retrival knowledge 
The retrieval system expects rule documents to be converted into chunks and indexed.

**Step 1: Create chunks**

Split rule documents into retrieval chunks.

Example:
```bash
python make_chunks.py
```
This step converts rule files into smaller text segments suitable for retrieval.

**Step 2:Build embedding index**

Generate embeddings and build the vector index.

Example:
```bash
python build_index.py
```
This step requires an embedding model (e.g., HuggingFace). A HuggingFace token is required as environment variable. 
### Run the generation pipeline
Once the index is built, run the main pipeline.

Example:
```bash
python app.py
```
You will be prompted to enter a query (natural language request). The pipeline then executes:
- Retrieve top-k relevant chunks (rules + examples)
- Build a rendered context
- Call the LLM to generate a candidate config
- Validate the candidate
- If validation fails, run a repair loop up to `max_repairs` times
### Expected Output (Artifacts)
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

