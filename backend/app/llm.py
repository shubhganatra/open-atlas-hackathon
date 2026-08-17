"""Shared LLM client + model choice. One place to swap models or providers.

Provider history: Anthropic (original plan) -> Featherless AI (free hackathon
credits via promo code OPENATLAS26, 2026-08-15) -> Groq (2026-08-15, same day
— the Featherless credit path never materialized; see DECISIONS.md "LLM
provider: Groq"). Each swap has been a same-file change (base_url + api_key +
model) because the OpenAI-compatible client shape was kept provider-agnostic
from the start — that design paid off directly here.

Model: llama-3.3-70b-versatile — Groq's flagship for quality + reliable tool
use, which matters directly since app/intake/extractor.py, app/planner.py, and
app/artifacts.py all depend on *forced* tool-calling (tool_choice pointing at
one specific function), not just any tool call.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

client = OpenAI(
    # Unlike Anthropic's client, OpenAI's raises at construction time if
    # api_key is falsy — a placeholder keeps modules importable (and thus
    # testable) before backend/.env has a real key; actual calls will 401.
    api_key=os.environ.get("GROQ_API_KEY") or "unset-see-backend/.env",
    base_url="https://api.groq.com/openai/v1",
)
