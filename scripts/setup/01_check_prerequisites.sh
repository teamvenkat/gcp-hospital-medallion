#!/usr/bin/env bash

# Hospital Medallion - local environment prerequisite check
# This script ONLY checks the machine. It does not install or modify anything.

set -u

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() {
    echo "[PASS] $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo "[FAIL] $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

warn() {
    echo "[WARN] $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "========================================"
echo "Hospital Medallion"
echo "Environment Prerequisite Check"
echo "========================================"
echo

# ---------------------------------------------------------------------------
# Operating system
# ---------------------------------------------------------------------------
if [[ "$(uname -s)" == "Darwin" ]]; then
    pass "Operating System : macOS"
else
    fail "Operating System : expected macOS, found $(uname -s)"
fi

ARCH="$(uname -m)"
if [[ "$ARCH" == "arm64" ]]; then
    pass "Architecture     : Apple Silicon (arm64)"
elif [[ "$ARCH" == "x86_64" ]]; then
    warn "Architecture     : Intel (x86_64)"
else
    warn "Architecture     : $ARCH"
fi

echo

# ---------------------------------------------------------------------------
# Required command-line tools
# ---------------------------------------------------------------------------
check_command() {
    local cmd="$1"
    local label="$2"

    if command_exists "$cmd"; then
        pass "$label : installed"
    else
        fail "$label : not installed"
    fi
}

check_command python3 "Python 3"
check_command git "Git"
check_command gcloud "Google Cloud CLI"
check_command bq "BigQuery CLI"

echo

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------
if command_exists python3; then
    echo "Python version:"
    python3 --version
fi

if command_exists git; then
    echo "Git version:"
    git --version
fi

if command_exists gcloud; then
    echo "Google Cloud CLI:"
    gcloud --version | head -n 1
fi

if command_exists bq; then
    echo "BigQuery CLI:"
    bq --version 2>&1 | head -n 1
fi

echo

# ---------------------------------------------------------------------------
# Python virtual environment
# ---------------------------------------------------------------------------
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    pass "Python virtual environment : active ($VIRTUAL_ENV)"
else
    warn "Python virtual environment : not active"
fi

echo

# ---------------------------------------------------------------------------
# Google Cloud authentication
# ---------------------------------------------------------------------------
if command_exists gcloud; then

    ACTIVE_ACCOUNT="$(gcloud config get-value account 2>/dev/null | tr -d '\r')"

    if [[ -n "$ACTIVE_ACCOUNT" && "$ACTIVE_ACCOUNT" != "(unset)" ]]; then
        pass "GCP account : $ACTIVE_ACCOUNT"
    else
        fail "GCP account : no active account configured"
    fi

    ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null | tr -d '\r')"

    if [[ -n "$ACTIVE_PROJECT" && "$ACTIVE_PROJECT" != "(unset)" ]]; then
        pass "GCP project : $ACTIVE_PROJECT"
    else
        fail "GCP project : no active project configured"
    fi
else
    fail "GCP authentication : cannot check because gcloud is missing"
fi

echo

# ---------------------------------------------------------------------------
# Google Application Default Credentials
# ---------------------------------------------------------------------------
if command_exists gcloud; then
    ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"

    if [[ -f "$ADC_FILE" ]]; then
        pass "Application Default Credentials : configured"
    else
        warn "Application Default Credentials : not configured"
        echo "       Run: gcloud auth application-default login"
    fi
fi

echo

# ---------------------------------------------------------------------------
# Project directory
# ---------------------------------------------------------------------------
if [[ -f "pyproject.toml" ]]; then
    pass "Project root : pyproject.toml found"
else
    warn "Project root : pyproject.toml not found in current directory"
fi

if [[ -d ".venv" ]]; then
    pass "Project virtual environment : .venv exists"
else
    warn "Project virtual environment : .venv not found"
fi

echo

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "========================================"
echo "Environment Check Summary"
echo "========================================"
echo "Passed : $PASS_COUNT"
echo "Warnings : $WARN_COUNT"
echo "Failed : $FAIL_COUNT"
echo

if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo "Environment prerequisite check PASSED."
    echo "Warnings do not block the next setup step."
    exit 0
else
    echo "Environment prerequisite check FAILED."
    echo "Fix the failed items before continuing."
    exit 1
fi
