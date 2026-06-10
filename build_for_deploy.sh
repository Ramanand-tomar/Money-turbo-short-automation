#!/bin/bash
echo "Installing dependencies for web-platform..."
cd web-platform || exit
npm install
echo "Building web-platform..."
npm run build
cd ..

echo "Copying build files to resource/public..."
mkdir -p resource/public
cp -r web-platform/dist/* resource/public/

echo "Done! The project is now ready for deployment."
