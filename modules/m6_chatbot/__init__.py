"""
Module 6: RAG Chatbot.
Governing Rules: RULES.md §1.3, §2, §4.3, §4.7; SPEC §3.4; IMPLEMENTATION_PLAN Phase 9.
"""

from modules.m6_chatbot.cache import chat_cache
from modules.m6_chatbot.chat_service import (
    create_chat_session,
    get_session_history,
    process_chat_message,
)
from modules.m6_chatbot.generator import generate_grounded_answer
from modules.m6_chatbot.retriever import retrieve_rag_context

__all__ = [
    "chat_cache",
    "retrieve_rag_context",
    "generate_grounded_answer",
    "create_chat_session",
    "process_chat_message",
    "get_session_history",
]
