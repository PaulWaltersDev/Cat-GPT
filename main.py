"""
cat_gpt — single-file FastAPI agent service.

Endpoint:
    POST /chat — takes a string request body (a JSON string, e.g. `"why do cats purr?"`)
                 and returns the agent's reply as a JSON string in the response.

Setup:
    pip install fastapi uvicorn openai
    export OPENAI_API_KEY=sk-...

Run:
    python main.py
    # or: uvicorn main:app --reload

Try it:
    curl -X POST http://localhost:8000/chat \
         -H "Content-Type: application/json" \
         -d '"why do cats purr?"'
"""

# IMPORTANT: Import instrumentation BEFORE openai to enable tracing
from instrumentation import tracer_provider

import os
import re # For prompt injection guardrails.

import gradio as gr

from openai import OpenAI

# Guardrails-ai used for I/O guardrails
from guardrails import Guard
from guardrails.hub import PolitenessCheck

# DeepEval for evaluation


#app = FastAPI(title="cat_gpt")

# Reads OPENROUTER_API_KEY from the environment by default.
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

MODEL = "deepseek/deepseek-v4-flash"
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

def input_guardrail(text: str) -> str:
    text = text.strip().lower()

    # BLOCKS ANYTHING LONGER THAN 200 CHARACTERS
    if len(text) > 200:
        raise ValueError(f"Input rejected: Questions with more than 200 characters ({len(text)} are not allowed)")

    # PROMPT INJECTION DETECTION
    for pattern, score in INJECTION_PATTERNS:
        if re.search(pattern, text):
            raise ValueError(f"Input rejected due to prompt injection risk (score={score}): {text}")
    
    return text
    

def output_guardrail(text: str) -> str:
    text = text.strip().lower()

    # BLOCKS ANYTHING LONGER THAN 500 CHARACTERS
    if len(text) > 500:
        raise ValueError(f"Output rejected: Responses with more than 500 characters ({len(text)} are not allowed)")
    

    # # NSFW DETECTION (using Guardrails)
    # guard = Guard().use(
    #     NSFWText,
    #     threshold=0.8,
    #     validation_method="sentence",
    #     on_fail="exception"
    # )

    # try:
    #     guard.validate(text)
    # except Exception as e:
    #     raise ValueError(f"Output rejected due to NSFW content: {text}")

    # POLITENESS CHECK
    guard = Guard().use(
        PolitenessCheck(on_fail="exception")
    )

    try:
        guard.validate(text)
    except Exception as e:
        raise ValueError(f"Output rejected due to politeness check failure: {text}")
 
    return text



#    """Validate/sanitize the incoming request: length limits, prompt-injection
#     screening, PII redaction, topic allow/block lists, etc.
#     Raise or return a refusal string if the input is not allowed."""
#     ...
#
# def output_guardrail(text: str) -> str:
#     """Check the model's response before returning it: toxicity, policy
#     compliance, groundedness, PII leakage, etc.
#     Raise or return a safe fallback string if the output is not allowed."""
#     ...


# ---------------------------------------------------------------------------
# Evals (stubs — to be implemented)
# ---------------------------------------------------------------------------
# def evaluate_response(question: str, answer: str) -> dict:
#     """Score the completed turn (relevance, faithfulness, latency, token usage)
#     and log it for offline evaluation / monitoring datasets."""
#     ...


def run_agent(question: str) -> str:
    """Agentic loop: send the question to the model and return its reply.

    The loop is where tool calls / multi-step reasoning will live later; for
    now it completes in a single turn when the model returns plain text.
    """
    messages = [
        {"role": "system", "content": """
         You a chatbot aimed only at cats who speak English.
         You respond courteously to questions from and about cats, cat behaviour,
         the location of catnip and mice, and other cat-related topics.
        "Everything not cat related is out of bounds and you should refuse to answer questions about it.
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

        # (future) execute requested tool calls and append their results here

    return "Agent stopped: reached the maximum number of iterations."


def chat(question) -> str:
    question = input_guardrail(question)
    answer = run_agent(question)
    answer = output_guardrail(answer)
    # evaluate_response(question, answer)
    return answer

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
