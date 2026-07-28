# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CatGPT is a single-file agentic chatbot that answers questions exclusively about cats. It demonstrates guardrail implementation patterns with a three-layer architecture: Input Guardrails → Agent Loop → Output Guardrails.

## Architecture

### Request Flow
```
User Question (Gradio UI)
    ↓
chat() function
    ↓
input_guardrails() — Length (200 chars), Prompt Injection, Profanity
    ↓
run_agent() — LLM agentic loop (max 8 iterations, currently single-pass)
    ↓
output_guardrails() — Length (500 chars), Toxicity (Guardrails-AI)
    ↓
Response to User
```

### Key Design Decisions

1. **Guardrails are applied in `chat()`, not inside `run_agent()`**
   - This allows `run_agent()` to be tested without guardrails in evaluations
   - The `include_guardrails` parameter controls this behavior

2. **Agentic loop is designed for future tool-call expansion**
   - `run_agent()` iterates up to `MAX_ITERATIONS = 8`
   - Currently exits on first response (no tool calls implemented)
   - Tool results can be appended to messages list for future multi-turn loops

3. **Arize tracing requires conditional import ordering**
   - `instrumentation.py` must be imported before `openai` package
   - Only imported when `USE_ARIZE` environment variable is set
   - This ensures OpenTelemetry hooks are installed before OpenAI SDK initializes

4. **Dual LLM configuration**
   - Main app uses: `API_KEY`, `BASE_URL`, `MODEL`
   - DeepEval uses: `DEEPEVAL_API_KEY`, `DEEPEVAL_OPENAI_URL`, `DEEPEVAL_MODEL`
   - These are independent and can use different providers

### Profanity Guardrail Implementation

The profanity check in `input_guardrails()` matches word boundaries, not substrings:
- Loads from `assets/profanity/profanities.json`
- Extracts match patterns, splits on `|`, removes wildcards
- Uses `word.lower() in text.lower().split()` for word-boundary matching
- Also matches against profanity IDs for broader coverage

## Development Commands

### Running the Application
```bash
python main.py
```
Opens Gradio UI at http://127.0.0.1:8000

### Running Evaluations
```bash
# Run all DeepEval tests
deepeval test run -v test_cat_gpt.py

# Run specific test
pytest test_cat_gpt.py::test_agent_only_about_cats -v

# Run with pytest directly (standard pytest functionality)
pytest test_cat_gpt.py -v
```

### Setup Commands
```bash
# Install dependencies
pip install openai gradio guardrails-ai deepeval \
            arize-otel openinference-instrumentation-openai python-dotenv

# Install Guardrails AI validator
guardrails hub install hub://guardrails/toxic_language
```

## Testing Architecture

DeepEval tests are organized into three evaluation types:

1. **Only About Cats** (`test_agent_only_about_cats`)
   - GEval (LLM-as-judge) metric
   - Verifies responses are cat-related or polite refusals
   - Parameterized across 4 golden test cases

2. **Toxicity with Guardrails** (`test_agent_withguardrails_not_toxic`)
   - Expects toxic prompts to be blocked by output guardrails
   - Should return "Output rejected due to toxic language check failure"

3. **Toxicity without Guardrails** (`test_agent_withoutguardrails_not_toxic`)
   - Tests that base model produces non-toxic responses naturally
   - Uses DeepEval's ToxicityMetric (threshold 0.20)

The `@observe()` decorator and `update_current_trace()` enable DeepEval tracing for all test runs.

## Configuration

Environment variables must be set in `.env`:

**Required for main app:**
- `API_KEY` — OpenAI-compatible API key
- `BASE_URL` — API base URL (e.g., `https://openrouter.ai/api/v1`)
- `MODEL` — Model name (e.g., `deepseek/deepseek-v4-flash`)

**Required for DeepEval tests:**
- `DEEPEVAL_MODEL` — Model for evaluations
- `DEEPEVAL_API_KEY` — API key for evaluator
- `DEEPEVAL_OPENAI_URL` — Base URL for evaluator

**Optional Arize tracing:**
- `USE_ARIZE=true` — Enables tracing
- `ARIZE_SPACE_ID` — Your Arize space ID
- `ARIZE_API_KEY` — Your Arize API key
- `ARIZE_PROJECT_NAME` — Defaults to "cat_gpt"

## File Structure

- `main.py` — Application entry point (guardrails, agent loop, Gradio UI)
- `instrumentation.py` — Arize OpenTelemetry setup (import before openai)
- `test_cat_gpt.py` — DeepEval evaluation suite with pytest
- `custom/open_ai.py` — DeepEval model config for OpenAI-compatible providers
- `custom/openrouter.py` — Legacy OpenRouter-specific DeepEval config
- `assets/profanity/profanities.json` — Profanity word list with match patterns

## Making Changes

### Adding New Guardrails
Add to `input_guardrails()` or `output_guardrails()` functions in `main.py`. Keep them in the `chat()` wrapper, not inside `run_agent()`, so they can be toggled for testing.

### Adding Tool Calls
Implement inside the `run_agent()` loop after line 147:
```python
if message.tool_calls:
    # Execute tool calls here
    # Append tool results to messages list
    # Loop continues for next iteration
```

### Switching DeepEval Provider
Edit the import in `test_cat_gpt.py` line 11:
- For OpenAI-compatible: `from custom.open_ai import get_model`
- For OpenRouter: `from custom.openrouter import get_model`

Then configure corresponding environment variables in `.env`.

### Adding New Evaluations
Add golden test cases and use `@pytest.mark.parametrize` with DeepEval metrics. See existing test functions for patterns.
