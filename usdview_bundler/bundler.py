#!/usr/bin/env python3
"""
Main class that orchestrates the USD viewer bundling process.
"""

import os
import logging
import argparse
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from usdview_bundler.builders.usd_builder import UsdBuilder
from usdview_bundler.builders.python_env import PythonEnvironment
from usdview_bundler.packagers.app_structure import AppStructure
from usdview_bundler.packagers.dylib_fixer import DylibFixer
from usdview_bundler.signing.notarizer import Notarizer
from usdview_bundler.utils.arch import Architecture


class Bundler:
    """Main class for bundling usdview as a macOS application."""
    
    def __init__(self, 
                 build_dir: Path,
                 usd_src_dir: Path,
                 output_dir: Optional[Path] = None,
                 archs: List[str] = ["ARM", "x64"],
                 notarize: bool = False,
                 app_name: str = "usdview",
                 skip_if_exists: bool = True):
        """
        Initialize the bundler.
        
        Args:
            build_dir: Directory for intermediate build files
            usd_src_dir: Directory containing USD source code
            output_dir: Directory where final app bundle will be placed
            archs: List of architectures to support ("ARM", "x64")
            notarize: Whether to notarize the app bundle
            app_name: Name of the application
            skip_if_exists: Skip build steps if outputs already exist
        """
        self.build_dir = build_dir
        self.usd_src_dir = usd_src_dir
        self.output_dir = output_dir or Path.cwd()
        self.archs = archs
        self.notarize = notarize
        self.app_name = app_name
        self.skip_if_exists = skip_if_exists
        
        # Setup app bundle paths
        self.app_bundle = self.output_dir / f"{app_name}.app"
        self.contents_dir = self.app_bundle / "Contents"
        self.macos_dir = self.contents_dir / "MacOS"
        self.resources_dir = self.contents_dir / "Resources"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("Bundler")
        
        # Initialize components
        self.app_structure = AppStructure(
            app_bundle=self.app_bundle,
            app_name=app_name
        )
        
        self.notarizer = Notarizer(
            app_bundle=self.app_bundle,
            app_name=app_name
        )
    
    def configure(self) -> None:
        """Configure the build environment."""
        self.logger.info(f"Configuring build for {self.app_name}")
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def build(self) -> None:
        """Build the app bundle."""
        self.logger.info(f"Building {self.app_name} for archs: {', '.join(self.archs)}")
        
        # Create basic app structure
        self.app_structure.create_directory_structure()
        self.app_structure.copy_resources()
        
        # Process each architecture
        for arch in self.archs:
            self._build_for_arch(arch)
        
        # Create launcher script
        self.app_structure.create_launcher_script(self.archs)
        
        # Notarize if requested
        if self.notarize:
            self.notarizer.notarize()
            
        self.logger.info(f"App bundle created at {self.app_bundle}")
    
    def _build_for_arch(self, arch: str) -> None:
        """Build for a specific architecture."""
        self.logger.info(f"Building for {arch} architecture")
        
        # Configure arch-specific paths
        arch_build_dir = self.build_dir / f"USD_{arch}"
        arch_resources_dir = self.resources_dir / arch
        
        # Initialize arch-specific components
        usd_builder = UsdBuilder(
            arch=arch,
            build_dir=arch_build_dir,
            output_dir=arch_resources_dir / "usd",
            usd_src_dir=self.usd_src_dir
        )
        
        python_env = PythonEnvironment(
            arch=arch,
            output_dir=arch_resources_dir / "python",
            env_name=f"usd_env_{arch}",
            skip_if_exists=self.skip_if_exists
        )
        
        dylib_fixer = DylibFixer(
            base_dir=arch_resources_dir
        )
        
        # Build USD
        usd_builder.build()
        
        # Setup Python environment
        python_env.create()
        python_env.package()
        
        # Fix dynamic library paths
        dylib_fixer.fix_libraries()
        
        self.logger.info(f"Completed build for {arch}")


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Bundle usdview as a macOS app")
    
    parser.add_argument("--build-dir", required=True, type=Path,
                        help="Directory for intermediate build files")
    parser.add_argument("--usd-src-dir", required=True, type=Path,
                        help="Directory containing USD source code")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Directory where the final app bundle will be placed")
    parser.add_argument("--archs", nargs="+", default=["ARM", "x64"],
                        help="Architectures to support (default: ARM x64)")
    parser.add_argument("-n", "--notarize", action="store_true",
                        help="Notarize the app bundle")
    parser.add_argument("--app-name", default="usdview",
                        help="Name of the application (default: usdview)")
    parser.add_argument("--force-rebuild", action="store_true",
                        help="Force rebuild even if previously built")
    
    args = parser.parse_args()
    
    bundler = Bundler(
        build_dir=args.build_dir,
        usd_src_dir=args.usd_src_dir,
        output_dir=args.output_dir,
        archs=args.archs,
        notarize=args.notarize,
        app_name=args.app_name,
        skip_if_exists=not args.force_rebuild
    )
    
    bundler.configure()
    bundler.build()


if __name__ == "__main__":
    main()