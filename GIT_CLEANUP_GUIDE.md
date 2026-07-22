# Git Cleanup Guide

## Problem

Files that should be ignored (like `.env`, `__pycache__`, `.venv`) were committed to Git before `.gitignore` was created. Even though `.gitignore` now exists, these files are still tracked by Git.

## Solution

Follow these steps to remove them from Git tracking while keeping them locally.

## Quick Solution (Automated)

### Step 1: Run the cleanup script

```bash
cd /mnt/sub0_2/projectX
./cleanup_git.sh
```

The script will:
- Remove `.env` files from Git tracking
- Remove `__pycache__/` and `*.pyc` files
- Remove `.venv/` directories
- Remove IDE files (`.vscode/`, `.idea/`)
- Remove OS files (`.DS_Store`, `Thumbs.db`)
- Remove build artifacts
- Keep all files locally (won't delete them)

### Step 2: Review and commit

```bash
# Check what was removed
git status

# If everything looks good, the script can create the commit for you
# Or manually:
git add .gitignore
git commit -m "Add .gitignore and remove sensitive files from tracking"
```

### Step 3: Push to remote

```bash
git push origin main
# or
git push origin master
# or whatever your branch name is
```

## Manual Solution (Step-by-Step)

If you prefer to do it manually or need more control:

### 1. Remove .env files

```bash
git rm --cached .env
git rm --cached backend/.env
git rm --cached .env.local
git rm --cached .env.*
```

### 2. Remove Python cache

```bash
# Find and remove all __pycache__ directories
find . -type d -name "__pycache__" -exec git rm --cached -r {} \; 2>/dev/null

# Remove .pyc files
find . -type f -name "*.pyc" -exec git rm --cached {} \; 2>/dev/null
```

### 3. Remove virtual environments

```bash
git rm --cached -r .venv/
git rm --cached -r venv/
git rm --cached -r backend/.venv/
```

### 4. Remove IDE files

```bash
git rm --cached -r .vscode/
git rm --cached -r .idea/
```

### 5. Remove OS files

```bash
find . -name ".DS_Store" -exec git rm --cached {} \; 2>/dev/null
find . -name "Thumbs.db" -exec git rm --cached {} \; 2>/dev/null
```

### 6. Remove build artifacts

```bash
git rm --cached -r dist/
git rm --cached -r build/
git rm --cached -r *.egg-info/
```

### 7. Commit the changes

```bash
git add .gitignore
git commit -m "Add .gitignore and remove sensitive files from tracking"
```

### 8. Push to remote

```bash
git push origin main
```

## What `git rm --cached` Does

- `--cached`: Removes file from Git index (stops tracking)
- **Does NOT delete** the file from your local disk
- File will still exist locally for you to use
- Git will ignore it going forward (thanks to `.gitignore`)

## For Team Members

After you push these changes, team members need to:

```bash
# Pull the changes
git pull origin main

# Create their own .env file
cp backend/.env.example backend/.env

# Edit with their credentials
nano backend/.env
```

## Removing Files from Git History (Advanced)

⚠️ **Warning**: This rewrites Git history! Only do this if sensitive data was committed.

### Using git-filter-repo (Recommended)

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove .env files from entire history
git filter-repo --path .env --invert-paths
git filter-repo --path backend/.env --invert-paths

# Force push (rewrites history)
git push origin --force --all
```

### Using BFG Repo-Cleaner (Alternative)

```bash
# Download BFG
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# Remove .env files from history
java -jar bfg-1.14.0.jar --delete-files .env

# Clean up and force push
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

## Common Issues

### Issue 1: "fatal: pathspec did not match any files"

**Cause**: File doesn't exist or isn't tracked by Git

**Solution**: That's okay! It means the file wasn't in Git. Continue with other files.

### Issue 2: Changes not taking effect

**Cause**: `.gitignore` only affects untracked files

**Solution**: You must use `git rm --cached` to untrack already-tracked files.

### Issue 3: Files reappear after pull

**Cause**: They're still in remote repository

**Solution**: Make sure you pushed the commit that removes them.

### Issue 4: Accidentally deleted files locally

**Cause**: Used `git rm` without `--cached`

**Solution**: Restore from Git:
```bash
git checkout HEAD -- filename
```

## Verification

Check that files are no longer tracked:

```bash
# Should not list .env, __pycache__, etc.
git ls-files | grep -E '\.env|__pycache__|\.pyc|\.venv'

# Should return nothing if successful
```

Check `.gitignore` is working:

```bash
# Create a test .env file
echo "TEST=value" > test.env

# Check git status
git status

# test.env should NOT appear in "Untracked files"
# (should be ignored)

# Clean up
rm test.env
```

## Files Typically Removed

✅ Environment files:
- `.env`
- `.env.local`
- `.env.*.local`

✅ Python artifacts:
- `__pycache__/`
- `*.pyc`
- `*.pyo`
- `.venv/`
- `venv/`

✅ IDE settings:
- `.vscode/`
- `.idea/`
- `*.sublime-workspace`

✅ OS files:
- `.DS_Store` (macOS)
- `Thumbs.db` (Windows)

✅ Build artifacts:
- `dist/`
- `build/`
- `*.egg-info/`

✅ Logs:
- `*.log`
- `logs/`

✅ Databases:
- `*.db`
- `*.sqlite3`

## Best Practices Going Forward

1. **Always create `.gitignore` first** before initial commit
2. **Use `.env.example`** as template (without actual secrets)
3. **Review before committing**: `git status` and `git diff`
4. **Use pre-commit hooks** to catch sensitive files
5. **Never commit**:
   - API keys
   - Passwords
   - Private keys
   - Database credentials

## Creating .env.example

Create a template for your `.env` file:

```bash
# Copy current .env
cp backend/.env backend/.env.example

# Edit .env.example and replace real values with placeholders
nano backend/.env.example
```

**Example `.env.example`:**
```env
SECRET_KEY=your-secret-key-here
PAYSTACK_SECRET_KEY=sk_test_your_test_key
POSTGRES_PASSWORD=your-database-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Summary

1. ✅ Created `.gitignore` in projectX root
2. ✅ Created cleanup script (`cleanup_git.sh`)
3. Run the script to remove files from Git tracking
4. Commit and push changes
5. Team members create their own `.env` from `.env.example`

Your repository will be clean and secure! 🛡️

## Need Help?

- **Dry run first**: Review `git status` before committing
- **Backup**: Create a backup before rewriting history
- **Questions**: Check Git documentation or ask for help

---

**Remember**: `git rm --cached` removes from Git but keeps files locally. Your `.env` file will still work! 🎉
