#!/usr/bin/env python3
"""
Handles building USD for a specific architecture.
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict


class UsdBuilder:
    """Builds USD for a specific architecture."""
    
    def __init__(self, 
                 arch: str, 
                 build_dir: Path, 
                 output_dir: Path,
                 build_script: str = "build_usd.py"):
        """
        Initialize the USD builder.
        
        Args:
            arch: Architecture to build for ("ARM" or "x64")
            build_dir: Directory for intermediate USD build files
            output_dir: Directory where USD will be installed
            build_script: Path to the USD build script
        """
        self.arch = arch
        self.build_dir = build_dir
        self.output_dir = output_dir
        self.build_script = build_script
        self.logger = logging.getLogger(f"UsdBuilder-{arch}")
    
    def build(self) -> None:
        """Build USD for the specified architecture."""
        self.logger.info(f"Building USD for {self.arch}")
        
        # Create build directory
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine the platform-specific environment
        env = os.environ.copy()
        if self.arch == "ARM":
            env["CONDA_SUBDIR"] = "osx-arm64"
        else:
            env["CONDA_SUBDIR"] = "osx-64"
        
        # Run the USD build script
        self.logger.info(f"Running build_usd.py for {self.arch}")
        try:
            subprocess.run([
                "python", 
                self.build_script, 
                str(self.build_dir),
                "--no-imaging",
                "--python", 
                "--usdview"
            ], env=env, check=True)
            
            # Copy build artifacts to output directory
            self.logger.info(f"Copying USD build artifacts to {self.output_dir}")
            self._copy_build_artifacts()
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"USD build failed for {self.arch}: {e}")
            raise
    
    def _copy_build_artifacts(self) -> None:
        """Copy build artifacts to the output directory."""
        # Use distutils.dir_util.copy_tree or equivalent for recursive copy with overwrite
        for item in self.build_dir.glob("*"):
            if item.is_dir():
                dst_dir = self.output_dir / item.name
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(item, dst_dir, dirs_exist_ok=True)
            else:
                shutil.copy2(item, self.output_dir)
        
        self.logger.info(f"USD build artifacts copied to {self.output_dir}")
