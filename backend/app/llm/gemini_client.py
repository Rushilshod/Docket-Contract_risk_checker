import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env", override=False)


def is_gemini_enabled() -> bool:
    api_key = ((os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip())
    return bool(api_key) and api_key != "REPLACE_ME"


def _clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_text(prompt: str, *, system_prompt: str | None = None, model: str | None = None) -> str | None:
    if not is_gemini_enabled():
        return None

    try:
        import google.generativeai as genai
    except Exception:
        return None

    api_key = ((os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip())
    if not api_key:
        return None

    os.environ.setdefault("GOOGLE_API_KEY", api_key)
    genai.configure(api_key=api_key)
    model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    generation_model = genai.GenerativeModel(model_name=model_name)

    full_prompt = prompt if system_prompt is None else f"{system_prompt}\n\n{prompt}"

    def _call_model() -> str | None:
        response = generation_model.generate_content(full_prompt)
        text = getattr(response, "text", None)
        if text:
            return text.strip()

        candidates = getattr(response, "candidates", None)
        if candidates:
            content = getattr(candidates[0], "content", None)
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    return "".join(getattr(part, "text", "") for part in parts if getattr(part, "text", None)).strip()
        return None

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_model)
            return future.result(timeout=15)
    except TimeoutError:
        return None
    except Exception:
        return None


def generate_json(prompt: str, *, system_prompt: str | None = None, model: str | None = None) -> dict[str, Any] | None:
    raw = generate_text(prompt, system_prompt=system_prompt, model=model)
    if not raw:
        return None

    cleaned = _clean_json_text(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
