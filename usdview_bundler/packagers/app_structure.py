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
        
        # Launcher script content
        launcher_content = """#!/bin/bash
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
"""
        
        # Write launcher script
        with open(launcher_path, "w") as f:
            f.write(launcher_content)
        
        # Make executable
        os.chmod(launcher_path, 0o755)
