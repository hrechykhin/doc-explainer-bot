SYSTEM_MAP = (
    "You summarize document chunks. Be accurate and concise. "
    "Do not invent facts. If the chunk is not meaningful text, say so."
)

SYSTEM_FINAL = (
    "You explain documents for a user. Be clear and structured. "
    "Separate facts from interpretation. If information is missing, say so explicitly. "
    "This is not legal advice."
)


def map_prompt(chunk_text: str, max_bullets: int = 8) -> str:
    return f"""Summarize this document chunk.

Rules:
- Output 5–{max_bullets} bullet points.
- Include key obligations, dates, money, parties, and constraints if present.
- If the chunk is boilerplate, say so.
- No hallucinations.

CHUNK:
{chunk_text}
"""


def final_explain_prompt(filename: str, map_summaries: list[str]) -> str:
    joined = "\n".join(f"- {s.strip()}" for s in map_summaries if s.strip())
    return f"""You have summaries of chunks from a document: {filename}

Produce a concise Telegram-ready markdown answer:

## Document Brief: {filename}
**TL;DR:** (3–6 bullets)
### Key Points
### Obligations / Responsibilities
### Risks / Red Flags
### Dates & Deadlines
### Money / Fees
### Suggested Next Actions (practical)
### Open Questions (what user should clarify)

Use only the info present in the summaries. If uncertain, say so.

Chunk summaries:
{joined}
"""


def final_qa_prompt(filename: str, map_summaries: list[str], question: str) -> str:
    joined = "\n".join(f"- {s.strip()}" for s in map_summaries if s.strip())
    return f"""You have summaries of chunks from a document: {filename}

Answer the user's question using only the info in the summaries.
If the summaries don't contain the answer, say what is missing and where to look.

User question: {question}

Output concise markdown suitable for Telegram.

Chunk summaries:
{joined}
"""
