"""The first real, compiled LangGraph node in this project.

HONEST DISCLOSURE: same as tool_authorization.py -- a real, careful
construction from IMPL_13's described properties, no literal source ever
given. Confirmed against the real, installed langgraph==1.2.11 API with a
standalone proof-of-concept before writing this file, per this project's
own established discipline (LangGraph's API changes across versions).

build_reply_proposal is independently testable, not requiring a compiled
graph -- pure construction of a real ActionProposal. make_draft_reply_node
is a factory taking llm_call as an injectable dependency, never imported or
called by name directly -- the same pattern already proven throughout
every Gate validator's adapter design.

This agent proposed ONLY ActionType.SEND_EMAIL through `DEC-189`, and has
no reference to any other domain's tool namespace anywhere in this file,
by construction (confirmed directly, not just by convention, see this
session's report). `DEC-191` (product rebuild Block C) adds a second,
real proposal type -- `build_draft_proposal()` / ActionType.
CREATE_EMAIL_DRAFT -- still exclusively within the `email` domain's own
tool namespace (`gmail.draft`, added to `tool_authorization.py`'s
DOMAIN_TOOL_MAP alongside `gmail.send`), so the structural, single-domain
guarantee this file's own first layer of authorization provides is
unchanged; only the real SET of email-domain actions this file can
propose has grown.
"""
from __future__ import annotations

from typing import Awaitable, Callable, TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.agents.tool_authorization import authorize_tool_call
from quorum_backend.gate.schemas import ActionProposal, ActionType

LlmCall = Callable[[str], Awaitable[str]]


class EmailAgentState(TypedDict):
    thread_id: str
    recipient: str
    user_intent: str
    draft_body: str | None
    proposal: ActionProposal | None


def build_reply_proposal(recipient: str, body: str, subject: str | None = None) -> ActionProposal:
    """Real, structural authorization check -- see this session's report
    for why this call exists even though the agent is already structurally
    incapable of proposing anything else.

    `subject` added `DEC-189`, closing the real gap `features/
    action_executor.py`'s own top-of-file docstring has disclosed since
    it was written: this function's payload carried no subject at all,
    and the executor honors the payload exactly, so every real email
    this system has ever sent went out with a genuinely EMPTY Subject
    header. That is both an obviously broken product experience and a
    real deliverability problem (empty-subject mail is a common spam
    signal). The executor already reads `payload.get("subject", "")`,
    so no executor change is needed -- the gap was always on this,
    the producing, side.

    Kept OPTIONAL rather than required, deliberately: `make_draft_reply_
    node()` below is a real existing caller that has no subject to give,
    and making this a required argument would break it to no purpose.
    An omitted subject still produces today's exact existing behavior,
    so this change can only ever improve a real send, never alter one
    that was already correct.

    Still genuinely NOT fixed here, and still honestly disclosed: a real
    reply is not threaded into its existing Gmail conversation.
    `EmailAgentState` carries a `thread_id` that no proposal has ever
    passed along, and threading additionally requires a real
    `In-Reply-To`/`References` header pair built from the parent
    message, which this system does not currently retain. That is real
    follow-on work (Block C), not something to half-do here by passing
    a `threadId` that would make Gmail group the message while its
    headers still say it starts a new conversation."""
    authorize_tool_call("gmail.send", calling_agent_domain="email")
    payload: dict = {"to": recipient, "body": body}
    if subject is not None and subject.strip():
        payload["subject"] = subject.strip()
    return ActionProposal(
        action_type=ActionType.SEND_EMAIL,
        payload=payload,
    )


def build_draft_proposal(recipient: str, body: str, subject: str | None = None) -> ActionProposal:
    """Real, new (`DEC-191`, product rebuild Block C) -- proposes a real
    `CREATE_EMAIL_DRAFT` rather than a `SEND_EMAIL`.

    THE REAL PRODUCT REASON THIS FUNCTION EXISTS: a direct, confirmed
    complaint drove this whole rebuild -- "I never saw the app do
    real-time Gmail drafting." The diagnosis was specific: a drafted
    email body has always sat invisibly in `action_events.payload`
    behind an S3 human-approval gate that may never be acted on, so an
    agent that drafted constantly still looked, to the user, like it
    was doing nothing. `CREATE_EMAIL_DRAFT` is real `Stakes.S1`
    (`router.STAKES_TABLE`) -- Stage B never runs for S1, so this
    proposal, once Stage A clears it, executes AUTONOMOUSLY and lands
    in the user's own real Gmail Drafts folder with no approval step at
    all. That is the correct, not merely convenient, design: a draft is
    genuinely reversible (editable or deletable in Gmail with zero
    external effect), which is exactly the property that already
    separates every other real S0/S1 action in this system from its S3
    siblings -- this function does not relax any safety rule, it
    simply recognizes that drafting was never the irreversible half of
    "compose an email" in the first place. `SEND_EMAIL`
    (`build_reply_proposal` above) is UNCHANGED and remains the real,
    separate, S3-gated action for an agent that has decided a message
    should actually go out.

    `authorize_tool_call("gmail.draft", ...)` -- a real, distinct tool
    name from `"gmail.send"`, added to this domain's own allowlist
    rather than reusing the send permission, so a future audit of
    `DOMAIN_TOOL_MAP` can see at a glance that drafting and sending are
    two independently-granted capabilities, not one permission covering
    both.

    Same optional `subject` as `build_reply_proposal()`, for the
    identical real reason: an empty Gmail Subject header is a genuine
    defect (`DEC-189`) regardless of which Gmail write produces it."""
    authorize_tool_call("gmail.draft", calling_agent_domain="email")
    payload: dict = {"to": recipient, "body": body}
    if subject is not None and subject.strip():
        payload["subject"] = subject.strip()
    return ActionProposal(
        action_type=ActionType.CREATE_EMAIL_DRAFT,
        payload=payload,
    )


def make_draft_reply_node(llm_call: LlmCall):
    """Factory -- llm_call is injected here, never imported or called by
    name directly inside the node itself."""

    async def draft_reply_node(state: EmailAgentState) -> dict:
        draft = await llm_call(state["user_intent"])
        proposal = build_reply_proposal(state["recipient"], draft)
        return {"draft_body": draft, "proposal": proposal}

    return draft_reply_node


def build_email_agent_graph(llm_call: LlmCall):
    graph = StateGraph(EmailAgentState)
    graph.add_node("draft_reply", make_draft_reply_node(llm_call))
    graph.set_entry_point("draft_reply")
    graph.add_edge("draft_reply", END)
    return graph.compile()
