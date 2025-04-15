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
                 usd_src_dir: Path):
        """
        Initialize the USD builder.
        
        Args:
            arch: Architecture to build for ("ARM" or "x64")
            build_dir: Directory for intermediate USD build files
            output_dir: Directory where USD will be installed
            usd_src_dir: Directory containing USD source code
        """
        self.arch = arch
        self.build_dir = build_dir
        self.output_dir = output_dir
        self.usd_src_dir = usd_src_dir
        self.build_script = usd_src_dir / "build_scripts" / "build_usd.py"
        self.logger = logging.getLogger(f"UsdBuilder-{arch}")
    
    def build(self) -> None:
        """Build USD for the specified architecture."""
        self.logger.info(f"Building USD for {self.arch}")
        
        # Verify build script exists
        if not self.build_script.exists():
            self.logger.error(f"USD build script not found at {self.build_script}")
            raise FileNotFoundError(f"USD build script not found at {self.build_script}")
        
        # Create build directory
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if USD was already built by looking for pxrConfig.cmake
        config_cmake = self.build_dir / "pxrConfig.cmake"
        if config_cmake.exists():
            self.logger.info(f"Found existing USD build at {self.build_dir}, skipping build step")
            # Still need to copy build artifacts to output directory
            self.logger.info(f"Copying USD build artifacts to {self.output_dir}")
            self._copy_build_artifacts()
            return
        
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
                str(self.build_script), 
                str(self.build_dir),
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
        """Copy build artifacts to the output directory using robust methods that handle permission issues."""
        self.logger.info(f"Copying USD build artifacts to {self.output_dir}")
        
        # Make sure destination exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use rsync with ignore-errors flag instead of Python's shutil
        # This is more robust for handling permission issues
        try:
            cmd = [
                "rsync",
                "-a",              # Archive mode (recursive, preserve attributes)
                "--ignore-errors",  # Continue even if there are errors
                "--exclude=.git",   # Exclude any git directories
                f"{self.build_dir}/",  # Source with trailing slash to copy contents
                f"{self.output_dir}/"   # Destination
            ]
            
            result = subprocess.run(
                cmd, 
                check=False,  # Don't raise exception on error
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.warning(f"rsync reported issues: {result.stderr}")
                self.logger.warning("Some files may not have been copied, but we'll continue")
        except Exception as e:
            self.logger.warning(f"Error during rsync copy: {e}")
            self.logger.warning("Falling back to manual directory copy with error handling")
            
            # Fallback to manual copy with error suppression
            self._manual_copy_with_error_handling(self.build_dir, self.output_dir)
            
        self.logger.info(f"USD build artifacts copied to {self.output_dir}")
    
    def _manual_copy_with_error_handling(self, src_dir: Path, dst_dir: Path) -> None:
        """
        Manually copy directory contents with error handling for permissions.
        
        Args:
            src_dir: Source directory
            dst_dir: Destination directory
        """
        # Make sure destination exists
        dst_dir.mkdir(parents=True, exist_ok=True)
        
        # Process all items in source directory
        for item in src_dir.iterdir():
            dst_path = dst_dir / item.name
            
            try:
                if item.is_dir():
                    # Create destination directory
                    dst_path.mkdir(parents=True, exist_ok=True)
                    # Recursively copy contents
                    self._manual_copy_with_error_handling(item, dst_path)
                else:
                    # Copy file with error handling
                    try:
                        shutil.copy2(item, dst_path)
                    except PermissionError:
                        self.logger.debug(f"Permission error copying {item}, skipping")
                    except Exception as e:
                        self.logger.debug(f"Error copying {item}: {e}, skipping")
            except Exception as e:
                self.logger.debug(f"Error processing {item}: {e}, skipping")