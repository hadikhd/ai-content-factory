# tools/ollama_client.py
from __future__ import annotations

import time
import logging
from typing import Generator, Optional

import ollama

# --------------------------------------------------
# Logging
# --------------------------------------------------
logger = logging.getLogger("ollama")
logger.setLevel(logging.INFO)

# --------------------------------------------------
# Defaults (safe for LangGraph)
# --------------------------------------------------
DEFAULT_MODEL = "gemma3:4b"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 2048
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.5


# --------------------------------------------------
# Internal helper
# --------------------------------------------------
def _generate(
    *,
    prompt: str,
    model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    stream: bool,
):
    """
    Internal Ollama generate wrapper.
    Always uses options={} (required by new Ollama client).
    """

    return ollama.generate(
        model=model,
        prompt=prompt,
        stream=stream,
        options={
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        },
    )


# --------------------------------------------------
# Non-streaming call (agents)
# --------------------------------------------------
def call_ollama(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
) -> str:
    """
    Safe non-streaming Ollama call.
    Used by LangGraph agents.
    """

    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Ollama call (attempt {attempt}/{retries})")

            res = _generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
)           # type: ignore
            res:dict = dict(res)
            # safely extract text from ollama response
            if isinstance(res, dict):
                text = res.get("response", "")
            elif hasattr(res, "response"):
                 text = res.response
            else:
                text = str(res)
                text = text.strip()

            if not text:
                raise ValueError("Empty response from Ollama")

            return text

        except Exception as e:
            last_error = e
            logger.warning(f"Ollama attempt {attempt} failed: {e}")

            if attempt < retries:
                time.sleep(backoff ** attempt)

    logger.error("Ollama call completely failed")
    raise RuntimeError("Ollama generation failed") from last_error


# --------------------------------------------------
# Streaming call (Gradio)
# --------------------------------------------------
def stream_ollama(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
) -> Generator[str, None, None]:
    """
    Streaming Ollama generator.
    Safe for Gradio streaming outputs.
    """

    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Ollama stream (attempt {attempt}/{retries})")

            stream = _generate(
                prompt=prompt,
                model=model,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in stream:
                if isinstance(chunk, dict):
                    text = chunk.get("response", "")
                    if text:
                        yield text

            return

        except Exception as e:
            last_error = e
            logger.warning(f"Ollama stream attempt {attempt} failed: {e}")

            if attempt < retries:
                time.sleep(backoff ** attempt)

    logger.error("Ollama streaming failed")
    raise RuntimeError("Ollama streaming failed") from last_error
