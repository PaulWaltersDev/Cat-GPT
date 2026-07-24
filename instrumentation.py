"""
Arize AX tracing instrumentation for cat_gpt.

This module must be imported before any OpenAI imports to ensure
proper tracing setup.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from arize.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor

# Register Arize tracer with credentials from environment
tracer_provider = register(
    space_id=os.environ.get("ARIZE_SPACE_ID"),
    api_key=os.environ.get("ARIZE_API_KEY"),
    project_name=os.environ.get("ARIZE_PROJECT_NAME", "cat_gpt"),
)

# Instrument OpenAI SDK to automatically capture traces
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

print("Arize AX tracing initialized for OpenAI.")
