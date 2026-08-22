#!/bin/bash
# 1. Build Next.js frontend into static assets
cd viper-audio-core
npm install
npm run build
cd ..

# 2. Launch FastAPI + Discord Bot
python bot.py