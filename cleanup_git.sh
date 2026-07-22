#!/bin/bash

# ====================================
# Git Cleanup Script
# Removes files that should be in .gitignore from Git tracking
# ====================================

echo "========================================="
echo "Git Repository Cleanup Script"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo -e "${RED}Error: Not a git repository!${NC}"
    echo "Please run this script from the root of your git repository."
    exit 1
fi

echo -e "${YELLOW}WARNING: This will remove files from Git tracking (but keep them locally)${NC}"
echo ""
echo "Files to be removed from Git:"
echo "  - .env files"
echo "  - __pycache__/ directories"
echo "  - .venv/ directories"
echo "  - *.pyc files"
echo "  - .DS_Store files"
echo "  - node_modules/ (if exists)"
echo "  - *.log files"
echo ""
read -p "Do you want to continue? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1: Removing files from Git index (keeping local copies)..."
echo "----------------------------------------------------------------"

# Remove .env files
echo "Removing .env files..."
git rm --cached -r .env* 2>/dev/null || true
git rm --cached .env 2>/dev/null || true

# Remove Python cache
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec git rm --cached -r {} \; 2>/dev/null || true
find . -type f -name "*.pyc" -exec git rm --cached {} \; 2>/dev/null || true
find . -type f -name "*.pyo" -exec git rm --cached {} \; 2>/dev/null || true

# Remove virtual environments
echo "Removing virtual environment directories..."
git rm --cached -r .venv/ 2>/dev/null || true
git rm --cached -r venv/ 2>/dev/null || true
git rm --cached -r ENV/ 2>/dev/null || true
git rm --cached -r env/ 2>/dev/null || true
git rm --cached -r backend/.venv/ 2>/dev/null || true
git rm --cached -r backend/venv/ 2>/dev/null || true

# Remove OS files
echo "Removing OS-specific files..."
find . -name ".DS_Store" -exec git rm --cached {} \; 2>/dev/null || true
find . -name "Thumbs.db" -exec git rm --cached {} \; 2>/dev/null || true

# Remove node_modules
echo "Removing node_modules..."
git rm --cached -r node_modules/ 2>/dev/null || true
git rm --cached -r frontend/node_modules/ 2>/dev/null || true

# Remove logs
echo "Removing log files..."
find . -name "*.log" -exec git rm --cached {} \; 2>/dev/null || true
git rm --cached -r logs/ 2>/dev/null || true

# Remove database files
echo "Removing database files..."
find . -name "*.db" -exec git rm --cached {} \; 2>/dev/null || true
find . -name "*.sqlite" -exec git rm --cached {} \; 2>/dev/null || true
find . -name "*.sqlite3" -exec git rm --cached {} \; 2>/dev/null || true
git rm --cached dump.rdb 2>/dev/null || true

# Remove IDE files
echo "Removing IDE configuration files..."
git rm --cached -r .vscode/ 2>/dev/null || true
git rm --cached -r .idea/ 2>/dev/null || true
git rm --cached -r backend/.vscode/ 2>/dev/null || true
git rm --cached -r backend/.idea/ 2>/dev/null || true

# Remove build artifacts
echo "Removing build artifacts..."
git rm --cached -r dist/ 2>/dev/null || true
git rm --cached -r build/ 2>/dev/null || true
git rm --cached -r *.egg-info/ 2>/dev/null || true
git rm --cached -r backend/dist/ 2>/dev/null || true
git rm --cached -r backend/build/ 2>/dev/null || true

# Remove coverage reports
echo "Removing coverage reports..."
git rm --cached -r htmlcov/ 2>/dev/null || true
git rm --cached -r .coverage 2>/dev/null || true
git rm --cached -r .pytest_cache/ 2>/dev/null || true

echo ""
echo -e "${GREEN}Step 1 Complete!${NC}"
echo ""

echo "Step 2: Checking Git status..."
echo "----------------------------------------------------------------"
git status

echo ""
echo "Step 3: What to do next..."
echo "----------------------------------------------------------------"
echo ""
echo "The files have been removed from Git tracking but are still on your disk."
echo ""
echo "To complete the cleanup, you need to:"
echo ""
echo "1. Review the changes:"
echo "   git status"
echo ""
echo "2. Commit the changes:"
echo "   git add .gitignore"
echo "   git commit -m 'Add .gitignore and remove tracked files that should be ignored'"
echo ""
echo "3. Push to remote:"
echo "   git push origin main"
echo "   (or replace 'main' with your branch name)"
echo ""
echo -e "${YELLOW}IMPORTANT NOTES:${NC}"
echo "- Files are still on your local disk (not deleted)"
echo "- Make sure you have a .env.example file for others to reference"
echo "- Team members should run: git pull && cp .env.example .env"
echo "- Consider using git-filter-repo if you need to remove files from history"
echo ""

read -p "Do you want to create a commit now? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Creating commit..."
    git add .gitignore
    git commit -m "Add .gitignore and remove tracked files that should be ignored

- Added comprehensive .gitignore
- Removed .env files from tracking
- Removed Python cache and virtual environments
- Removed IDE configuration files
- Removed build artifacts and logs
- Removed OS-specific files"
    
    echo ""
    echo -e "${GREEN}Commit created successfully!${NC}"
    echo ""
    echo "Next step: Push to remote with:"
    echo "  git push origin main"
    echo ""
else
    echo ""
    echo "Skipped commit creation."
    echo "You can commit manually when ready."
    echo ""
fi

echo "========================================="
echo "Cleanup Complete!"
echo "========================================="
