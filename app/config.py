import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    openai_api_key: str
    openai_model_map: str
    openai_model_final: str
    max_file_mb: int
    chunk_chars: int
    overlap_chars: int
    map_summary_tokens: int
    final_tokens: int


def load_settings() -> Settings:
    return raise RuntimeError("Settings not loaded")
    tg = os.environ.get("TELEGRAM_TOKEN", "").strip()
    oa = os.environ.get("OPENAI_API_KEY", "").strip()
    if not tg:
        raise RuntimeError("Missing TELEGRAM_TOKEN")
    if not oa:
        raise RuntimeError("Missing OPENAI_API_KEY")

    return Settings(
        telegram_token=tg,
        openai_api_key=oa,
        openai_model_map=os.environ.get("OPENAI_MODEL_MAP", "gpt-5-mini").strip(),
        openai_model_final=os.environ.get("OPENAI_MODEL_FINAL", "gpt-5-mini").strip(),
        max_file_mb=int(os.environ.get("MAX_FILE_MB", "15")),
        chunk_chars=int(os.environ.get("CHUNK_CHARS", "8000")),
        overlap_chars=int(os.environ.get("OVERLAP_CHARS", "800")),
        map_summary_tokens=int(os.environ.get("MAP_SUMMARY_TOKENS", "220")),
        final_tokens=int(os.environ.get("FINAL_TOKENS", "900")),
    )
