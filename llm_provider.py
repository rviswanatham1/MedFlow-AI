"""
LLM Provider Factory — supports Anthropic Claude, Google Gemini, and DeepSeek / Ollama.
"""

from typing import Optional


def get_llm(
    provider: str = "ollama",
    model_name: str = "deepseek-r1:8b",
    api_key: Optional[str] = None,
    base_url: str = "http://localhost:11434",
    temperature: float = 0.1,
):
    """
    Return a LangChain chat model for the chosen provider.

    provider   : "anthropic" | "gemini" | "ollama"
    model_name : Claude model ID, Gemini model ID, or Ollama model tag
    api_key    : Required for Anthropic and Gemini; ignored for Ollama
    base_url   : Ollama endpoint; ignored for cloud providers
    temperature: Sampling temperature (0 = deterministic)
    """
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "Anthropic support requires: pip install langchain-anthropic"
            )
        if not api_key:
            raise ValueError("An Anthropic API key is required for the Anthropic provider.")
        return ChatAnthropic(
            model=model_name or "claude-3-5-haiku-20241022",
            anthropic_api_key=api_key,
            temperature=temperature,
        )

    elif provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "Google Gemini support requires: pip install langchain-google-genai"
            )
        if not api_key:
            raise ValueError("A Google API key is required for the Gemini provider.")
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-1.5-flash",
            google_api_key=api_key,
            temperature=temperature,
        )

    else:
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError(
                "Ollama support requires: pip install langchain-ollama"
            )
        return ChatOllama(
            model=model_name or "deepseek-r1:8b",
            temperature=temperature,
            base_url=base_url,
        )
