"""Groq AI assistant integration with retry logic."""
from __future__ import annotations

from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.utils.logger import logger

_client: AsyncGroq | None = None


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def generate_response(
    system_prompt: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    """
    Call the Groq chat completion API and return the assistant's reply.

    Args:
        system_prompt: The business context system prompt.
        history:       List of prior {role, content} messages (excluding latest user msg).
        user_message:  The user's latest message text.

    Returns:
        The assistant's response text.
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = get_client()
    completion = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        stream=False,
    )

    reply = completion.choices[0].message.content or ""
    logger.debug(
        "groq.response",
        model=settings.groq_model,
        input_tokens=completion.usage.prompt_tokens if completion.usage else None,
        output_tokens=completion.usage.completion_tokens if completion.usage else None,
    )
    return reply.strip()
