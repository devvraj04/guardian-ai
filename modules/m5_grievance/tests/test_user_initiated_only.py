"""
Architectural Invariant Test for Module 5 (SPEC §3.4; IMPLEMENTATION_PLAN Phase 8).

INVARIANT:
Grievance classification and dispute creation is ONLY triggered on explicit
user-initiated dispute — a support path, never part of the automated pipeline or cron.
"""

from pathlib import Path
import re


def test_no_automated_dispute_creation():
    root_dir = Path(__file__).resolve().parents[3]

    # Directories that must NEVER trigger dispute creation automatically
    automated_pipeline_dirs = [
        root_dir / "modules" / "m0_intake",
        root_dir / "modules" / "m1_recompute",
        root_dir / "modules" / "m1b_serviceability",
        root_dir / "modules" / "m2_consistency",
        root_dir / "modules" / "m3_verifier",
        root_dir / "modules" / "m4_vernacular",
    ]

    violations = []
    pattern = re.compile(r"\bcreate_user_dispute\b")

    for d in automated_pipeline_dirs:
        for py_file in d.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                if pattern.search(content):
                    violations.append(str(py_file.relative_to(root_dir)))

    assert (
        len(violations) == 0
    ), f"Grievance creation is user-initiated ONLY; forbidden call found in automated modules: {violations}"
