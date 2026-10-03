#!/bin/sh
# SkillsBench verifier contract: write score to /logs/verifier/reward.txt
set -e
cd "$(dirname "$0")"
python verify.py
