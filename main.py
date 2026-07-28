"""
cat_gpt — LLM agent for answering questions about cats. Done as a demonstration of a simple agent
with included input and output guardrails for prompt injection, length and output toxicity.

Evals to be done with DeepEval unit tests and Arize Ax.

Takes a string request body (a JSON string, e.g. `"why do cats purr?"`)
                 and returns the agent's reply as a JSON string in the response.

Setup:
    pip install fastapi uvicorn openai
    export OPENAI_API_KEY=sk-...

Run:
    python main.py
    Open http://127.0.0.1:8000
"""

import os
import re # For prompt injection guardrails.
import json

import gradio as gr

# Guardrails-ai used for I/O guardrails
from guardrails import Guard
from guardrails_ai.toxic_language import ToxicLanguage

# DotEnv used for loading environment variables from .env file
import dotenv

dotenv.load_dotenv()

# Only loads the trace if the user wants to use ARIZE AX.
if os.getenv("USE_ARIZE"):
    from instrumentation import tracer_provider

from openai import OpenAI

# Reads OPENROUTER_API_KEY from the environment by default.
client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY")
)

MODEL = os.getenv("MODEL")
MAX_ITERATIONS = 8

# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

# Attr: https://www.kalviumlabs.ai/blog/guardrails-for-llm-applications/
INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?previous\s+instructions", 0.9),
    (r"ignore\s+(all\s+)?above", 0.8),
    (r"you\s+are\s+now\s+(?:(?:a\s+customer).+)?", 0.7),  # role reassignment
    (r"system\s*prompt", 0.6),
    (r"act\s+as\s+(?:a\s+different|another|an? \w+bot)", 0.6),
    (r"pretend\s+you", 0.6),
    (r"jailbreak", 0.95),
    (r"DAN\s+mode", 0.95),
    (r"\[INST\]|\[/INST\]|<<SYS>>", 0.9),  # model-specific tokens
]

# Input guardrails - Length, Profanity, Prompt Injection

def input_guardrails(text: str) -> str:
    text = text.strip().lower()

    # BLOCKS ANYTHING LONGER THAN 200 CHARACTERS
    if len(text) > 200:
        raise ValueError(f"Please try again with a shorter question: Questions with more than 200 characters i.e. ({len(text)} are not allowed)")

    # PROMPT INJECTION DETECTION
    for pattern, score in INJECTION_PATTERNS:
        if re.search(pattern, text):
            raise ValueError(f"Don't try to Prompt Inject this kitty, mate. I wasn't born yesterday. (score={score}): {text}")
    
    # PROFANITY CHECK
    # Attr: https://github.com/dsojevic/profanity-list/blob/main/en.json with some feline-related omissions
    with open("assets/profanity/profanities.json", "r") as file:
        profanities = json.load(file) 
        for profanity in profanities:
            profanity_match_and_id = profanity["match"].replace("*", "").split('|') + [profanity["id"]]
            if any(word.lower() in text.lower().split() for word in profanity_match_and_id):
                raise ValueError(f"Keep the language clean please. Good felines don't use profanity.")

    return text

# Output Guardrails - Length and Toxicity
    
def output_guardrails(text: str) -> str:
    text = text.strip().lower()

    # BLOCKS ANYTHING LONGER THAN 500 CHARACTERS
    if len(text) > 500:
        raise ValueError(f"Output rejected: Responses with more than 500 characters ({len(text)} are not allowed)")

    # TOXIC LANGUAGE CHECK USING GUARDRAILS-AI
    guard = Guard().use(
        ToxicLanguage(
            threshold=0.2,
            validation_method="full",
            on_fail="exception"
        )
    )

    try:
        guard.validate(text)
        return text
    except Exception as e:
        raise ValueError(f"Output rejected due to toxic language check failure")
 
    return text

# AI Loop (not currently a full loop)

def run_agent(question: str) -> str:
    """LLM Workflow: send the question to the model and return its reply.
    Currently there are no guardrails at this level, they are implemented in
    the calling function.

    Currently there are no external tools, so this is not a "proper" AI agent as such.
    The workflow is implemented as a single pass agentic loop - this allows for the
    easy addition of tool calling or "re-ask" guardrails in future releases.
    """
    messages = [
        {"role": "system", "content": """
         You are a chatbot aimed at cats who speak English and people interested in cats.
         You respond to questions from and about cats, cat behaviour,
         the location of catnip and mice, grooming and other cat-related topics.
         Everything not explicitly from a cat, or alternatively cat related
         is out of bounds and you must refuse to answer questions about it.
         Keep the response less than 500 characters long.
         """},
        {"role": "user", "content": question},
    ]

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(model=MODEL, messages=messages)
        message = response.choices[0].message
        messages.append(message)

        # No tool calls requested — the agent has its final answer.
        if not message.tool_calls:
            return message.content or ""

        # To Add Tool Calls here at a future date.

    return "Agent stopped: reached the maximum number of iterations."


def chat(question, include_guardrails=True) -> str:
    try:
        question = input_guardrails(question) if include_guardrails else question
        answer = run_agent(question)
        answer = output_guardrails(answer) if include_guardrails else answer
        return answer
    except Exception as e:
        return str(e)

# Gradio UI

cat_gpt_interface = gr.Interface(
    fn=chat,
    inputs=gr.Textbox(label="Ask a question about cats", lines=2, placeholder="e.g. 'Why do cats purr?'"),
    outputs=gr.Textbox(label="CatGPT's answer"),
    title="CatGPT",
    description="Ask CatGPT anything about cats! CatGPT is a chatbot that only answers questions related to cats and cat behavior."
)

if __name__ == "__main__":
    # Run the Gradio interface
    cat_gpt_interface.launch(server_name="127.0.0.1", server_port=8000, share=False)
