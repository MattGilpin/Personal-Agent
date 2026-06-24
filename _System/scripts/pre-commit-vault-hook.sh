#!/bin/bash
# Pre-commit hook for Lotty's vault editing protocol
# Blocks staged markdown that violates timestamp, chronological, or dash rules.

set -e

VAULT="$HOME/.hermes/vault"
LINT="$VAULT/_System/scripts/vault-lint.py"

if [ ! -f "$LINT" ]; then
    echo "WARNING: vault-lint.py not found at $LINT, skipping validation"
    exit 0
fi

# Run staged validation
python3 "$LINT" staged

# Also check for whitespace errors
cd "$VAULT" && git diff --cached --check

echo "Vault validation passed."
