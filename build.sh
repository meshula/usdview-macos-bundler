#!/bin/bash

set -e

APP_NAME="usdview"
APP_BUNDLE="$APP_NAME.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

ARCHS=("ARM" "x64")
ICON_PNG="icon.png"
ICONSET_DIR="icon.iconset"
ICON_FILE="icon.icns"
PLIST_FILE="Info.plist"

# --- Parse arguments ---
NOTARIZE=false
BUILD_DIR=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--notarize)
      NOTARIZE=true
      shift
      ;;
    --build-dir)
      BUILD_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--build-dir DIR] [-n|--notarize]"
      exit 1
      ;;
  esac
done

if [ -z "$BUILD_DIR" ]; then
  echo "Error: --build-dir is required."
  exit 1
fi

if $NOTARIZE && { [ -z "$APPLE_ID" ] || [ -z "$APPLE_PASSWORD" ]; }; then
  echo "Error: APPLE_ID and APPLE_PASSWORD environment variables must be set for notarization."
  exit 1
fi

mkdir -p "$MACOS" "$RESOURCES"

# Ensure icon.png exists
if [ ! -f "$ICON_PNG" ]; then
  echo "Error: Required icon file '$ICON_PNG' not found."
  exit 1
fi

# Generate .icns from PNG
mkdir -p "$ICONSET_DIR"
sizes=(16 32 64 128 256 512 1024)
for size in "${sizes[@]}"; do
  sfx=""
  [ "$size" -ne 1024 ] && sfx="${size}x${size}"
  sfx_out="$ICONSET_DIR/icon_${sfx}.png"
  sips -z "$size" "$size" "$ICON_PNG" --out "$sfx_out"
done
iconutil -c icns "$ICONSET_DIR" -o "$ICON_FILE"
rm -r "$ICONSET_DIR"

# Copy icon and plist
cp "$ICON_FILE" "$RESOURCES/"
cp "$PLIST_FILE" "$CONTENTS/"

for ARCH in "${ARCHS[@]}"; do
    echo "Setting up Conda environment for $ARCH..."
    ENV_NAME="usd_env_$ARCH"
    ENV_DIR="$RESOURCES/$ARCH/python"
    USD_INSTALL_DIR="$RESOURCES/$ARCH/usd"
    ARCH_BUILD_DIR="$BUILD_DIR/USD_$ARCH"

    # Create new conda environment for each arch
    CONDA_SUBDIR="$([ "$ARCH" = "ARM" ] && echo osx-arm64 || echo osx-64)"
    conda create -y -n "$ENV_NAME" python=3.11 pyside6 -c conda-forge --override-channels --platform="$CONDA_SUBDIR"

    # Activate environment
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "$ENV_NAME"

    echo "Building USD for $ARCH..."
    python build_usd.py "$ARCH_BUILD_DIR" \
        --python --usdview

    # Copy build artifacts
    mkdir -p "$USD_INSTALL_DIR"
    cp -R "$ARCH_BUILD_DIR"/* "$USD_INSTALL_DIR"

    # Package minimal python
    echo "Packing Python for $ARCH..."
    conda-pack -o "$ENV_DIR.tar.gz"
    mkdir -p "$ENV_DIR"
    tar -xzf "$ENV_DIR.tar.gz" -C "$ENV_DIR"
    rm "$ENV_DIR.tar.gz"

    # RPath fixup (simplified)
    echo "Fixing dylib paths for $ARCH..."
    find "$USD_INSTALL_DIR" -name "*.dylib" | while read dylib; do
        install_name_tool -id "@loader_path/$(basename "$dylib")" "$dylib"
    done

    # Cleanup environment
    conda deactivate
    conda remove -y -n "$ENV_NAME" --all

done

# Build launcher stub
cat > "$MACOS/usdview-launcher" <<'EOF'
#!/bin/bash
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  PLATFORM="ARM"
else
  PLATFORM="x64"
fi
APP_DIR="$(dirname "$0")/.."
PYTHON="$APP_DIR/Resources/$PLATFORM/python/bin/python"
USDVIEW="$APP_DIR/Resources/$PLATFORM/usd/bin/usdview"

if [ "$#" -gt 0 ]; then
  "$PYTHON" "$USDVIEW" "$@"
else
  FILE=$(osascript -e 'POSIX path of (choose file with prompt "Open a USD file")')
  if [ -n "$FILE" ]; then
    "$PYTHON" "$USDVIEW" "$FILE"
  fi
fi
EOF
chmod +x "$MACOS/usdview-launcher"

# Optional notarization
if $NOTARIZE; then
  echo "Submitting for notarization..."
  zip -r "$APP_NAME.zip" "$APP_BUNDLE"
  xcrun altool --notarize-app \
    --primary-bundle-id "com.example.usdview" \
    --username "$APPLE_ID" \
    --password "$APPLE_PASSWORD" \
    --file "$APP_NAME.zip"
  echo "Notarization submitted."
fi

echo "App bundle created at $APP_BUNDLE"
