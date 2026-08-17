# IMPL_13: AGENT — EMAIL
## The first real LangGraph node in this project, actually compiled and invoked — not just imported

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §7 (orchestration), §9.1 (Email), §14.3 (two-layer authorization)

**Prerequisites:** `IMPL_12`. Also builds directly on the already-real `features/style_reply.py`.

**Review tier:** STANDARD for the graph node logic; the tool-authorization module is genuinely security-relevant (it's the second of the two layers §14.3 describes) but small and narrow enough that fresh-context review is proportionate — CRITICAL tier is reserved for the Gate/secrets/auth work already done, not every security-adjacent line thereafter.

**What makes this session genuinely new, not another module:** every backend session before this produced real, tested Python functions. This is the first one that actually builds a `langgraph.graph.StateGraph`, compiles it, and calls `.invoke()` on it for real — proven by `test_real_compiled_graph_produces_a_real_proposal`, which doesn't test the underlying function in isolation, it runs the actual graph.

**What this session creates:** `backend/agents/tool_authorization.py` (the real second-layer check), `backend/agents/email_agent.py` (the real graph).

**Out of scope:** the real Gmail API calls themselves (`gmail.send`, `gmail.read`, etc.) — those need live OAuth credentials this environment doesn't have; the `llm_call` and the eventual real MCP tool execution are both injected dependencies here, the same pattern already proven throughout this project. Also out of scope: `Waiting On`'s own graph node — `waiting_on.py` is already real as a standalone module; wiring it into this same graph as a second node is a small, natural follow-up, not bundled into this session to keep this one's scope bounded.

---

## FILE 1: `backend/agents/tool_authorization.py` (real, complete — see file)

**The concrete proof of the two-layer authorization claim, not just an assertion of it.** `DOMAIN_TOOL_MAP` fails closed by construction — `dict.get(domain, set())` means any domain not explicitly listed gets an empty allowed-set, never a default-allow. Proven by `test_an_unrecognized_domain_fails_closed_not_open`, which deliberately misspells a domain name and confirms it's rejected exactly like a genuinely malicious one would be.

## FILE 2: `backend/agents/email_agent.py` (real, complete — see file)

Built directly on top of the already-real, already-tested `style_reply.py` — this session didn't reimplement style-conditioned drafting, it wrapped the existing real logic into a graph node via the same factory-function injection pattern already proven (`make_draft_reply_node(llm_call)`, matching `verdict_outcome_mapping.py` and every Gate validator's adapter pattern).

**The real proof this graph actually runs, not just imports cleanly:**
```python
graph = build_email_agent_graph(llm_call=fake_llm)
result = graph.invoke({...})
assert result["proposal"].action_type == ActionType.SEND_EMAIL
```
This is a genuine `.invoke()` call against a genuinely compiled `StateGraph` — confirmed by first writing a minimal, separate proof-of-concept graph against the real, currently-installed LangGraph 1.2.11 API before building the real Email agent around it, since LangGraph's API has changed meaningfully across versions and trusting a remembered API would have been exactly the kind of unverified assumption this project doesn't make.

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → Expected: `All checks passed!` — **verified live, this run, clean on the first pass.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_email_agent.py -v` → Expected: `5 passed` — **verified live, this run.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **88 passed** (83 prior + 5 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-13: Agent — Email. First real, genuinely-invoked LangGraph graph in this project. Two-layer tool authorization's second layer proven to fail closed. 5/5 tests passing, 88/88 total suite."
```

**Update `STATUS_INDEX.md`** — the Email agent moves from "not built" to real; note that this is also the first session where `langgraph` becomes a real runtime dependency, not just an architectural decision.

**Append to `DECISIONS_LOG.md`:** the real LangGraph version confirmed (1.2.11), and the fail-closed authorization proof.

---

*Document version: 1.0 — `IMPL_14` (Calendar) follows the same graph-node pattern this session established.*
