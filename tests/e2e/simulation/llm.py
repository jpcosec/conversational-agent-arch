"""Cliente LLM con salida JSON tipada para el harness de simulacion.

Un unico puerto (``JsonLLM.complete``) usado por el usuario simulado y por el
juez. La implementacion real es Gemini con ``response_schema`` (pydantic) y
temperatura 0; los tests del harness usan ``ScriptedJsonLLM``.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class JsonLLM(Protocol):
    def complete(self, prompt: str, schema: type[T]) -> T: ...


class GeminiJsonLLM:
    def __init__(self, client: Any, model: str, temperature: float = 0.0) -> None:
        self._client = client
        self.model = model
        self.temperature = temperature
        self.calls = 0

    def complete(self, prompt: str, schema: type[T]) -> T:
        from google.genai import types

        self.calls += 1
        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=self.temperature,
            ),
        )
        parsed = resp.parsed
        if isinstance(parsed, schema):
            return parsed
        return schema.model_validate_json(resp.text or "{}")


class ScriptedJsonLLM:
    """Devuelve respuestas predefinidas (para probar el harness sin red)."""

    def __init__(self, responder: Callable[[str, type[BaseModel]], BaseModel]) -> None:
        self._responder = responder
        self.prompts: list[str] = []

    def complete(self, prompt: str, schema: type[T]) -> T:
        self.prompts.append(prompt)
        out = self._responder(prompt, schema)
        assert isinstance(out, schema)
        return out
