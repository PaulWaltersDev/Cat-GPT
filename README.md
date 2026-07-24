# CatGPT

A single-file agentic chatbot that answers questions exclusively about cats. Built with a Gradio web UI, it routes requests through input/output guardrails before hitting the LLM, and ships with Arize AX OpenTelemetry tracing out of the box.

## What it does

- Serves a Gradio web interface at `http://127.0.0.1:8000`
- Accepts natural-language questions about cats and cat behaviour
- Refuses any off-topic questions (enforced by the system prompt)
- Runs an agentic loop (max 8 iterations) powered by **DeepSeek V4 Flash** via [OpenRouter](https://openrouter.ai/)
- Applies input and output guardrails on every request (see below)
- Emits OpenTelemetry traces to [Arize AX](https://arize.com/) for monitoring

## Guardrails

### Input
| Check | Limit |
|-------|-------|
| Length | Max 200 characters |
| Prompt injection | Regex patterns detect and block common injection attempts (e.g. "ignore previous instructions", "jailbreak", "DAN mode") |

### Output
| Check | Limit |
|-------|-------|
| Length | Max 500 characters |
| Toxic language | Guardrails AI `ToxicLanguage` validator (sentence-level, threshold 0.5) |

Any guardrail failure returns an error message to the user instead of the model's response.

## Requirements

- Python 3.9+
- An [OpenRouter](https://openrouter.ai/) API key
- (Optional) An [Arize AX](https://arize.com/) account for tracing

## Installation

```bash
pip install fastapi uvicorn openai gradio guardrails-ai guardrails-hub \
            arize-otel openinference-instrumentation-openai python-dotenv
```

Install the required Guardrails Hub validators:

```bash
guardrails hub install hub://guardrails/toxic_language
guardrails hub install hub://guardrails/politeness_check
```

## Configuration

Create a `.env` file in the project root (or export the variables in your shell):

```env
# Required
OPENROUTER_API_KEY=sk-or-...

# Required for Arize tracing
ARIZE_SPACE_ID=your-space-id
ARIZE_API_KEY=your-api-key

# Optional — defaults to "cat_gpt"
ARIZE_PROJECT_NAME=cat_gpt
```

## Running

```bash
python main.py
```

The Gradio interface will be available at `http://127.0.0.1:8000`.

## Project structure

```
cat_gpt/
├── main.py              # Application entry point — agent loop, guardrails, Gradio UI
├── instrumentation.py   # Arize AX / OpenTelemetry setup (imported before openai)
└── .env                 # Environment variables (not committed)
```

## Architecture notes

- `instrumentation.py` **must** be imported before the `openai` package to enable full tracing; `main.py` handles this at the top of the file.
- The agentic loop in `run_agent()` supports future tool-call expansion — tool results can be appended to the message list and the loop will continue up to `MAX_ITERATIONS = 8`.
- Evaluation hooks (`evaluate_response`) are stubbed and ready to be wired up with [DeepEval](https://docs.confident-ai.com/) or a similar framework.
