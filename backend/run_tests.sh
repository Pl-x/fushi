#!/bin/bash

# ====================================
# Test Runner Script for Payment Gateway
# ====================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Payment Gateway Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Always target this project's interpreter. Activating a uv environment does
# not guarantee that a bare `pip` command belongs to it.
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -x "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Create one with: uv venv .venv"
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo -e "${RED}Error: uv is required to install dependencies into this environment${NC}"
    exit 1
fi

# Install test dependencies
echo -e "${BLUE}Installing test dependencies...${NC}"
UV_LINK_MODE=copy uv pip install --python "$PYTHON" -q -r requirements.txt -r tests/test_requirements.txt

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

case "$TEST_TYPE" in
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        "$PYTHON" -m pytest tests/ $VERBOSE
        ;;
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        "$PYTHON" -m pytest tests/ -m unit $VERBOSE
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        "$PYTHON" -m pytest tests/test_integration.py $VERBOSE
        ;;
    auth)
        echo -e "${GREEN}Running authentication tests...${NC}"
        "$PYTHON" -m pytest tests/test_auth.py $VERBOSE
        ;;
    payment)
        echo -e "${GREEN}Running payment tests...${NC}"
        "$PYTHON" -m pytest tests/test_c2b.py $VERBOSE
        ;;
    transfer)
        echo -e "${GREEN}Running transfer/refund tests...${NC}"
        "$PYTHON" -m pytest tests/test_b2c.py $VERBOSE
        ;;
    model)
        echo -e "${GREEN}Running model tests...${NC}"
        "$PYTHON" -m pytest tests/test_models.py $VERBOSE
        ;;
    health)
        echo -e "${GREEN}Running health check tests...${NC}"
        "$PYTHON" -m pytest tests/test_health.py $VERBOSE
        ;;
    smoke)
        echo -e "${GREEN}Running smoke tests...${NC}"
        "$PYTHON" -m pytest tests/ -m smoke $VERBOSE
        ;;
    coverage)
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        "$PYTHON" -m pytest tests/ --cov=src/app --cov-report=html --cov-report=term
        echo ""
        echo -e "${GREEN}Coverage report generated at: htmlcov/index.html${NC}"
        ;;
    quick)
        echo -e "${GREEN}Running quick tests (no coverage)...${NC}"
        "$PYTHON" -m pytest tests/ --no-cov -x
        ;;
    failed)
        echo -e "${GREEN}Re-running failed tests...${NC}"
        "$PYTHON" -m pytest tests/ --lf $VERBOSE
        ;;
    watch)
        echo -e "${GREEN}Running tests in watch mode...${NC}"
        echo -e "${YELLOW}(Tests will re-run on file changes)${NC}"
        "$PYTHON" -m pytest_watch tests/ -- $VERBOSE
        ;;
    parallel)
        echo -e "${GREEN}Running tests in parallel...${NC}"
        "$PYTHON" -m pytest tests/ -n auto $VERBOSE
        ;;
    help|--help|-h)
        echo "Usage: ./run_tests.sh [test_type] [verbose_flag]"
        echo ""
        echo "Test Types:"
        echo "  all         - Run all tests (default)"
        echo "  unit        - Run only unit tests"
        echo "  integration - Run integration tests"
        echo "  auth        - Run authentication tests"
        echo "  payment     - Run payment (C2B) tests"
        echo "  transfer    - Run transfer/refund (B2C) tests"
        echo "  model       - Run database model tests"
        echo "  health      - Run health check tests"
        echo "  smoke       - Run smoke tests"
        echo "  coverage    - Run tests with coverage report"
        echo "  quick       - Run tests without coverage (fast)"
        echo "  failed      - Re-run only failed tests"
        echo "  parallel    - Run tests in parallel"
        echo "  watch       - Run tests in watch mode"
        echo ""
        echo "Verbose Flags:"
        echo "  -v          - Verbose output"
        echo "  -vv         - Very verbose output"
        echo "  -s          - Show print statements"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh                    # Run all tests"
        echo "  ./run_tests.sh unit -v            # Run unit tests verbosely"
        echo "  ./run_tests.sh coverage           # Generate coverage report"
        echo "  ./run_tests.sh quick              # Quick test run"
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Use './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Some tests failed! ✗${NC}"
    echo -e "${RED}========================================${NC}"
fi

exit $EXIT_CODE
