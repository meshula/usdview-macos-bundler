#!/bin/bash
set -e

# Get absolute path to the app bundle directory
SCRIPT_PATH="$0"
if [[ "$SCRIPT_PATH" != /* ]]; then
  SCRIPT_PATH="$(pwd)/$SCRIPT_PATH"
fi

# APP_DIR should point to the .app bundle root
APP_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  PLATFORM="ARM"
else
  PLATFORM="x64"
fi

# Set up paths using absolute references
RESOURCES_DIR="$APP_DIR/Resources/$PLATFORM"
USD_DIR="$RESOURCES_DIR/usd"

# Check if we're using bundled Python or system Python
PYTHON_DIR="$RESOURCES_DIR/python"
if [ -d "$PYTHON_DIR" ]; then
  # Using bundled Python
  USE_BUNDLED_PYTHON=true
  PYTHON="$PYTHON_DIR/bin/python3"
  PYTHON_LIB="$PYTHON_DIR/lib/python3.11"
  
  # Set up Python environment variables with absolute paths
  export PYTHONHOME="$PYTHON_DIR"
  export PYTHONPATH="$PYTHON_LIB:$PYTHON_LIB/lib-dynload:$PYTHON_LIB/site-packages:$USD_DIR/lib/python:$USD_DIR/build/usd-github-meshula"
  export PATH="$PYTHON_DIR/bin:$USD_DIR/bin:$PATH"
  export DYLD_LIBRARY_PATH="$USD_DIR/lib:$PYTHON_DIR/lib:$DYLD_LIBRARY_PATH"
else
  # Using system Python
  USE_BUNDLED_PYTHON=false
  PYTHON="python3"
  
  # Set up minimal environment for system Python
  export PYTHONPATH="$USD_DIR/lib/python:$PYTHONPATH"
  export PATH="$USD_DIR/bin:$PATH"
  export DYLD_LIBRARY_PATH="$USD_DIR/lib:$DYLD_LIBRARY_PATH"
fi

# Use USD script
USDVIEW="$USD_DIR/bin/usdview"

# Debug info (uncomment for debugging)
# echo "App Directory: $APP_DIR"
# echo "Using bundled Python: $USE_BUNDLED_PYTHON"
# echo "Python: $PYTHON"
# echo "USDView: $USDVIEW"
# echo "PYTHONPATH: $PYTHONPATH"
# echo "DYLD_LIBRARY_PATH: $DYLD_LIBRARY_PATH"

# Get file to open
if [ "$#" -gt 0 ]; then
  FILE="$1"
else
  FILE=$(osascript -e 'POSIX path of (choose file with prompt "Open a USD file")')
fi

# Run usdview
if [ -n "$FILE" ]; then
  cd "$USD_DIR"
  "$PYTHON" "$USDVIEW" "$FILE"
else
  echo "No file selected."
  exit 0
fi