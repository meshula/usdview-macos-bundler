#!/usr/bin/env python3
"""
Handles creation of the basic .app bundle structure and resources.
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import List, Optional


class AppStructure:
    """Creates and manages the macOS .app bundle structure."""
    
    def __init__(self, app_bundle: Path, app_name: str):
        """
        Initialize the app structure.
        
        Args:
            app_bundle: Path to the .app bundle
            app_name: Name of the application
        """
        self.app_bundle = app_bundle
        self.app_name = app_name
        self.contents_dir = app_bundle / "Contents"
        self.macos_dir = self.contents_dir / "MacOS"
        self.resources_dir = self.contents_dir / "Resources"
        self.logger = logging.getLogger("AppStructure")
        
        # Resource files
        self.icon_png = Path("icon.png")
        self.iconset_dir = Path("icon.iconset")
        self.icon_file = Path("icon.icns")
        self.plist_file = Path("Info.plist")
    
    def create_directory_structure(self) -> None:
        """Create the basic directory structure for the app bundle."""
        self.logger.info("Creating app bundle directory structure")
        
        self.macos_dir.mkdir(parents=True, exist_ok=True)
        self.resources_dir.mkdir(parents=True, exist_ok=True)
    
    def copy_resources(self) -> None:
        """Generate and copy resources (icon, plist, etc.) to the app bundle."""
        self.logger.info("Generating and copying resources")
        
        # Verify icon.png exists
        if not self.icon_png.exists():
            self.logger.error(f"Required icon file '{self.icon_png}' not found")
            raise FileNotFoundError(f"Required icon file '{self.icon_png}' not found")
        
        # Generate .icns from PNG
        self._generate_icns()
        
        # Copy icon and plist
        shutil.copy(self.icon_file, self.resources_dir)
        shutil.copy(self.plist_file, self.contents_dir)
        
        # Make sure permissions are correct for the bundle contents
        subprocess.run(["chmod", "-R", "755", str(self.app_bundle)], check=False)
    
    def _generate_icns(self) -> None:
        """Generate .icns file from PNG."""
        self.logger.info("Generating .icns file from PNG")
        
        # Create iconset directory
        self.iconset_dir.mkdir(exist_ok=True)
        
        # Generate different sizes
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for size in sizes:
            suffix = ""
            if size != 1024:
                suffix = f"{size}x{size}"
            else:
                suffix = "1024x1024"
            
            output_file = self.iconset_dir / f"icon_{suffix}.png"
            
            # Use sips to resize
            subprocess.run([
                "sips", 
                "-z", str(size), str(size), 
                str(self.icon_png), 
                "--out", str(output_file)
            ], check=True)
        
        # Use iconutil to create .icns
        subprocess.run([
            "iconutil", 
            "-c", "icns", 
            str(self.iconset_dir), 
            "-o", str(self.icon_file)
        ], check=True)
        
        # Clean up
        shutil.rmtree(self.iconset_dir)
    
    def create_launcher_script(self, archs: List[str]) -> None:
        """
        Create the launcher script that will detect architecture and run the appropriate binary.
        
        Args:
            archs: List of supported architectures
        """
        self.logger.info("Creating launcher script")
        
        launcher_path = self.macos_dir / "usdview-launcher"
        
        # Launcher script content - with additional debugging for library issues
        launcher_content = """#!/bin/bash
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
PYTHON_DIR="$RESOURCES_DIR/python"
PYTHON="$PYTHON_DIR/bin/python3"
USD_DIR="$RESOURCES_DIR/usd"
USDVIEW="$USD_DIR/bin/usdview"
PYTHON_LIB="$PYTHON_DIR/lib/python3.11"

# Set up Python environment variables with absolute paths
export PYTHONHOME="$PYTHON_DIR"
export PYTHONPATH="$PYTHON_LIB:$PYTHON_LIB/lib-dynload:$PYTHON_LIB/site-packages:$USD_DIR/lib/python"
export PATH="$PYTHON_DIR/bin:$USD_DIR/bin:$PATH"
export DYLD_LIBRARY_PATH="$USD_DIR/lib:$PYTHON_DIR/lib:$DYLD_LIBRARY_PATH"
export DYLD_PRINT_LIBRARIES=1  # Debug library loading
export DYLD_PRINT_LIBRARIES_POST_LAUNCH=1  # Debug dynamic libraries 

# Debug info
echo "App Directory: $APP_DIR"
echo "Python: $PYTHON"
echo "USDView: $USDVIEW"
echo "PYTHONHOME: $PYTHONHOME"
echo "PYTHONPATH: $PYTHONPATH"
echo "DYLD_LIBRARY_PATH: $DYLD_LIBRARY_PATH"

# Check if key files and libraries exist
echo "Checking for key files..."
if [ ! -f "$PYTHON" ]; then
  echo "ERROR: Python executable not found at $PYTHON"
  exit 1
fi

if [ ! -f "$USDVIEW" ]; then
  echo "ERROR: USDView script not found at $USDVIEW"
  exit 1
fi

# List Python modules to verify installation
echo "Python modules installed:"
"$PYTHON" -c "help('modules')" || echo "Failed to list modules"

# Try running a minimal Python script to import PySide6 and OpenGL
echo "Testing PySide6 and OpenGL imports..."
"$PYTHON" -c "
try:
    import PySide6
    print('PySide6 version:', PySide6.__version__)
    print('PySide6 path:', PySide6.__file__)
    
    import OpenGL
    print('OpenGL version:', OpenGL.__version__)
    print('OpenGL path:', OpenGL.__file__)
    
    print('Import test successful')
except ImportError as e:
    print('Import error:', e)
" || echo "Failed to import dependencies"

# Get file to open
if [ "$#" -gt 0 ]; then
  FILE="$1"
else
  FILE=$(osascript -e 'POSIX path of (choose file with prompt "Open a USD file")')
fi

# Run usdview with debug output
if [ -n "$FILE" ]; then
  cd "$USD_DIR"
  # Try running with a simple trace first
  echo "Running with basic Python trace..."
  "$PYTHON" -m trace --trace "$USDVIEW" "$FILE" 2>&1 | head -n 100
  
  # Now try the actual command
  echo "Launching USD View..."
  "$PYTHON" "$USDVIEW" "$FILE"
else
  echo "No file selected."
  exit 0
fi
"""
        
        # Write launcher script
        with open(launcher_path, "w") as f:
            f.write(launcher_content)
        
        # Make executable
        os.chmod(launcher_path, 0o755)