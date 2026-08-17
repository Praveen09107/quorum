# Quorum backend — real Dockerfile.
#
# HONEST NOTE: the original IMPL_11 spec describes a requirements.txt-based
# COPY step. This repository's real, current packaging is pyproject.toml +
# an editable install (see backend/pyproject.toml) -- built that way from
# the start of this repository's real work (IMPL_01's bootstrap). This
# Dockerfile matches what's ACTUALLY here, not the original spec's assumed
# packaging approach.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["uvicorn", "quorum_backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
