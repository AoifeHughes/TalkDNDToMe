#!/bin/bash

# Script to run tests for TalkDNDToMe project

echo "🎲 TalkDNDToMe Test Runner"
echo "========================="

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest is not installed. Please run: pip install pytest pytest-cov"
    exit 1
fi

# Default to running non-LLM tests
TEST_TYPE="non-llm"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            TEST_TYPE="all"
            shift
            ;;
        --llm)
            TEST_TYPE="llm"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  --all       Run all tests (including LLM tests)"
            echo "  --llm       Run only LLM tests"
            echo "  --coverage  Generate coverage report"
            echo "  --help, -h  Show this help message"
            echo ""
            echo "By default, runs only non-LLM tests (fast, no API costs)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set pytest command based on test type
case $TEST_TYPE in
    "all")
        echo "Running all tests..."
        PYTEST_CMD="pytest -v"
        ;;
    "llm")
        echo "Running LLM tests only..."
        echo "⚠️  Note: This requires a local LLM server running at localhost:11434"
        PYTEST_CMD="pytest -v -m llm"
        ;;
    "non-llm")
        echo "Running non-LLM tests only (no API costs)..."
        PYTEST_CMD="pytest -v -m 'not llm'"
        ;;
esac

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=talk_dnd_to_me --cov-report=term-missing --cov-report=html"
fi

# Run the tests
echo ""
echo "Command: $PYTEST_CMD"
echo ""

$PYTEST_CMD

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    if [ "$COVERAGE" = true ]; then
        echo "📊 Coverage report generated in htmlcov/index.html"
    fi
else
    echo ""
    echo "❌ Some tests failed"
    exit 1
fi