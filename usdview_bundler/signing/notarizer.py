#!/usr/bin/env python3
"""
Handles code signing and notarization of macOS app bundles.
"""

import os
import subprocess
import logging
import tempfile
from pathlib import Path
from typing import Optional


class Notarizer:
    """Handles code signing and notarization of macOS app bundles."""
    
    def __init__(self, 
                 app_bundle: Path, 
                 app_name: str,
                 bundle_id: str = "org.openusd.usdview"):
        """
        Initialize the notarizer.
        
        Args:
            app_bundle: Path to the app bundle
            app_name: Name of the application
            bundle_id: Bundle identifier for the app
        """
        self.app_bundle = app_bundle
        self.app_name = app_name
        self.bundle_id = bundle_id
        self.logger = logging.getLogger("Notarizer")
        
        # Check for required environment variables
        self.apple_id = os.environ.get("APPLE_ID")
        self.apple_password = os.environ.get("APPLE_PASSWORD")
        self.team_id = os.environ.get("APPLE_TEAM_ID")
    
    def notarize(self) -> bool:
        """
        Sign and notarize the app bundle.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Beginning notarization process for {self.app_name}")
        
        # Check for required environment variables
        if not self.apple_id or not self.apple_password:
            self.logger.error("APPLE_ID and APPLE_PASSWORD environment variables must be set for notarization")
            return False
        
        try:
            # Sign the app bundle
            self._sign_app_bundle()
            
            # Create a ZIP archive for submission
            zip_path = self._create_zip()
            
            # Submit for notarization
            self._submit_for_notarization(zip_path)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Notarization failed: {e}")
            return False
    
    def _sign_app_bundle(self) -> None:
        """Sign the app bundle with a developer ID."""
        self.logger.info("Signing app bundle")
        
        # Check if team ID is available
        sign_identity = "Developer ID Application"
        if self.team_id:
            sign_identity = f"{sign_identity}: {self.team_id}"
        
        # Sign the app bundle
        subprocess.run([
            "codesign",
            "--force",
            "--deep",
            "--options", "runtime",
            "--sign", sign_identity,
            str(self.app_bundle)
        ], check=True)
        
        self.logger.info("App bundle signed successfully")
    
    def _create_zip(self) -> Path:
        """
        Create a ZIP archive of the app bundle for notarization.
        
        Returns:
            Path to the ZIP archive
        """
        self.logger.info("Creating ZIP archive for notarization")
        
        # Create ZIP in the same directory as the app bundle
        zip_path = self.app_bundle.parent / f"{self.app_name}.zip"
        
        # Remove existing ZIP if it exists
        if zip_path.exists():
            zip_path.unlink()
        
        # Create ZIP archive
        subprocess.run([
            "ditto",
            "-c",
            "-k",
            "--keepParent",
            str(self.app_bundle),
            str(zip_path)
        ], check=True)
        
        self.logger.info(f"ZIP archive created at {zip_path}")
        return zip_path
    
    def _submit_for_notarization(self, zip_path: Path) -> None:
        """
        Submit the app for notarization.
        
        Args:
            zip_path: Path to the ZIP archive containing the app bundle
        """
        self.logger.info("Submitting app for notarization")
        
        # Create a temporary file for the password
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(self.apple_password.encode())
            password_path = temp.name
        
        try:
            # Submit for notarization
            subprocess.run([
                "xcrun", "altool",
                "--notarize-app",
                "--primary-bundle-id", self.bundle_id,
                "--username", self.apple_id,
                "--password", "@" + password_path,
                "--file", str(zip_path)
            ], check=True)
            
            self.logger.info("App submitted for notarization")
            self.logger.info("Check status with: xcrun altool --notarization-info <RequestUUID> -u <username>")
            
        finally:
            # Clean up password file
            os.unlink(password_path)
