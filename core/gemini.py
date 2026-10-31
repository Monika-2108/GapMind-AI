import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.5-flash-lite"

client = (
    genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(timeout=60000)
    )
    if API_KEY else None
)


def gemini_available():
    return client is not None


def generate_response(prompt, temperature=0.1, json_mode=False):
    if not client:
        raise RuntimeError(
            "Gemini API key not found. Check your .env file."
        )

    config_options = {
        "temperature": temperature,
        "max_output_tokens": 1800
    }

    if json_mode:
        config_options["response_mime_type"] = "application/json"

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(**config_options)
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        return response.text.strip()

    except Exception as error:
        raise RuntimeError(
            f"Gemini ({MODEL_NAME}) failed: {error}"
        ) from error


def generate_text(prompt, temperature=0.1):
    return generate_response(prompt, temperature)


def generate_json(prompt):
    response_text = generate_response(
        prompt,
        temperature=0.1,
        json_mode=True
    )

    try:
        return json.loads(response_text)

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Gemini returned invalid JSON. Please try again."
        ) from error