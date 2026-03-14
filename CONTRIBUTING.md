# Contributing Guide

## Development Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Run local checks:
   ```bash
   python3 -m compileall src app.py scripts tests
   ```

## Branch and PR Workflow
- Create feature branches from `main`.
- Use descriptive branch names: `feature/<name>` or `fix/<name>`.
- Submit a pull request with:
  - objective,
  - files changed,
  - testing proof,
  - screenshots (if UI changes).

## Coding Rules
- Keep SQL logic explicit and reviewable.
- Use parameterized queries only.
- Keep ingestion robust to common CSV variants.
- Add/update tests for behavior changes.
