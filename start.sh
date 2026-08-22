#!/bin/bash
# Start the Node.js dashboard in the background
node server.js &

# Start the Python Discord bot in the foreground
python bot.py