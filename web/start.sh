#!/bin/bash
# Start DAN Web Server
cd "$(dirname "$0")"
PYTHON=/home/asher/miniconda3/envs/openclaw/bin/python3
echo "Starting DAN Web → http://localhost:3847"
$PYTHON server/main.py
