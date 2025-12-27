#!/bin/bash

# Exit on error
set -e

echo "📦 Building Frontend..."
cd frontend
npm install
echo "🎨 Generating Icons (Node.js)..."
# npm run generate-icons
npm run build
cd ..
