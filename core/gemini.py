import os
import json
import re

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
        "max_output_tokens": 3500
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


def clean_json_response(response_text):
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Gemini returned an empty response.")

    text = response_text.strip()

    # Remove Markdown code fences.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(r"\s*```$", "", text)

    # First try parsing the complete response.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first complete JSON object or array.
    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character in "{[":
            try:
                result, _ = decoder.raw_decode(text[index:])
                return result
            except json.JSONDecodeError:
                continue

    raise ValueError("No valid JSON object was found.")


def generate_json(prompt):
    response_text = generate_response(
        prompt,
        temperature=0.0,
        json_mode=True
    )

    try:
        return clean_json_response(response_text)

    except (ValueError, json.JSONDecodeError):
        # Retry once with stricter JSON instructions.
        retry_prompt = f"""
{prompt}

IMPORTANT RETRY INSTRUCTIONS:
Your previous response could not be parsed.
Return one complete, valid JSON object.
Do not include Markdown code fences.
Do not include explanations before or after the JSON.
Do not truncate the response.
Use the exact keys and structure requested above.
"""

        retry_response = generate_response(
            retry_prompt,
            temperature=0.0,
            json_mode=True
        )

        try:
            return clean_json_response(retry_response)

        except (ValueError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "Gemini could not produce valid JSON after one retry. "
                "Please run the analysis again."
            ) from error