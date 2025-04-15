#!/usr/bin/env python3
"""
Manages Python environment creation and packaging.
"""

import os
import json
import subprocess
import shutil
import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Dict


class PythonEnvironment:
    """Creates and packages a Python environment for a specific architecture."""
    
    def __init__(self, 
                 arch: str, 
                 output_dir: Path, 
                 env_name: str,
                 python_version: str = "3.11",
                 skip_if_exists: bool = True):
        """
        Initialize the Python environment manager.
        
        Args:
            arch: Architecture to build for ("ARM" or "x64")
            output_dir: Directory where Python environment will be installed
            env_name: Name for the conda environment
            python_version: Python version to use
            skip_if_exists: Skip environment creation if output already exists
        """
        self.arch = arch
        self.output_dir = output_dir
        self.env_name = env_name
        self.python_version = python_version
        self.skip_if_exists = skip_if_exists
        self.logger = logging.getLogger(f"PythonEnv-{arch}")
        
        # Determine conda subdir based on architecture
        self.conda_subdir = "osx-arm64" if arch == "ARM" else "osx-64"
    
    def create(self) -> None:
        """Create a new conda environment for the specified architecture."""
        self.logger.info(f"Creating conda environment '{self.env_name}' for {self.arch}")
        
        # Check if environment already exists in conda
        try:
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                capture_output=True,
                text=True,
                check=True
            )
            env_list = json.loads(result.stdout)
            
            # In conda's JSON output, 'envs' is a list of environment paths
            env_names = [Path(env).name for env in env_list.get("envs", [])]
            env_exists = self.env_name in env_names
            
            if env_exists:
                self.logger.info(f"Conda environment '{self.env_name}' already exists")
                return
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            self.logger.warning(f"Failed to check if environment exists: {e}")
        
        try:
            # Create conda environment
            subprocess.run([
                "conda", "create", "-y", 
                "-n", self.env_name,
                f"python={self.python_version}", 
                "pyside6",
                "pyopengl",
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
        
        # Check if output already exists and skip if requested
        python_bin = self.output_dir / "bin" / "python"
        if self.skip_if_exists and python_bin.exists():
            self.logger.info(f"Found existing Python environment at {self.output_dir}, skipping packaging")
            return
        
        try:
            # Create temporary tarball
            tarball = self.output_dir.with_suffix(".tar.gz")
            
            # We need to run conda-pack from within a conda environment
            # This creates a temporary activation script and runs it
            pack_script = f"""
                source $(conda info --base)/etc/profile.d/conda.sh
                conda activate {self.env_name}
                conda install -y -c conda-forge conda-pack
                
                # Use --ignore-missing-files to handle common conda-pack issues
                # Use --arcroot '' to avoid nested directory structure
                conda-pack -n {self.env_name} -o {tarball} --ignore-missing-files --arcroot ''
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
            
            # Ensure target directory exists and is empty
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract to target directory with verbose output for debugging
            self.logger.info(f"Extracting conda environment to {self.output_dir}")
            result = subprocess.run([
                "tar", "-xzf", str(tarball), 
                "-C", str(self.output_dir),
                "--verbose"  # Add verbose output for debugging
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Tar extraction failed: {result.stderr}")
                # Try an alternative extraction method
                self.logger.info("Trying alternative extraction method...")
                os.makedirs(self.output_dir, exist_ok=True)
                subprocess.run([
                    "mkdir", "-p", str(self.output_dir)
                ], check=True)
                subprocess.run([
                    "tar", "--no-same-owner", "-xzf", str(tarball), 
                    "-C", str(self.output_dir)
                ], check=True)
            
            # Remove tarball
            tarball.unlink()
            
            self.logger.info(f"Conda environment packaged to {self.output_dir}")
            
            # Clean up the environment
            self._cleanup_environment()
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to package conda environment: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                self.logger.error(f"Error details: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
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