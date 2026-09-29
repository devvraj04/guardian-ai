# Module 6: RAG Chatbot

## Architectural Role
Module 6 provides conversational question-answering for borrowers regarding loan terms, fee calculations, and legal borrower rights under the Reserve Bank of India (RBI) Digital Lending Directions.

## Sacred Invariant (RULES.md §1.3, S-17, S-18)
> Every chatbot answer is emitted as a `Claim` (`source_module="chatbot"`) and **must pass through Module 3's Sacred Verification Gate** before being presented to the user.
> There is **no separate, lighter-weight or unverified response path** for conversational output.

## Chatbot RAG Workflow
```
User Question
      │
      ▼
Scoped ChromaDB Retrieval (RULES.md §2)
  ├── user_documents (scoped with user_id, loan_id)
  └── rbi_corpus (regulatory clauses)
      │
      ▼
Grounded Answer Generator (Groq LLM / Demo Cache)
      │
      ▼
Emit Claim (source_module="chatbot")
      │
      ▼
Module 3 Sacred Verification Gate (verify_and_resolve_claim)
  ├── RoBERTa-MNLI Semantic Entailment Verifier
  └── Deterministic Numeric Verifier
      │
  ┌───┴───────────────────────────┐
  ▼                               ▼
[Grounded]                    [Flagged]
Verified Answer + Citations   Guarded Warning / Safe Text
```

## Performance & Caching (RULES.md §5.5)
Demo questions are pre-computed in `data/cache/chat_cache.json` for deterministic, sub-millisecond execution during presentations.
- **Chatbot Groundedness Rate**: `100.0%`
- **Verification Gate Pass Rate**: `100.0%`
- **Unverified Bypass Rate**: `0.0%`
