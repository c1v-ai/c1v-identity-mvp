# Testing Guide for C1V Identity MVP

## Overview
This document describes the testing strategy, test cases, and quality gates for the C1V Identity MVP system.

## Test Structure

### Unit Tests
- **Generator Tests**: Test individual components of the synthetic data generator
- **Feature Tests**: Test feature extraction and similarity calculations
- **Model Tests**: Test model training and inference logic
- **API Tests**: Test REST API endpoints and response formats

### Integration Tests
- **End-to-End Generation**: Test complete data generation pipeline
- **Training Pipeline**: Test model training with generated data
- **API Integration**: Test API with trained models

### Property-Based Tests
- **Data Quality**: Ensure generated data meets quality constraints
- **Reproducibility**: Verify consistent output with same seeds
- **Edge Cases**: Test boundary conditions and error handling

## Test Files

### tests/gen/test_synth_happy_path.py
Tests the happy path for synthetic data generation:
- Generator initialization with different parameters
- Generation of small datasets (leads, sales, financial)
- Pair building and validation
- CLI integration and argument parsing
- PII hashing functionality
- Noise injection and locale-specific generation

### tests/gen/test_pairs_quality.py
Tests the quality and constraints of generated training pairs:
- Class balance limits (1:3 to 1:5 positive:negative ratio)
- Label validity (all y values in {0, 1})
- No NaN values in key fields
- Positive pair quality (valid source combinations)
- Negative pair quality (hard negatives)
- No data leakage in positive pairs
- Train/validation/test split ratios (70/15/15)

## Test Execution

### Running All Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/gen/test_synth_happy_path.py

# Run specific test class
python -m pytest tests/gen/test_synth_happy_path.py::TestSyntheticDataGenerator
```

### Running Tests in CI
```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests with verbose output
python -m pytest -v --tb=short

# Exit on first failure
python -m pytest -x
```

## Quality Gates

### Data Generation Gates
- **Schema Validation**: All required columns present in generated datasets
- **Data Types**: Correct data types for all fields
- **Uniqueness**: Unique IDs across all datasets
- **No Missing Values**: No NaN values in key fields (email, first_name, last_name)
- **Volume Requirements**: Minimum record counts met (1k per entity for dev mode)

### Training Pairs Gates
- **Minimum Positives**: At least 100 positive pairs in training set
- **Minimum Negatives**: At least 500 hard negative pairs in training set
- **Class Balance**: Positive:negative ratio between 1:3 and 1:5
- **Split Ratios**: Train:validation:test split approximately 70:15:15
- **No Leakage**: Positive pairs have non-empty key fields

### Validation Checks
The system performs automatic validation and reports:
- **Column Presence**: All required columns exist
- **Data Quality**: NaN counts in key fields
- **Pairs Quality**: Training set size and class balance
- **Overall Status**: PASS/FAIL with detailed error messages

## Test Data

### Synthetic Data Generation
Tests use the same generator as production with small volumes:
- **Leads**: 100-200 records for testing
- **Sales**: 50-100 records for testing
- **Financial**: 50-100 records for testing
- **Duplicates**: 10% duplicate rate
- **Overlap**: 40% cross-source overlap

### Test Isolation
- Each test creates temporary directories
- Tests clean up after themselves
- No shared state between tests
- Deterministic output with fixed seeds

## API Contract (enforced by tests)
- `MatchResponse`: `match: bool`, `confidence: float (0..1)`, `reason: string|null`
- Tests must verify: HTTP 200, types of fields, and confidence within `[0,1]`

## Performance Testing

### Data Generation Performance
- **Small Datasets**: < 5 seconds for 1k/1k/1k records
- **Medium Datasets**: < 30 seconds for 10k/1k/1k records
- **Large Datasets**: < 5 minutes for 30k/3k/2.1k records

### Memory Usage
- **Peak Memory**: < 2GB for largest supported dataset
- **Efficient Processing**: Vectorized operations where possible
- **Chunked Writes**: Large datasets written in chunks

## Error Handling

### Expected Errors
- **Invalid Arguments**: Clear error messages for bad CLI parameters
- **Missing Files**: Graceful handling of missing schema files
- **Validation Failures**: Detailed reporting of data quality issues
- **System Errors**: Proper error logging and exit codes

### Error Recovery
- **Non-Zero Exit**: CLI exits with status 1 on validation failure
- **Detailed Logging**: Comprehensive error messages and stack traces
- **Partial Results**: Intermediate files preserved on failure
- **Summary Reports**: Validation status included in summary

## Continuous Integration

### Pre-commit Hooks
- **Code Formatting**: Black and isort for consistent style
- **Linting**: Flake8 for code quality
- **Type Checking**: MyPy for type safety
- **Test Execution**: Run unit tests before commit

### CI Pipeline
- **Test Execution**: All tests must pass
- **Coverage Requirements**: Minimum 80% code coverage
- **Performance Benchmarks**: Generation time within limits
- **Documentation**: API docs and examples up to date

## Debugging Tests

### Common Issues
- **Import Errors**: Ensure src/ is in Python path
- **Missing Dependencies**: Install all requirements
- **File Permissions**: Check write access to temp directories
- **Random Failures**: Use fixed seeds for deterministic tests

### Debug Commands
```bash
# Run single test with debug output
python -m pytest tests/gen/test_synth_happy_path.py::TestSyntheticDataGenerator::test_generate_leads_small -s -v

# Run with print statements
python -m pytest tests/gen/test_synth_happy_path.py -s

# Run with pdb debugger
python -m pytest tests/gen/test_synth_happy_path.py --pdb
```

## Test Maintenance

### Adding New Tests
1. **Follow Naming**: Use descriptive test method names
2. **Test One Thing**: Each test should verify one specific behavior
3. **Use Fixtures**: Leverage pytest fixtures for common setup
4. **Assert Clearly**: Use specific assertions with helpful error messages

### Updating Tests
- **Keep Tests Current**: Update tests when functionality changes
- **Maintain Coverage**: Ensure new code is covered by tests
- **Review Failures**: Investigate and fix test failures promptly
- **Document Changes**: Update this guide when test strategy changes
