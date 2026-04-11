#!/bin/bash
cd "$(dirname "$0")"
echo "Starting DAN Web → http://localhost:3847"
python3 server/main.py
