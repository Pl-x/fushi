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

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not detected${NC}"
    echo "Activating .venv..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}Error: Virtual environment not found${NC}"
        echo "Please create one with: python -m venv .venv"
        exit 1
    fi
fi

# Install test dependencies
echo -e "${BLUE}Installing test dependencies...${NC}"
pip install -q -r tests/test_requirements.txt

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

case "$TEST_TYPE" in
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        pytest tests/ $VERBOSE
        ;;
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        pytest tests/ -m unit $VERBOSE
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        pytest tests/test_integration.py $VERBOSE
        ;;
    auth)
        echo -e "${GREEN}Running authentication tests...${NC}"
        pytest tests/test_auth.py $VERBOSE
        ;;
    payment)
        echo -e "${GREEN}Running payment tests...${NC}"
        pytest tests/test_c2b.py $VERBOSE
        ;;
    transfer)
        echo -e "${GREEN}Running transfer/refund tests...${NC}"
        pytest tests/test_b2c.py $VERBOSE
        ;;
    model)
        echo -e "${GREEN}Running model tests...${NC}"
        pytest tests/test_models.py $VERBOSE
        ;;
    health)
        echo -e "${GREEN}Running health check tests...${NC}"
        pytest tests/test_health.py $VERBOSE
        ;;
    smoke)
        echo -e "${GREEN}Running smoke tests...${NC}"
        pytest tests/ -m smoke $VERBOSE
        ;;
    coverage)
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        pytest tests/ --cov=src/app --cov-report=html --cov-report=term
        echo ""
        echo -e "${GREEN}Coverage report generated at: htmlcov/index.html${NC}"
        ;;
    quick)
        echo -e "${GREEN}Running quick tests (no coverage)...${NC}"
        pytest tests/ --no-cov -x
        ;;
    failed)
        echo -e "${GREEN}Re-running failed tests...${NC}"
        pytest tests/ --lf $VERBOSE
        ;;
    watch)
        echo -e "${GREEN}Running tests in watch mode...${NC}"
        echo -e "${YELLOW}(Tests will re-run on file changes)${NC}"
        pytest-watch tests/ -- $VERBOSE
        ;;
    parallel)
        echo -e "${GREEN}Running tests in parallel...${NC}"
        pytest tests/ -n auto $VERBOSE
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
