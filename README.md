# CatGPT

A single-file agentic chatbot that answers questions exclusively about cats. Built with a Gradio web UI, it routes requests through input/output guardrails before hitting the LLM, and ships with Arize AX OpenTelemetry tracing out of the box.

## What it does

- Serves a Gradio web interface at `http://127.0.0.1:8000`
- Accepts natural-language questions about cats and cat behaviour
- Refuses any off-topic questions (enforced by the system prompt)
- Runs an agentic loop (max 8 iterations) powered by an OpenAI-compatible LLM API
- Applies input and output guardrails on every request (see below)
- Emits OpenTelemetry traces to [Arize AX](https://arize.com/) for monitoring (optional)

## Workflow

See the complete workflow diagram with guardrails: [workflow_diagram.svg](workflow_diagram.svg)

## Guardrails

### Input
| Check | Limit |
|-------|-------|
| Length | Max 200 characters |
| Prompt injection | Regex patterns detect and block common injection attempts (e.g. "ignore previous instructions", "jailbreak", "DAN mode") |
| Profanity | Blocks profanity using a curated word list |

### Output
| Check | Limit |
|-------|-------|
| Length | Max 500 characters |
| Toxic language | Guardrails AI `ToxicLanguage` validator (threshold 0.2, validation_method "full") |

Any guardrail failure returns an error message to the user instead of the model's response.

## Evaluations

CatGPT includes automated evaluations implemented with [DeepEval](https://docs.confident-ai.com/) and pytest:

| Evaluation | Type | Description |
|------------|------|-------------|
| **Only About Cats** | GEval (LLM-as-judge) | Verifies that responses contain only cat-related information or polite refusals for off-topic questions |
| **Toxicity (with guardrails)** | ToxicityMetric | Confirms that the output guardrail successfully blocks toxic language (threshold 0.20) |
| **Toxicity (without guardrails)** | ToxicityMetric | Validates that the base model produces non-toxic responses even without guardrail enforcement |

Run evaluations with:
```bash
deepeval test run -v test_cat_gpt.py
```

### DeepEval Configuration

CatGPT's evaluation suite supports any OpenAI-compatible LLM provider through DeepEval's `GPTModel` class. Configure your evaluator by adding these environment variables to your `.env` file:

```env
# DeepEval LLM Configuration (for evaluations)
DEEPEVAL_MODEL=model-name
DEEPEVAL_API_KEY=your-api-key
DEEPEVAL_OPENAI_URL=https://api.example.com/v1

# Example for OpenRouter:
# DEEPEVAL_MODEL=anthropic/claude-sonnet-4.6
# DEEPEVAL_API_KEY=sk-or-...
# DEEPEVAL_OPENAI_URL=https://openrouter.ai/api/v1

# Example for OpenAI:
# DEEPEVAL_MODEL=gpt-4o
# DEEPEVAL_API_KEY=sk-...
# DEEPEVAL_OPENAI_URL=https://api.openai.com/v1

# Example for Azure OpenAI:
# DEEPEVAL_MODEL=gpt-4
# DEEPEVAL_API_KEY=your-azure-key
# DEEPEVAL_OPENAI_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
```

**Note:** The evaluation LLM configuration is independent from the main application's LLM configuration. You can use different providers for the application (`API_KEY`, `BASE_URL`, `MODEL`) and for evaluations (`DEEPEVAL_MODEL`, `DEEPEVAL_API_KEY`, `DEEPEVAL_OPENAI_URL`).

## Requirements

- Python 3.9+
- An API key for an OpenAI-compatible LLM provider (e.g., [OpenRouter](https://openrouter.ai/), OpenAI, Azure OpenAI)
- (Optional) An [Arize AX](https://arize.com/) account for tracing

## Installation

```bash
pip install openai gradio guardrails-ai deepeval \
            arize-otel openinference-instrumentation-openai python-dotenv
```

Install the required Guardrails Hub validator:

```bash
guardrails hub install hub://guardrails/toxic_language
```

## Configuration

Create a `.env` file in the project root (or export the variables in your shell):

```env
# Required - OpenAI-compatible API configuration
API_KEY=your-api-key-here
BASE_URL=https://api.example.com/v1
MODEL=model-name

# Example for OpenRouter:
# API_KEY=sk-or-...
# BASE_URL=https://openrouter.ai/api/v1
# MODEL=deepseek/deepseek-v4-flash

# Example for OpenAI:
# API_KEY=sk-...
# BASE_URL=https://api.openai.com/v1
# MODEL=gpt-4o

# Example for Azure OpenAI:
# API_KEY=your-azure-key
# BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
# MODEL=gpt-4

# Optional — enables Arize tracing (set to any non-empty value)
USE_ARIZE=true

# Required when USE_ARIZE is set
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
├── test_cat_gpt.py      # DeepEval evaluation suite with pytest integration
├── custom/
│   ├── open_ai.py       # DeepEval model configuration for OpenAI-compatible providers
│   └── openrouter.py    # DeepEval model configuration for OpenRouter (legacy)
├── assets/
│   └── profanity/
│       └── profanities.json  # Profanity word list for input filtering
└── .env                 # Environment variables (not committed)
```

## Architecture notes

- `instrumentation.py` is imported conditionally (when `USE_ARIZE` is set) before the `openai` package to enable full tracing.
- The agentic loop in `run_agent()` supports future tool-call expansion — tool results can be appended to the message list and the loop will continue up to `MAX_ITERATIONS = 8`.
- Evaluation hooks are implemented using [DeepEval](https://docs.confident-ai.com/) in `test_cat_gpt.py` with pytest integration for relevance and toxicity metrics.
- CatGPT uses the OpenAI Python SDK with configurable `base_url`, `api_key`, and model selection to support any OpenAI-compatible API provider.
