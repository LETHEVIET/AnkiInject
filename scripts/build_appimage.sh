#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting AppImage Build Process..."

# 0. Cleanup old artifacts to prevent "Text file busy" errors
rm -f *.AppImage
rm -rf AppDir
rm -rf build/
rm -rf dist/

# 0.5 (Replaces Python script)
# Icons are generated during frontend build

# 1. Build Frontend & Icons
echo "📦 Building Frontend..."
cd frontend
npm install
echo "🎨 Generating Icons (Node.js)..."
npm run generate-icons
npm run build
cd ..

# 2. Ensure PyInstaller is in the environment
echo "🐍 Ensuring PyInstaller is ready..."
uv venv
uv pip install pyinstaller

# 3. Bundle with PyInstaller using uv
echo "🛠️ Bundling with PyInstaller (via uv)..."
uv run pyinstaller --noconfirm --onedir --windowed \
    --add-data "frontend/dist:frontend/dist" \
    --add-data "app:app" \
    --name "anki-inject" \
    main.py

# 4. Prepare AppDir
echo "📂 Preparing AppDir..."
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/512x512/apps

cp dist/anki-inject/anki-inject AppDir/usr/bin/
cp -r dist/anki-inject/* AppDir/usr/bin/
cp packaging/anki-inject.desktop AppDir/usr/share/applications/
cp packaging/anki-inject.png AppDir/usr/share/icons/hicolor/512x512/apps/

# 5. Download & Run linuxdeploy
echo "🔨 Packaging as AppImage..."
if [ ! -f linuxdeploy-x86_64.AppImage ]; then
    wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

export ARCH=x86_64
./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

echo "✅ AppImage created successfully: Anki_Inject-x86_64.AppImage"
