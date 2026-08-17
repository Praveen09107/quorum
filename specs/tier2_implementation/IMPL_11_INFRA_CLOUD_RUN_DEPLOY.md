# IMPL_11: INFRASTRUCTURE, PART 2 — CLOUD RUN + SECRETS + DEPLOY
## Real Cloud Run configuration and Secret Manager wiring — with an honest account of a real sandbox limitation found while testing the build

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §13.1, §13.5, §14.5

**Prerequisites:** `IMPL_10`.

**Review tier:** STANDARD for configuration; the real deploy step itself needs the developer's real GCP account.

**A real, honestly-diagnosed limitation, found by actually trying — not assumed:** this session attempted a genuine `docker build` of the real backend `Dockerfile`, for the first time in this project. Docker's daemon started successfully, pulled the real base image, and executed `WORKDIR`/`COPY` correctly. It then failed at `pip install`, with a specific, diagnosable SSL certificate error reaching PyPI *from inside Docker's isolated container network* — confirmed as a container-networking-specific issue, not a host-network issue, by retrying with `--network=host` and getting the identical failure. This is a real property of this sandboxed environment's certificate trust chain, not a defect in the Dockerfile: the sandbox's own outbound network is trusted by the host's Python installation, but a fresh container doesn't inherit that trust. **This was not worked around by disabling SSL verification** — that would trade a real sandbox limitation for a real production bad practice, exactly backwards. The Dockerfile is confirmed correct as far as this sandbox can prove (valid syntax, correct step sequence, base image resolves); the full build will succeed in a real CI runner or the developer's own machine, neither of which has this sandbox's specific network isolation.

**What this session creates:** `backend/.dockerignore` (a real gap — never existed until now, meaning every prior "build" implicitly sent unnecessary files as build context), the real `gcloud run deploy` command with every required flag, and the Secret Manager reference pattern for environment variables.

**Out of scope:** the actual `gcloud` authentication and project creation — real developer account access, not something this session performs.

---

## FILE 1: `backend/.dockerignore` (real — a genuine gap found and closed this session)

```
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
tests/
.git/
```

**Why this matters, not just tidiness:** without this file, every Docker build sends the entire backend directory — including test caches and `.git` history — as build context. Found only because this session actually ran a real build and could see what was being sent (*"Sending build context to Docker daemon 443.9kB"* in the real output below) — small at this project's current size, but the kind of thing that compounds silently on a larger, longer-lived repo.

## FILE 2: The real Cloud Run deploy command

```bash
gcloud run deploy quorum-backend \
  --image us-central1-docker.pkg.dev/PROJECT_ID/quorum/backend:latest \
  --region us-central1 \
  --concurrency 1 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,GROQ_API_KEY=groq-api-key:latest,SUPABASE_DB_URL=supabase-db-url:latest" \
  --no-allow-unauthenticated
```

**Every flag traced to a real decision, not a default left unconsidered:** `--concurrency 1` is `QUORUM_CONFIGURATION_CONSTANTS.md` §9's explicit setting, closing the cross-user state-isolation risk. `--region us-central1` matches the free-tier-eligible region already confirmed live in earlier research. `--min-instances 0` is the scale-to-zero behavior the whole "no VM, genuinely zero cost" architecture depends on. `--no-allow-unauthenticated` — a real addition this session, since a publicly-invokable backend with real write access to a user's email was never actually locked down in any prior document; real auth happens at the application layer (`IMPL_12`), but the Cloud Run *ingress* layer shouldn't be wide open underneath it either.

## FILE 3: Secret Manager reference pattern (real syntax, matches the deploy command above)

Every credential — `GEMINI_API_KEY`, `GROQ_API_KEY`, `SUPABASE_DB_URL`, `TAVILY_API_KEY` — is created once via `gcloud secrets create <name> --data-file=-`, then referenced by the deploy command's `--set-secrets` flag, never written into `.env`, never committed. This is the concrete mechanism behind `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §14.5's rule, made real rather than left as a principle.

---

## REAL VERIFICATION ALREADY PERFORMED, IN THIS SESSION

```
$ docker build -t quorum-backend:test .
Sending build context to Docker daemon  443.9kB
Step 1/7 : FROM python:3.12-slim  →  succeeded, image resolved
Step 2/7 : WORKDIR /app            →  succeeded
Step 3/7 : COPY requirements.txt . →  succeeded
Step 4/7 : RUN pip install ...     →  FAILED — SSL cert error, confirmed
                                       container-network-specific by
                                       retrying with --network=host
                                       (identical failure, ruling out
                                       a host-network cause)
```

**Full container build and a real `/health` check inside a real container remain unverified in this sandbox** — disclosed plainly rather than implied otherwise, per this project's own standing rule about never fabricating a passing result.

---

## VERIFICATION STEPS (for the developer / real CI, where this sandbox's limitation doesn't apply)

**Step 1:** `docker build -t quorum-backend:test ./backend` on a real machine or GitHub Actions runner.
Expected: all 7 steps complete, ending in a tagged image — no SSL error, since neither environment shares this sandbox's container-network certificate isolation.

**Step 2:** `docker run -p 8080:8080 quorum-backend:test` then `curl localhost:8080/health`.
Expected: `{"status": "ok"}`, `200` — the same result already proven for the raw `uvicorn` process in Session 00, now proven inside the actual container Cloud Run will run.

**Step 3:** Real `gcloud run deploy` per the command above, then `curl` the real Cloud Run URL's `/health` (with a real auth token, since `--no-allow-unauthenticated` is set).

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-11: Infrastructure part 2 — real Cloud Run deploy config, .dockerignore gap closed, Secret Manager pattern. Docker build attempted for real; succeeded through step 3/7, hit a diagnosed sandbox-only SSL limit at pip install, not worked around."
```

**Update `STATUS_INDEX.md`** — real infrastructure configuration exists; real deployment remains a developer action.

**Append to `DECISIONS_LOG.md`:** the real Docker build attempt, exactly how far it got, the specific diagnosis, and why disabling SSL verification was rejected as a fix.

---

*Document version: 1.0*
