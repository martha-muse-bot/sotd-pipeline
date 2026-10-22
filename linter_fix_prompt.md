# Reusable Linter Error Fix Prompt

## Purpose
This is a reusable prompt for systematically identifying, tracking, and fixing Python linter errors in the SOTD Pipeline project. Use this prompt anytime you encounter linter issues or want to maintain code quality.

## Current Situation (2025-09-03)
The SOTD Pipeline project has **2,364 linter errors** causing Cursor to timeout after 3 attempts:
- **2,255 E501 errors** (line too long >100 characters) - PRIMARY CAUSE OF TIMEOUT
- **85 F401 errors** (unused imports)
- **24 F841 errors** (unused variables)

## Step 1: Error Discovery and Analysis

### Get Current Error Counts
```bash
# Get total error count
ruff check . | wc -l

# Get error counts by type
ruff check . --select E501 | wc -l  # Line length errors
ruff check . --select F401 | wc -l  # Unused imports
ruff check . --select F841 | wc -l  # Unused variables
ruff check . --select E401 | wc -l  # Multiple imports on same line
ruff check . --select I001 | wc -l  # Import sorting issues
```

### Create/Update Error Tracking
- Create or update `linter_errors_todo.md` with current error counts
- Categorize errors by type and priority
- Set realistic goals based on error volume

## Step 2: Systematic Fix Strategy

### Phase 1: E501 Line Length Errors (Priority 1)
**Goal**: Fix line length errors (usually the most common and timeout-causing)

**Approach**:
1. **Start with most problematic files** - files with many E501 errors
2. **Use automated formatting first**: `ruff format .` and `black .`
3. **Manual fixes for complex cases** - long strings, complex expressions
4. **Break long lines strategically** - preserve readability

**Commands**:
```bash
# Auto-format all files (handles many E501 errors automatically)
ruff format .
black .

# Check remaining E501 errors
ruff check . --select E501 | head -20

# Fix specific file
ruff format path/to/file.py
```

**File Priority Strategy**:
```bash
# Find files with most E501 errors
ruff check . --select E501 --output-format=json | jq -r '.[] | select(.code == "E501") | .filename' | sort | uniq -c | sort -nr | head -10

# Start with files having most errors
# Then move to directories: analysis/ → sotd/ → webui/
```

### Phase 2: F401 Unused Imports (Priority 2)
**Goal**: Remove 85 unused import errors

**Approach**:
1. **Use auto-fix**: `ruff check . --select F401 --fix`
2. **Manual review** for complex cases
3. **Preserve imports** that might be used dynamically

**Commands**:
```bash
# Auto-fix unused imports
ruff check . --select F401 --fix

# Check remaining F401 errors
ruff check . --select F401
```

### Phase 3: F841 Unused Variables (Priority 3)
**Goal**: Fix 24 unused variable errors

**Approach**:
1. **Use auto-fix**: `ruff check . --select F841 --fix`
2. **Manual review** for variables that should be used
3. **Add underscore prefix** for intentionally unused variables

**Commands**:
```bash
# Auto-fix unused variables
ruff check . --select F841 --fix

# Check remaining F841 errors
ruff check . --select F841
```

## Step 3: Progress Tracking

### Update `linter_errors_todo.md` after each phase:
1. **Mark category as COMPLETE** when done
2. **Update resolved count** 
3. **Add notes** about any complex cases
4. **Re-run linter** to verify progress

### Example progress updates:
```markdown
### E501 - Line Too Long (>100 characters)
**Status**: COMPLETE  
**Count**: 2,255 → 0  
**Notes**: Fixed with ruff format + black + manual fixes for complex cases

**Resolved**: 2,255  
**Remaining**: 109
```

### Progress Validation Commands:
```bash
# Check remaining errors after each phase
ruff check . --select E501 | wc -l
ruff check . --select F401 | wc -l
ruff check . --select F841 | wc -l

# Full linter check
ruff check . | wc -l
```

## Step 4: Quality Assurance

### After each phase:
1. **Run linter check**: `ruff check . --select [ERROR_TYPE]`
2. **Run tests**: `make test` to ensure no regressions
3. **Update tracking file** with progress
4. **Commit changes** with descriptive message

### Final validation:
```bash
# Should return 0 errors
ruff check .

# Should pass all tests
make test
```

### Regression Prevention:
```bash
# Run before starting any linter fixes
make test

# Run after each major phase
make test

# Run before committing
make format lint typecheck test
```

