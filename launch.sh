#!/bin/bash
cd "/home/lukas/Documents/Dev/spotify overlay"
if [ -f "./venv/bin/python" ]; then
    ./venv/bin/python main.py
else
    spotify-overlay
fi
