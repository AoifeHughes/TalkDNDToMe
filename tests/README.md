# TalkDNDToMe Test Suite

This directory contains comprehensive tests for the TalkDNDToMe enhanced D&D DM system.

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_character_info.py      # Character information retrieval tests
├── test_dice_rolling.py        # Dice rolling functionality tests  
├── test_function_calling.py    # Function calling and tool schema tests
├── test_rag_filtering.py       # RAG filtering and spoiler prevention
├── test_caching.py            # ChromaDB caching performance tests
└── test_session_management.py # Session management tests
```

## Running Tests

### Quick Start
```bash
# Install test dependencies
pip install pytest pytest-mock pytest-asyncio

# Run all tests
pytest

# Run without LLM-dependent tests
pytest -m "not llm"
```

### By Category
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only  
pytest -m llm           # Tests requiring LLM (needs local LLM running)
pytest -m caching       # Caching-related tests
pytest -m rag           # RAG and context retrieval tests
```

### Specific Test Files
```bash
pytest tests/test_character_info.py       # Character tests
pytest tests/test_dice_rolling.py         # Dice rolling tests
pytest tests/test_function_calling.py     # Function calling tests
```

### Using the Test Runner
```bash
python run_tests.py --help              # Show options
python run_tests.py --category unit     # Run unit tests
python run_tests.py --file test_character_info.py  # Run specific file
python run_tests.py --no-llm           # Skip LLM tests
python run_tests.py --verbose          # Verbose output
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests (require full system)
- `@pytest.mark.llm` - Tests requiring a running LLM at localhost:11434
- `@pytest.mark.caching` - ChromaDB caching functionality
- `@pytest.mark.rag` - RAG and context retrieval functionality
- `@pytest.mark.slow` - Tests that take significant time

## Test Categories

### Character Information Tests (`test_character_info.py`)
- ✅ Verifies "Rose" character name appears in responses
- ✅ Tests character details (elf, bard, stats) are included
- ✅ Validates ability score numbers are present
- **Requires**: Local LLM running

### Dice Rolling Tests (`test_dice_rolling.py`)  
- ✅ Tests dice notation appears (1d20, 1d8+3, etc.)
- ✅ Validates reasonable roll results (1-20 for d20)
- ✅ Tests various die types (d4, d6, d8, d10, d12, d20, d100)
- ✅ Tests advantage/disadvantage mechanics
- **Requires**: Local LLM running

### Function Calling Tests (`test_function_calling.py`)
- ✅ Validates tool schemas have required fields
- ✅ Tests required tools exist (roll_dice, update_character_hp, etc.)
- ✅ Tests function implementations work correctly
- ✅ Mock function call processing
- **Requires**: None (unit tests)

### RAG Filtering Tests (`test_rag_filtering.py`)
- ✅ Tests campaign progression filtering blocks future content
- ✅ Validates current act content gets priority boost
- ✅ Tests spoiler content gets penalized
- ✅ Tests enhanced query intent analysis
- **Requires**: ChromaDB initialized

### Caching Tests (`test_caching.py`)
- ✅ Tests cache manager functionality
- ✅ Validates performance improvements from caching
- ✅ Tests cache invalidation on file changes
- ✅ Tests content loader cache integration
- **Requires**: ChromaDB initialized

### Session Management Tests (`test_session_management.py`)
- ✅ Tests session creation and ID generation
- ✅ Validates session ID format
- ✅ Tests new session behavior (no previous sessions)
- **Requires**: ChromaDB initialized

## Fixtures

The `conftest.py` file provides shared fixtures:

- `dm_config` - Default DM configuration
- `chroma_client` - Initialized ChromaDB client
- `embedding_manager` - Embedding manager instance
- `cache_manager` - Cache manager instance
- `context_retriever` - Context retrieval system
- `dm_engine` - Full DM engine (for LLM tests)
- `sample_character_data` - Rose character data for testing

## Prerequisites

### For All Tests
- ChromaDB collections initialized
- Curse-of-Strahd-Reloaded content directory present
- player_character/player.json with Rose character data

### For LLM Tests
- Local LLM running at `http://localhost:11434/v1` (e.g., LM Studio, Ollama)
- Compatible with OpenAI API format
- Sufficient context window for D&D scenarios
- **Note**: Tests will automatically skip if no LLM is detected
- **Note**: LLM tests may take 30-60 seconds each depending on model speed

## Example Test Run

```bash
$ pytest tests/test_character_info.py -v

================================= test session starts =================================
collected 4 items

tests/test_character_info.py::TestCharacterInfo::test_character_name_retrieval PASSED
tests/test_character_info.py::TestCharacterInfo::test_character_details_retrieval PASSED  
tests/test_character_info.py::TestCharacterInfo::test_character_stats_include_numbers PASSED
tests/test_character_info.py::TestCharacterInfo::test_various_character_queries PASSED

================================= 4 passed in 12.34s =================================
```

## Troubleshooting

### Common Issues

1. **LLM Connection Errors**: Ensure local LLM is running at localhost:11434
2. **ChromaDB Errors**: Run `python main.py` once to initialize collections
3. **Character Not Found**: Ensure `player_character/player.json` exists with Rose data
4. **Import Errors**: Install requirements: `pip install -r requirements.txt`

### Debug Mode
```bash
pytest -v -s --tb=long  # Verbose output with full tracebacks
```