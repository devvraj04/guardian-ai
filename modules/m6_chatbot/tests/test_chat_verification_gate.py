"""
Architectural Invariant Test for Module 6 (RULES.md §1.3; STATUS.md line 102).

INVARIANT:
Every chatbot answer emitted by process_chat_message MUST be created as a Claim
(source_module="chatbot") and route through verify_and_resolve_claim() before presentation.
There is NO separate response path or bypass branch for conversational output.
"""

import ast
from pathlib import Path


def test_no_separate_unverified_chatbot_response_path():
    service_file = Path(__file__).resolve().parents[1] / "chat_service.py"
    assert service_file.exists(), "chat_service.py not found in Module 6"

    with open(service_file, "r", encoding="utf-8") as f:
        source_code = f.read()

    # 1. AST verification that verify_and_resolve_claim is called
    tree = ast.parse(source_code, filename="chat_service.py")
    calls_verifier_gate = False
    emits_chatbot_claim = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "verify_and_resolve_claim"
            ):
                calls_verifier_gate = True
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "verify_and_resolve_claim"
            ):
                calls_verifier_gate = True

        if isinstance(node, ast.Constant) and node.value == "chatbot":
            emits_chatbot_claim = True

    assert calls_verifier_gate, "Critical Invariant Violation (RULES.md §1.3): chat_service.py must call verify_and_resolve_claim"
    assert emits_chatbot_claim, "Critical Invariant Violation (RULES.md §4.7): chat_service.py must emit Claim with source_module='chatbot'"

    # 2. Text inspection: ensure no bypass flags exist in chat module
    forbidden_tokens = [
        "skip_verif",
        "bypass_verification",
        "skip_verification",
        "TRUSTED_SOURCE",
    ]
    for token in forbidden_tokens:
        assert (
            token.lower() not in source_code.lower()
        ), f"Forbidden bypass token '{token}' detected in chat_service.py"
