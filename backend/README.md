# Quorum Backend

FastAPI + LangGraph service implementing the Gate, five domain
agents, and negotiation. Real, tested — see
`specs/tier3_verification/STATUS_INDEX.md` for current status, not
this file.

## Local setup

```
cd backend
pip install -e .
cp .env.example .env   # fill in real values only if you have them
```

## Running tests

```
pytest tests -q
```

## Structure

`src/quorum_backend/` — the real package. See
`specs/tier1_foundation/QUORUM_PROJECT_STRUCTURE.md` for the full,
reasoned layout.