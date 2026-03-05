# runs/

This directory stores artifacts produced by each pipeline run.

Every execution of `app.py` creates a new subdirectory named with the run timestamp (to the second):
```bash
runs/
  20260304_142226/
  20260304_142512/
```
Each run directory contains intermediate artifacts for debugging and reproducibility:
```bash
- request.txt        — user query entered at runtime
- retrieved.json     — retrieved chunks from the vector index
- context.txt        — rendered retrieval context
- prompt.txt         — prompt sent to the LLM

- candidate_0.txt    — initial generated configuration
- validation_0.json  — validation report

- candidate_N.txt / validation_N.json — repair attempts (if validation fails)

- final_config.txt   — final accepted configuration
```
