"""Gemini API client via REST (SDK-independent)."""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-2.0-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def get_api_key() -> str | None:
    load_dotenv(override=True)
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        key = key.strip().strip('"').strip("'")
    return key or None


def get_model_name() -> str:
    load_dotenv(override=True)
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def generate_text(prompt: str, temperature: float = 0.7) -> str:
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY が設定されていません。.env ファイルに API キーを設定してください。"
        )

    model = get_model_name()
    url = f"{API_BASE}/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }

    response = requests.post(
        url,
        params={"key": api_key},
        json=payload,
        timeout=120,
    )

    if response.status_code != 200:
        detail = response.text
        raise RuntimeError(f"Gemini API エラー ({response.status_code}): {detail}")

    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Gemini から有効な応答を取得できませんでした: {data}") from exc

    return text.strip()
