"""Offline GGUF coding assistant for VynStudio (llama-cpp-python)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

_SYSTEM = (
    "You are an expert Vyn programming language assistant. "
    "Vyn syntax: fn, let, mut, struct, enum, match, try/catch, hot fn, import std.io. "
    "Respond with valid Vyn code only when asked to write code."
)


class GgufAssistant:
    def __init__(self):
        self._llm = None
        self.model_path: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._llm is not None

    def load(self, path: str) -> tuple[bool, str]:
        p = Path(path)
        if not p.exists():
            return False, f"File not found: {path}"
        if p.suffix.lower() != ".gguf":
            return False, "Please select a .gguf model file"
        try:
            from llama_cpp import Llama
        except ImportError:
            return False, "Install llama-cpp-python: pip install llama-cpp-python"
        try:
            self._llm = Llama(model_path=str(p), n_ctx=4096, n_threads=4, verbose=False)
            self.model_path = str(p)
            return True, f"Loaded: {p.name}"
        except Exception as e:
            self._llm = None
            self.model_path = None
            return False, f"Load failed: {e}"

    def unload(self) -> None:
        self._llm = None
        self.model_path = None

    def generate_vyn(self, user_prompt: str, context: str = "") -> str:
        if not self._llm:
            return "No GGUF model loaded. Click 'Load GGUF Model' first."
        prompt = f"{_SYSTEM}\n\n"
        if context.strip():
            prompt += f"Current file:\n```vyn\n{context[:3000]}\n```\n\n"
        prompt += f"User request: {user_prompt}\n\nVyn code:"
        try:
            out = self._llm(
                prompt,
                max_tokens=1200,
                temperature=0.15,
                stop=["```", "\n\n\n"],
            )
            text = out["choices"][0]["text"].strip()
            return text if text else "(empty response)"
        except Exception as e:
            return f"Generation error: {e}"
