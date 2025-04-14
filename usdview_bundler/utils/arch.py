#!/usr/bin/env python3
"""
Utilities for architecture detection and management.
"""

import os
import subprocess
import enum
from typing import List, Optional


class Architecture(enum.Enum):
    """Supported CPU architectures."""
    ARM = "ARM"  # Apple Silicon
    X64 = "x64"  # Intel x86_64
    
    @staticmethod
    def detect() -> "Architecture":
        """
        Detect the current system architecture.
        
        Returns:
            The detected Architecture enum value
        """
        try:
            result = subprocess.run(
                ["uname", "-m"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            arch_str = result.stdout.strip()
            
            if arch_str == "arm64":
                return Architecture.ARM
            else:
                return Architecture.X64
                
        except subprocess.CalledProcessError:
            # Default to X64 if detection fails
            return Architecture.X64
            
    @staticmethod
    def get_conda_subdir(arch: "Architecture") -> str:
        """
        Get the conda subdir for a given architecture.
        
        Args:
            arch: The Architecture enum value
            
        Returns:
            The conda subdir string
        """
        if arch == Architecture.ARM:
            return "osx-arm64"
        else:
            return "osx-64"
    
    @staticmethod
    def supports_rosetta() -> bool:
        """
        Check if the system supports Rosetta 2.
        
        Returns:
            True if Rosetta 2 is available, False otherwise
        """
        # Only relevant on ARM-based systems
        if Architecture.detect() != Architecture.ARM:
            return False
            
        try:
            # Check if Rosetta is installed by trying to run an x86_64 binary
            result = subprocess.run(
                ["arch", "-x86_64", "true"],
                capture_output=True,
                check=False
            )
            return result.returncode == 0
            
        except FileNotFoundError:
            return False
