"""Core reasoning agents for Augury."""

from augury.agents.strategist import StrategistAgent
from augury.agents.analyst import (
    AnalystAgent,
    StubAnalystAgent,
    LLMAnalystAgent,
    BedrockAnalystAgent,
    get_analyst_agent,
)
from augury.agents.content import (
    ContentGeneratorAgent,
    BedrockContentGeneratorAgent,
    get_content_generator_agent,
)
from augury.agents.prompts import (
    STRATEGIST_SYSTEM_PROMPT,
    ANALYST_SYSTEM_PROMPT,
    ANALYST_HUMAN_PREAMBLE,
    CONTENT_SYSTEM_PROMPT,
    CONTENT_HUMAN_PREAMBLE,
)

__all__ = [
    "StrategistAgent",
    "AnalystAgent",
    "StubAnalystAgent",
    "LLMAnalystAgent",
    "BedrockAnalystAgent",
    "get_analyst_agent",
    "ContentGeneratorAgent",
    "BedrockContentGeneratorAgent",
    "get_content_generator_agent",
    "STRATEGIST_SYSTEM_PROMPT",
    "ANALYST_SYSTEM_PROMPT",
    "ANALYST_HUMAN_PREAMBLE",
    "CONTENT_SYSTEM_PROMPT",
    "CONTENT_HUMAN_PREAMBLE",
]
