"""Real tests for gate/prompts.py. Currently covers only the CoverageCheck
extraction prompt (IMPL_07) -- Critic/Judge prompt tests are added whenever
IMPL_08's real orchestration work actually builds those prompts."""
from quorum_backend.gate.prompts import build_coverage_extraction_prompt


def test_coverage_extraction_prompt_includes_source_body():
    body = "Can we move our 3pm to Thursday, and can you also send the invoice?"
    rendered = build_coverage_extraction_prompt(body)
    assert body in rendered


def test_coverage_extraction_prompt_is_real_text_not_a_stub():
    rendered = build_coverage_extraction_prompt("test body")
    assert "question" in rendered.lower()
    assert len(rendered) > 50
