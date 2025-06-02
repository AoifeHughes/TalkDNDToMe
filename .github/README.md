# GitHub Actions Workflows

This directory contains GitHub Actions workflows for continuous integration and testing.

## Workflows

### 1. Run Tests (`test.yml`)
- **Trigger**: Automatically on push to `main` and on pull requests
- **Purpose**: Run all non-LLM tests to ensure code quality
- **Python version**: 3.12
- **Coverage**: Generates test coverage reports
- **Cost**: Free (no LLM calls)

### 2. Run LLM Tests (`test-llm.yml`)
- **Trigger**: Manual dispatch only
- **Purpose**: Run tests that require LLM interactions
- **Requirements**: Tests expect a local LLM server at localhost:11434
- **Options**: Can filter to specific test files
- **Note**: These tests are designed to run with a local llama.cpp server

## Local LLM Setup

The project is configured to use a local LLM server (llama.cpp) by default:
- Default endpoint: `http://localhost:11434/v1`
- No API keys required
- Tests assume the LLM server is running locally

## Running Tests Locally

```bash
# Run only non-LLM tests (fast, no API costs)
pytest -m "not llm"

# Run only LLM tests
pytest -m "llm"

# Run all tests
pytest
```

## Test Markers

- `llm`: Tests requiring LLM API calls
- `unit`: Pure unit tests
- `integration`: Integration tests
- `slow`: Long-running tests
- `caching`: ChromaDB caching tests
- `rag`: RAG and context retrieval tests