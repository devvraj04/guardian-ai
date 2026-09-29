"""
Module 5: Grievance Classification & Redressal.
Governing Rules: RULES.md §1.3, §4.3, §4.7; SPEC §3.4; IMPLEMENTATION_PLAN Phase 8.
"""

from modules.m5_grievance.classifier import grievance_classifier
from modules.m5_grievance.dispute_service import create_user_dispute, list_user_disputes

__all__ = [
    "grievance_classifier",
    "create_user_dispute",
    "list_user_disputes",
]
