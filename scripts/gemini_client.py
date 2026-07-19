"""
gemini_client.py
Thin wrapper around the Gemini API used for AI-powered security triage.

IMPORTANT: The model string below must remain exactly "gemini-3.5-flash".
Do not let any tooling "helpfully" downgrade this to an older model name
(e.g. gemini-1.5-flash, gemini-2.0-flash) that it may recognize from
training data. gemini-3.5-flash is required for this project.
"""

import time

import google.genai as genai
from google.genai import types

# Hard-coded model constant -- must stay exactly "gemini-3.5-flash".
GEMINI_MODEL = "gemini-3.5-flash"


class GeminiAPIError(Exception):
    """
    Raised when a Gemini API call fails in a way the pipeline should
    handle gracefully instead of crashing.

    Attributes:
        user_message:    Short, human-readable message safe to show in a
                          PR comment or console output.
        technical_detail: The underlying exception detail, useful for logs.
        error_code:       A short machine-readable code for the failure type.
    """

    def __init__(self, user_message: str, technical_detail: str = "", error_code: str = "GEMINI_ERROR"):
        self.user_message = user_message
        self.technical_detail = technical_detail
        self.error_code = error_code
        super().__init__(user_message)


class GeminiClient:
    """
    Wraps calls to the Gemini API for the security triage task.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise GeminiAPIError(
                user_message="No Gemini API key was provided.",
                technical_detail="GeminiClient.__init__ received an empty/None api_key.",
                error_code="MISSING_API_KEY",
            )
        self.client = genai.Client(api_key=api_key)

    def triage(self, prompt: str, max_retries: int = 2) -> str:
        """
        Sends `prompt` to Gemini and returns the raw text response.

        Retries transient failures a small number of times before raising
        a GeminiAPIError with a user-friendly message.
        """
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,  # Low temperature: this is classification/ranking, not creative writing.
                        max_output_tokens=2048,
                    ),
                )
                if not response or not getattr(response, "text", None):
                    raise ValueError("Empty response from Gemini API")
                return response.text
            except Exception as exc:  # noqa: BLE001 - we deliberately catch broadly here
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break

        raise GeminiAPIError(
            user_message=(
                "AI triage step failed to get a response from Gemini after "
                f"{max_retries + 1} attempt(s). Raw scan results are still available "
                "in the Actions log."
            ),
            technical_detail=str(last_exc),
            error_code="GEMINI_CALL_FAILED",
        )
