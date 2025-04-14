#!/usr/bin/env python3
"""
Handles fixing dynamic library dependency paths for macOS bundles.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Set


class DylibFixer:
    """Fixes dynamic library paths in macOS bundles."""
    
    def __init__(self, base_dir: Path):
        """
        Initialize the dynamic library fixer.
        
        Args:
            base_dir: Base directory containing libraries to fix
        """
        self.base_dir = base_dir
        self.logger = logging.getLogger("DylibFixer")
        self.processed_libs: Set[Path] = set()
    
    def fix_libraries(self) -> None:
        """Find and fix all dynamic libraries in the base directory."""
        self.logger.info(f"Fixing dynamic library paths in {self.base_dir}")
        
        # Find all dynamic libraries
        dylibs = list(self.base_dir.glob("**/*.dylib"))
        self.logger.info(f"Found {len(dylibs)} dynamic libraries to process")
        
        # Process each library
        for dylib in dylibs:
            self._process_library(dylib)
    
    def _process_library(self, lib_path: Path) -> None:
        """
        Process a single dynamic library, fixing its ID and dependencies.
        
        Args:
            lib_path: Path to the dynamic library
        """
        if lib_path in self.processed_libs:
            return
        
        self.logger.debug(f"Processing library: {lib_path}")
        self.processed_libs.add(lib_path)
        
        # Fix the library ID
        self._fix_library_id(lib_path)
        
        # Get and fix dependencies
        deps = self._get_dependencies(lib_path)
        for dep in deps:
            if self._is_system_lib(dep):
                continue
                
            # If dependency is within our bundle, fix it
            dep_path = self._find_dependency_in_bundle(dep)
            if dep_path:
                # Process this dependency first
                self._process_library(dep_path)
                
                # Now update the reference in the current library
                self._fix_dependency_reference(lib_path, dep, dep_path)
    
    def _fix_library_id(self, lib_path: Path) -> None:
        """
        Fix the ID of a dynamic library.
        
        Args:
            lib_path: Path to the dynamic library
        """
        lib_name = lib_path.name
        new_id = f"@loader_path/{lib_name}"
        
        try:
            subprocess.run([
                "install_name_tool",
                "-id", new_id,
                str(lib_path)
            ], check=True, capture_output=True)
            
            self.logger.debug(f"Fixed ID for {lib_path.name} -> {new_id}")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to fix library ID for {lib_path}: {e.stderr.decode()}")
            raise
    
    def _get_dependencies(self, lib_path: Path) -> List[str]:
        """
        Get all dependencies of a dynamic library.
        
        Args:
            lib_path: Path to the dynamic library
            
        Returns:
            List of dependency paths
        """
        try:
            result = subprocess.run([
                "otool", "-L", str(lib_path)
            ], check=True, capture_output=True, text=True)
            
            # Parse otool output
            lines = result.stdout.strip().split('\n')[1:]  # Skip first line (the library itself)
            dependencies = []
            
            for line in lines:
                parts = line.strip().split()
                if parts:
                    dependencies.append(parts[0])
            
            return dependencies
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get dependencies for {lib_path}: {e.stderr}")
            raise
    
    def _is_system_lib(self, lib_path: str) -> bool:
        """
        Check if a library is a system library.
        
        Args:
            lib_path: Path to the library
            
        Returns:
            True if it's a system library, False otherwise
        """
        system_prefixes = [
            "/System/Library/",
            "/usr/lib/",
            "@rpath/",
            "@loader_path/"
        ]
        
        return any(lib_path.startswith(prefix) for prefix in system_prefixes)
    
    def _find_dependency_in_bundle(self, dep_path: str) -> Optional[Path]:
        """
        Find a dependency in the bundle.
        
        Args:
            dep_path: Original dependency path
            
        Returns:
            Path to the dependency in the bundle, or None if not found
        """
        dep_name = os.path.basename(dep_path)
        
        # Search for the dependency in the bundle
        candidates = list(self.base_dir.glob(f"**/{dep_name}"))
        
        if candidates:
            return candidates[0]
        
        return None
    
    def _fix_dependency_reference(self, lib_path: Path, old_ref: str, dep_path: Path) -> None:
        """
        Fix a dependency reference in a library.
        
        Args:
            lib_path: Path to the library being fixed
            old_ref: Original reference path
            dep_path: Path to the dependency in the bundle
        """
        # Calculate relative path for the new reference
        rel_path = os.path.relpath(dep_path.parent, lib_path.parent)
        if rel_path == ".":
            new_ref = f"@loader_path/{dep_path.name}"
        else:
            new_ref = f"@loader_path/{rel_path}/{dep_path.name}"
        
        try:
            subprocess.run([
                "install_name_tool",
                "-change", old_ref, new_ref,
                str(lib_path)
            ], check=True, capture_output=True)
            
            self.logger.debug(f"Fixed dependency in {lib_path.name}: {old_ref} -> {new_ref}")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to fix dependency reference in {lib_path}: {e.stderr.decode()}")
            raise
