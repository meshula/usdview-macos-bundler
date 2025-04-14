#!/usr/bin/env python3
"""
Utilities for working with macOS property list (plist) files.
"""

import plistlib
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class PlistManager:
    """Manages plist file creation and modification."""
    
    def __init__(self, plist_path: Path):
        """
        Initialize the plist manager.
        
        Args:
            plist_path: Path to the plist file
        """
        self.plist_path = plist_path
        self.logger = logging.getLogger("PlistManager")
    
    def read(self) -> Dict[str, Any]:
        """
        Read a plist file.
        
        Returns:
            Dictionary containing the plist data
        """
        if not self.plist_path.exists():
            self.logger.warning(f"Plist file doesn't exist: {self.plist_path}")
            return {}
            
        try:
            with open(self.plist_path, 'rb') as f:
                return plistlib.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to read plist file: {e}")
            return {}
    
    def write(self, data: Dict[str, Any]) -> bool:
        """
        Write data to a plist file.
        
        Args:
            data: Dictionary containing the plist data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.plist_path, 'wb') as f:
                plistlib.dump(data, f)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write plist file: {e}")
            return False
    
    def update(self, key: str, value: Any) -> bool:
        """
        Update a single key in the plist.
        
        Args:
            key: Key to update
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        data = self.read()
        data[key] = value
        return self.write(data)
    
    def create_app_plist(self, 
                         bundle_id: str,
                         bundle_name: str,
                         bundle_version: str = "1.0",
                         executable: str = "usdview-launcher",
                         icon_file: str = "icon") -> bool:
        """
        Create a basic app Info.plist.
        
        Args:
            bundle_id: Bundle identifier
            bundle_name: Bundle name
            bundle_version: Bundle version
            executable: Name of the executable
            icon_file: Name of the icon file (without extension)
            
        Returns:
            True if successful, False otherwise
        """
        plist_data = {
            "CFBundleName": bundle_name,
            "CFBundleDisplayName": bundle_name,
            "CFBundleIdentifier": bundle_id,
            "CFBundleVersion": bundle_version,
            "CFBundleShortVersionString": bundle_version,
            "CFBundleExecutable": executable,
            "CFBundlePackageType": "APPL",
            "CFBundleIconFile": icon_file,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        }
        
        # Add USD file types
        plist_data["CFBundleDocumentTypes"] = [
            {
                "CFBundleTypeName": "USD File",
                "CFBundleTypeExtensions": ["usd", "usda", "usdc", "usdz"],
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["org.openusd.usd"]
            }
        ]
        
        # Add UTI declarations
        plist_data["UTExportedTypeDeclarations"] = [
            {
                "UTTypeIdentifier": "org.openusd.usd",
                "UTTypeTagSpecification": {
                    "public.filename-extension": ["usd", "usda", "usdc", "usdz"],
                    "public.mime-type": "application/octet-stream"
                },
                "UTTypeDescription": "Universal Scene Description",
                "UTTypeConformsTo": ["public.data"]
            }
        ]
        
        return self.write(plist_data)
