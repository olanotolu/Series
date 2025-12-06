#!/bin/bash
# Script to run consumer.py and keep it running
# Automatically restarts if it crashes

cd "$(dirname "$0")"

echo "🚀 Starting Series Consumer..."
echo "   Press Ctrl+C to stop"
echo ""

# Run consumer in a loop (auto-restart on crash)
while true; do
    python consumer.py
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Consumer exited normally"
        break
    else
        echo "⚠️  Consumer crashed (exit code: $EXIT_CODE)"
        echo "🔄 Restarting in 5 seconds..."
        sleep 5
    fi
done

