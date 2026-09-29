"""
Architectural Invariant Test for Module 4 (RULES.md §1.6).

RULE 1.6:
Module 4 (vernacular) imports and calls Module 3's verifier functions.
It does not fork, copy, or reimplement any part of the semantic or numeric check.
"""

import ast
from pathlib import Path


def test_module3_import_integrity():
    m4_dir = Path(__file__).resolve().parents[1]
    verifier_file = m4_dir / "vernacular_verifier.py"

    assert verifier_file.exists(), "vernacular_verifier.py not found in Module 4"

    with open(verifier_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="vernacular_verifier.py")

    imports_module3 = False
    imported_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "modules.m3_verifier" in node.module:
                imports_module3 = True
                for alias in node.names:
                    imported_names.add(alias.name)

    assert (
        imports_module3
    ), "Module 4 must import from modules.m3_verifier (RULES.md §1.6)"
    assert (
        "verify_claim" in imported_names
    ), "Module 4 must import verify_claim from Module 3"
    assert (
        "verify_semantic_entailment" in imported_names
    ), "Module 4 must import verify_semantic_entailment from Module 3"
