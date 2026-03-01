from __future__ import annotations

from openai import OpenAI


class LLM:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def summarize_chunk(
        self, model: str, system: str, prompt: str, max_output_tokens: int
    ) -> str:
        resp = self.client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=max_output_tokens,
        )
        return (getattr(resp, "output_text", "") or "").strip()

    def generate(
        self, model: str, system: str, prompt: str, max_output_tokens: int
    ) -> str:
        resp = self.client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=max_output_tokens,
        )
        return (getattr(resp, "output_text", "") or "").strip()
