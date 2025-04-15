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
                 sign: bool = False,
                 sign_identity: Optional[str] = None,
                 app_name: str = "usdview",
                 skip_if_exists: bool = True,
                 log_dir: Optional[Path] = None):
        """
        Initialize the bundler.
        
        Args:
            build_dir: Directory for intermediate build files
            usd_src_dir: Directory containing USD source code
            output_dir: Directory where final app bundle will be placed
            archs: List of architectures to support ("ARM", "x64")
            notarize: Whether to notarize the app bundle
            sign: Whether to sign the app bundle
            sign_identity: Developer ID to use for signing (None for ad-hoc)
            app_name: Name of the application
            skip_if_exists: Skip build steps if outputs already exist
            log_dir: Directory for log files
        """
        self.build_dir = build_dir
        self.usd_src_dir = usd_src_dir
        self.output_dir = output_dir or Path.cwd()
        self.archs = archs
        self.notarize = notarize
        self.sign = sign or notarize  # Always sign if notarizing
        self.sign_identity = sign_identity
        self.app_name = app_name
        self.skip_if_exists = skip_if_exists
        
        # Setup logging
        from usdview_bundler.utils import log_manager
        self.log_manager = log_manager.initialize(app_name, log_dir or build_dir / "logs")
        self.logger = self.log_manager.get_logger("Bundler")
        
        # Setup app bundle paths
        self.app_bundle = self.output_dir / f"{app_name}.app"
        self.contents_dir = self.app_bundle / "Contents"
        self.macos_dir = self.contents_dir / "MacOS"
        self.resources_dir = self.contents_dir / "Resources"
    
    def configure(self) -> None:
        """Configure the build environment."""
        self.logger.info(f"Configuring build for {self.app_name}")
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def build(self) -> None:
        """Build the app bundle."""
        self.logger.info(f"Building {self.app_name} for archs: {', '.join(self.archs)}")
        
        # Use a staging directory for building components
        staging_dir = self.build_dir / "staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each architecture in the staging area
        arch_dirs = {}
        for arch in self.archs:
            self.logger.info(f"Building for {arch} architecture")
            arch_dir = staging_dir / arch
            arch_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure arch-specific paths
            arch_build_dir = self.build_dir / f"USD_{arch}"
            
            # Initialize arch-specific components
            usd_builder = UsdBuilder(
                arch=arch,
                build_dir=arch_build_dir,
                output_dir=arch_dir / "usd",
                usd_src_dir=self.usd_src_dir
            )
            
            python_env = PythonEnvironment(
                arch=arch,
                output_dir=arch_dir / "python",
                env_name=f"usd_env_{arch}",
                skip_if_exists=self.skip_if_exists
            )
            
            # Build components
            usd_builder.build()
            python_env.create()
            python_env.package()
            
            # Store directory for later
            arch_dirs[arch] = arch_dir
            
            self.logger.info(f"Completed build for {arch}")
            
        # -------- Final assembly: create app bundle and populate it all at once --------
        
        # First, check if an existing bundle needs to be removed
        if self.app_bundle.exists():
            self.logger.info(f"Removing existing app bundle at {self.app_bundle}")
            shutil.rmtree(self.app_bundle)
        
        # Initialize the app structure component
        self.app_structure = AppStructure(
            app_bundle=self.app_bundle,
            app_name=self.app_name
        )
        
        # Create the basic directory structure
        self.app_structure.create_directory_structure()
        
        # Copy arch-specific components into the bundle
        for arch, arch_dir in arch_dirs.items():
            self.logger.info(f"Copying {arch} components to app bundle")
            
            # Create the architecture-specific resources directory
            arch_resources_dir = self.resources_dir / arch
            arch_resources_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy USD files
            usd_src = arch_dir / "usd"
            usd_dst = arch_resources_dir / "usd"
            self.logger.info(f"Copying USD from {usd_src} to {usd_dst}")
            
            # Use rsync for more reliable copying
            try:
                subprocess.run([
                    "rsync",
                    "-a",              # Archive mode (recursive, preserve attributes)
                    "--ignore-errors",  # Continue even if there are errors
                    f"{usd_src}/",
                    f"{usd_dst}/"
                ], check=False)
            except Exception as e:
                self.logger.warning(f"Error copying USD files: {e}")
            
            # Copy Python environment
            python_src = arch_dir / "python"
            python_dst = arch_resources_dir / "python"
            self.logger.info(f"Copying Python from {python_src} to {python_dst}")
            
            # Use rsync for more reliable copying
            try:
                subprocess.run([
                    "rsync",
                    "-a",              # Archive mode (recursive, preserve attributes)
                    "--ignore-errors",  # Continue even if there are errors
                    f"{python_src}/",
                    f"{python_dst}/"
                ], check=False)
            except Exception as e:
                self.logger.warning(f"Error copying Python files: {e}")
            
            # Fix dynamic libraries
            self.logger.info(f"Fixing dynamic libraries for {arch}")
            dylib_fixer = DylibFixer(base_dir=arch_resources_dir)
            dylib_fixer.fix_libraries()
        
        # Finally, copy resources and create launcher script
        self.logger.info("Adding resources and creating launcher script")
        self.app_structure.copy_resources()
        self.app_structure.create_launcher_script(self.archs)
        
        # Sign the app bundle if requested
        if self.sign:
            self.logger.info("Signing app bundle...")
            
            # First remove any existing signatures that might be invalid
            self.logger.info("Removing existing signatures...")
            try:
                # Find and remove signatures from .so files
                subprocess.run(
                    f"find '{self.app_bundle}' -type f -name '*.so' -exec codesign --remove-signature {{}} \\;",
                    shell=True, check=False
                )
                
                # Find and remove signatures from .dylib files
                subprocess.run(
                    f"find '{self.app_bundle}' -type f -name '*.dylib' -exec codesign --remove-signature {{}} \\;",
                    shell=True, check=False
                )
                
                # Find and remove signatures from executable files in bin directories
                subprocess.run(
                    f"find '{self.app_bundle}' -type f -path '*/bin/*' -perm +111 -exec codesign --remove-signature {{}} \\;",
                    shell=True, check=False
                )
            except Exception as e:
                self.logger.warning(f"Error removing signatures: {e}")
            
            # Then sign the whole bundle
            try:
                # Determine signing identity
                sign_identity = self.sign_identity if self.sign_identity else "-"
                sign_args = ["codesign", "--force", "--deep"]
                
                # Add signing identity
                sign_args.extend(["--sign", sign_identity])
                
                # Add option to disable hardened runtime
                sign_args.extend(["--options", "runtime"])
                
                # Add the app bundle path
                sign_args.append(str(self.app_bundle))
                
                # Execute the codesign command
                self.logger.info(f"Signing with identity: {sign_identity}")
                result = subprocess.run(sign_args, check=False, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.logger.warning(f"Signing returned non-zero exit code: {result.returncode}")
                    self.logger.warning(f"Signing stderr: {result.stderr}")
                else:
                    self.logger.info("Signing completed successfully")
            except Exception as e:
                self.logger.error(f"Error during code signing: {e}")
        
        # Notarize if requested
        if self.notarize:
            self.notarizer = Notarizer(
                app_bundle=self.app_bundle,
                app_name=self.app_name,
                sign_identity=self.sign_identity
            )
            self.notarizer.notarize()
            
        self.logger.info(f"App bundle created at {self.app_bundle}")


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
    parser.add_argument("--sign", action="store_true",
                        help="Sign the app bundle (without notarization)")
    parser.add_argument("--sign-identity", default=None,
                        help="Developer ID to use for signing (omit for ad-hoc signing)")
    parser.add_argument("--app-name", default="usdview",
                        help="Name of the application (default: usdview)")
    parser.add_argument("--force-rebuild", action="store_true",
                        help="Force rebuild even if previously built")
    parser.add_argument("--log-dir", type=Path, default=None,
                        help="Directory for log files (defaults to build-dir/logs)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging level if verbose flag is set
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    bundler = Bundler(
        build_dir=args.build_dir,
        usd_src_dir=args.usd_src_dir,
        output_dir=args.output_dir,
        archs=args.archs,
        notarize=args.notarize,
        sign=args.sign,
        sign_identity=args.sign_identity,
        app_name=args.app_name,
        skip_if_exists=not args.force_rebuild,
        log_dir=args.log_dir
    )
    
    bundler.configure()
    bundler.build()


if __name__ == "__main__":
    main()