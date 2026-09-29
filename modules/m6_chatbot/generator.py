"""
Answer Generator for Module 6 (RAG Chatbot).
Governing Rules: RULES.md §5.5; SPEC §3.4; IMPLEMENTATION_PLAN Phase 9.

Generates concise, factual, legally-grounded answers to borrower queries.
Uses pre-computed cache for demo queries and Groq LLM with deterministic fallback.
"""

from typing import List, Tuple
from groq import Groq

from app.core.config import settings
from app.core.logging import logger
from app.schemas.chat import RetrievedContextCitation
from modules.m6_chatbot.cache import chat_cache


def generate_grounded_answer(
    query: str,
    context: str,
    citations: List[RetrievedContextCitation],
    use_cache: bool = True,
) -> Tuple[str, List[RetrievedContextCitation], bool]:
    """
    Produces a grounded answer given the user query and retrieved context.
    Returns (answer_text, citations_used, is_cached).
    """
    # 1. Check Pre-computed Demo Cache (RULES.md §5.5)
    if use_cache:
        cached_result = chat_cache.get(query)
        if cached_result:
            answer, cached_cites = cached_result
            structured_cites = [
                RetrievedContextCitation(
                    source=c["source"],  # type: ignore
                    citation_id=c["citation_id"],
                    text=c["text"],
                )
                for c in cached_cites
            ]
            return answer, (structured_cites or citations), True

    # 2. Call Groq LLM if API Key is available
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("test_"):
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            system_prompt = (
                "You are GUARDIAN, an AI assistant protecting digital lending borrowers in India.\n"
                "Answer the user's question accurately and objectively using ONLY the retrieved context provided.\n"
                "If the context cites specific clauses (e.g., Clause 4.1, Clause 5.2), cite them explicitly.\n"
                "If the context does not contain sufficient evidence to answer, state clearly that the provided "
                "loan documents and RBI regulations do not verify the claim.\n"
                "Keep your answer under 3 sentences. Be factual, concise, and professional."
            )
            user_prompt = (
                f"RETRIEVED CONTEXT:\n{context}\n\n" f"USER QUESTION:\n{query}"
            )

            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            answer = response.choices[0].message.content or ""
            if answer.strip():
                return answer.strip(), citations, False

        except Exception as e:
            logger.warning(
                f"Groq chat generation failed: {e}. Using grounded extraction fallback."
            )

    # 3. Grounded Fallback Synthesizer
    if citations:
        best_passage = citations[0].text
        citation_id = citations[0].citation_id
        answer = f"According to {citation_id}: {best_passage.strip()}"
    else:
        answer = "I could not locate sufficient evidence in your loan documents or RBI digital lending directions to answer this inquiry."

    return answer, citations, False
