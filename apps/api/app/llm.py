"""Single entry point for all LLM calls (Groq, OpenAI-compatible API)."""
import httpx

from .config import settings

GROQ_BASE = "https://api.groq.com/openai/v1"


def _headers() -> dict:
    if not (settings.groq_api_key and settings.groq_model):
        raise RuntimeError("Set GROQ_API_KEY and GROQ_MODEL in apps/api/.env")
    return {"Authorization": f"Bearer {settings.groq_api_key}"}


def chat(prompt: str, system: str | None = None, temperature: float = 0.2) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    r = httpx.post(
        f"{GROQ_BASE}/chat/completions",
        headers=_headers(),
        json={"model": settings.groq_model, "messages": messages, "temperature": temperature},
        timeout=90,
    )
    if r.status_code != 200:
        raise RuntimeError(f"LLM error {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"] or ""


def list_models() -> list[str]:
    r = httpx.get(f"{GROQ_BASE}/models", headers=_headers(), timeout=30)
    r.raise_for_status()
    return sorted(m["id"] for m in r.json().get("data", []))