## Complex Cases Handling

### Long String Literals
```python
# Instead of:
long_string = "This is a very long string that exceeds 100 characters and needs to be broken up for linting compliance"

# Use:
long_string = (
    "This is a very long string that exceeds 100 characters "
    "and needs to be broken up for linting compliance"
)
```

### Long Function Calls
```python
# Instead of:
result = some_function_with_many_parameters(param1, param2, param3, param4, param5, param6)

# Use:
result = some_function_with_many_parameters(param1, param2, param3, param4, param5, param6)
```

### Long Import Statements
```python
# Instead of:
from very.long.module.path import very_long_function_name, another_long_function_name

# Use:
from very.long.module.path import very_long_function_name, another_long_function_name
```

## Step 5: Emergency Fallback Options

If the systematic approach is too slow or overwhelming:
1. **Temporarily increase line length** in pyproject.toml to 120 characters
2. **Fix critical files first** (core pipeline files in sotd/)
3. **Use per-file ignores** for non-critical files
4. **Gradual improvement** over time
5. **Focus on specific directories** (e.g., just sotd/ first)

### Per-file ignore examples:
```python
# Add to top of file for specific ignores
# ruff: noqa: E501  # Line too long
# ruff: noqa: F401  # Unused import
```

## Step 6: Success Metrics

### Current Session Goals (2025-09-03):
- [ ] E501 errors: 2,255 → 0
- [ ] F401 errors: 85 → 0  
- [ ] F841 errors: 24 → 0
- [ ] Total linter errors: 2,364 → 0
- [ ] Cursor linting no longer times out
- [ ] All tests still pass

### Future Session Goals:
- [ ] Run error discovery to get current counts
- [ ] Set realistic targets based on error volume
- [ ] Track progress in linter_errors_todo.md
- [ ] Maintain zero linter errors going forward

## Step 7: Commands Reference

### Discovery Commands:
```bash
# Get current error counts (using Makefile targets)
make lint-count

# Or manually:
ruff check . | wc -l
ruff check . --select E501 | wc -l
ruff check . --select F401 | wc -l
ruff check . --select F841 | wc -l

# Find files with most errors
ruff check . --select E501 --output-format=json | jq -r '.[] | select(.code == "E501") | .filename' | sort | uniq -c | sort -nr | head -10
```

### Fix Commands:
```bash
# Systematic workflow (recommended)
make lint-systematic

# Individual steps:
make lint-auto-fix    # Auto-fix all fixable errors
make lint-format      # Format all files (handles most E501 errors)

# Or manually:
ruff check . --fix
ruff format .
black .

# Fix specific error types
ruff check . --select F401 --fix
ruff check . --select F841 --fix
```

### Validation Commands:
```bash
# Check specific error types (using Makefile targets)
make lint-e501
make lint-f401
make lint-f841

# Or manually:
ruff check . --select E501
ruff check . --select F401
ruff check . --select F841

# Full linter check
ruff check .

# Run tests
make test

# Full quality check
make format lint typecheck test
```

### Progress Tracking:
```bash
# Update linter_errors_todo.md with current counts
# Mark categories as COMPLETE when done
# Add notes about complex cases
```

## Step 8: Best Practices

### General Approach:
- **Start with systematic workflow**: `make lint-systematic`
- **Start with E501 errors** - they're usually the most common and timeout-causing
- **Use automated tools first** - ruff format and black handle most cases
- **Manual fixes last** - only for complex cases
- **Track progress** - update linter_errors_todo.md regularly
- **Test frequently** - ensure no regressions
- **Commit incrementally** - logical chunks of fixes

### Makefile Integration:
- **Use `make lint-systematic`** for complete workflow
- **Use `make lint-count`** to get current error counts
- **Use `make lint-e501`**, `make lint-f401`, `make lint-f841`** for specific error types
- **Use `make lint-auto-fix`** and `make lint-format`** for automated fixes

### Reusability Tips:
- **Run discovery first** - get current error counts before starting
- **Update tracking file** - keep linter_errors_todo.md current
- **Set realistic goals** - don't try to fix everything at once
- **Use this prompt** - bookmark for future linter maintenance
- **Regular maintenance** - run linter checks weekly to prevent accumulation

### When to Use This Prompt:
- Cursor linting times out
- Large number of linter errors accumulate
- Before major releases or commits
- Regular code quality maintenance
- After adding new code or refactoring
