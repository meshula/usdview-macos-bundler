#!/usr/bin/env python3
"""
Manages Python environment creation and packaging.
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict


class PythonEnvironment:
    """Creates and packages a Python environment for a specific architecture."""
    
    def __init__(self, 
                 arch: str, 
                 output_dir: Path, 
                 env_name: str,
                 python_version: str = "3.11"):
        """
        Initialize the Python environment manager.
        
        Args:
            arch: Architecture to build for ("ARM" or "x64")
            output_dir: Directory where Python environment will be installed
            env_name: Name for the conda environment
            python_version: Python version to use
        """
        self.arch = arch
        self.output_dir = output_dir
        self.env_name = env_name
        self.python_version = python_version
        self.logger = logging.getLogger(f"PythonEnv-{arch}")
        
        # Determine conda subdir based on architecture
        self.conda_subdir = "osx-arm64" if arch == "ARM" else "osx-64"
    
    def create(self) -> None:
        """Create a new conda environment for the specified architecture."""
        self.logger.info(f"Creating conda environment '{self.env_name}' for {self.arch}")
        
        try:
            # Create conda environment
            subprocess.run([
                "conda", "create", "-y", 
                "-n", self.env_name,
                f"python={self.python_version}", 
                "pyside6",
                "-c", "conda-forge", 
                "--override-channels",
                f"--platform={self.conda_subdir}"
            ], check=True)
            
            self.logger.info(f"Conda environment '{self.env_name}' created successfully")
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create conda environment: {e}")
            raise
    
    def package(self) -> None:
        """Package the conda environment for distribution."""
        self.logger.info(f"Packaging conda environment '{self.env_name}'")
        
        try:
            # Create temporary tarball
            tarball = self.output_dir.with_suffix(".tar.gz")
            
            # We need to run conda-pack from within a conda environment
            # This creates a temporary activation script and runs it
            pack_script = f"""
                source $(conda info --base)/etc/profile.d/conda.sh
                conda activate {self.env_name}
                conda install -y -c conda-forge conda-pack
                conda-pack -n {self.env_name} -o {tarball}
                conda deactivate
            """
            
            # Create a temporary script file
            script_path = Path(f"temp_pack_{self.env_name}.sh")
            with open(script_path, 'w') as f:
                f.write(pack_script)
            
            # Make it executable
            os.chmod(script_path, 0o755)
            
            # Run the script
            subprocess.run(["bash", str(script_path)], check=True)
            
            # Clean up the script
            script_path.unlink()
            
            # Extract to target directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run([
                "tar", "-xzf", str(tarball), 
                "-C", str(self.output_dir)
            ], check=True)
            
            # Remove tarball
            tarball.unlink()
            
            self.logger.info(f"Conda environment packaged to {self.output_dir}")
            
            # Clean up the environment
            self._cleanup_environment()
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to package conda environment: {e}")
            raise
    
    def _cleanup_environment(self) -> None:
        """Remove the conda environment after packaging."""
        self.logger.info(f"Cleaning up conda environment '{self.env_name}'")
        
        try:
            # Deactivate and remove the environment
            subprocess.run([
                "conda", "remove", "-y", 
                "-n", self.env_name, 
                "--all"
            ], check=True)
            
            self.logger.info(f"Conda environment '{self.env_name}' removed")
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to clean up conda environment: {e}")