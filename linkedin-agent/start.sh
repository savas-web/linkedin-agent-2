#!/bin/bash
# Load user environment (picks up ANTHROPIC_API_KEY from ~/.zshrc)
source ~/.zshrc 2>/dev/null || source ~/.zprofile 2>/dev/null

cd "/Users/savassuner/CLAUDE CODE/linkedin-agent"
exec "./venv/bin/python" main.py
