#!/usr/bin/env python3
"""
Handles code signing and notarization of macOS app bundles.
"""

import os
import re
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
                 bundle_id: str = "org.openusd.usdview",
                 sign_identity: Optional[str] = None):
        """
        Initialize the notarizer.
        
        Args:
            app_bundle: Path to the app bundle
            app_name: Name of the application
            bundle_id: Bundle identifier for the app
            sign_identity: Developer ID to use for signing
        """
        self.app_bundle = app_bundle
        self.app_name = app_name
        self.bundle_id = bundle_id
        self.logger = logging.getLogger("Notarizer")
        self.sign_identity = sign_identity
        
        # Check for required environment variables
        self.apple_id = os.environ.get("APPLE_ID")
        self.apple_password = os.environ.get("APPLE_PASSWORD")
        self.team_id = os.environ.get("APPLE_TEAM_ID") or self._extract_team_id(sign_identity)
        
        # Flag for signing only without notarization
        self.sign_only = False
    
    def _extract_team_id(self, sign_identity: Optional[str]) -> Optional[str]:
        """
        Extract team ID from the signing identity.
        
        Args:
            sign_identity: Developer ID signature
            
        Returns:
            Team ID if found, None otherwise
        """
        if not sign_identity:
            return None
            
        # Identity format: "Developer ID Application: Name (TEAM_ID)"
        # Or format: "Developer ID Application: TEAM_ID"
        match = re.search(r'\(([A-Z0-9]+)\)$', sign_identity)
        if match:
            return match.group(1)
        
        parts = sign_identity.split(':')
        if len(parts) > 1:
            # Try to get the team ID from the part after the colon
            id_part = parts[1].strip()
            # If it looks like a team ID (10 alphanumeric characters)
            if re.match(r'^[A-Z0-9]{10}$', id_part):
                return id_part
        
        return None
    
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
            
            # If sign_only is set, skip notarization
            if self.sign_only:
                self.logger.info("Signing completed. Skipping notarization as requested.")
                return True
            
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
        if self.sign_identity:
            sign_identity = self.sign_identity
        elif self.team_id:
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