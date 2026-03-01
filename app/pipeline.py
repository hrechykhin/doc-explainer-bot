from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .prompts import (
    SYSTEM_MAP,
    SYSTEM_FINAL,
    map_prompt,
    final_explain_prompt,
    final_qa_prompt,
)
from .llm import LLM


def chunk_text(text: str, chunk_chars: int, overlap_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + chunk_chars)
        chunk = text[i:j]
        chunks.append(chunk)
        if j == n:
            break
        i = max(0, j - overlap_chars)
    return chunks


@dataclass
class PipelineResult:
    ok: bool
    map_summaries: list[str]
    error: Optional[str] = None


def build_map_summaries(
    llm: LLM,
    text: str,
    model_map: str,
    chunk_chars: int,
    overlap_chars: int,
    map_summary_tokens: int,
    max_chunks: int = 20,
) -> PipelineResult:
    chunks = chunk_text(text, chunk_chars, overlap_chars)
    if not chunks:
        return PipelineResult(False, [], "No text to process.")

    if len(chunks) > max_chunks:
        # Hard cap to control costs; process head+tail to preserve endings.
        head = chunks[: max_chunks // 2]
        tail = chunks[-(max_chunks // 2) :]
        chunks = head + tail

    summaries: list[str] = []
    for c in chunks:
        p = map_prompt(c)
        s = llm.summarize_chunk(
            model=model_map,
            system=SYSTEM_MAP,
            prompt=p,
            max_output_tokens=map_summary_tokens,
        )
        summaries.append(s if s else "(empty summary)")
    return PipelineResult(True, summaries)


def explain_from_summaries(
    llm: LLM,
    filename: str,
    map_summaries: list[str],
    model_final: str,
    final_tokens: int,
) -> str:
    p = final_explain_prompt(filename, map_summaries)
    return llm.generate(
        model=model_final, system=SYSTEM_FINAL, prompt=p, max_output_tokens=final_tokens
    )


def answer_question_from_summaries(
    llm: LLM,
    filename: str,
    map_summaries: list[str],
    question: str,
    model_final: str,
    final_tokens: int,
) -> str:
    p = final_qa_prompt(filename, map_summaries, question)
    return llm.generate(
        model=model_final, system=SYSTEM_FINAL, prompt=p, max_output_tokens=final_tokens
    )


def summaries_to_json(summaries: list[str]) -> str:
    return json.dumps(summaries, ensure_ascii=False)


def summaries_from_json(s: str | None) -> list[str]:
    if not s:
        return []
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else []
    except Exception:
        return []
