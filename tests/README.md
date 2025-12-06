# Tests

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_matching.py

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## Test Files

- `test_matching.py` - Matching algorithm tests
- `test_embedding.py` - Embedding generation tests
- `test_supabase_table.py` - Database operation tests
- `test_llm_simple.py` - LLM integration tests
- `test_cartesia.py` - TTS tests
- `test_tts.py` - Text-to-speech tests

## Test Data

Tests use mock data and don't require live API keys for basic functionality.

