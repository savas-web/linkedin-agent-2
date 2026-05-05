#!/bin/bash
# Load user environment (picks up ANTHROPIC_API_KEY from ~/.zshrc)
source ~/.zshrc 2>/dev/null || source ~/.zprofile 2>/dev/null

cd "/Users/savassuner/CLAUDE CODE/linkedin-agent-2"

# Kill any stale Chromium and Python instances, remove profile lock files
pkill -f "linkedin-agent-2" 2>/dev/null
sleep 2
rm -f linkedin_profile/SingletonLock linkedin_profile/SingletonSocket linkedin_profile/SingletonCookie 2>/dev/null

exec "./venv/bin/python" -u main.py
