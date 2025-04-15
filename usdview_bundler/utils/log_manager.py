#!/usr/bin/env python3
"""
Logging module with structured output and issue aggregation for easier triage.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field


@dataclass
class IssueGroup:
    """Group of similar issues for aggregation."""
    name: str
    description: str
    count: int = 0
    examples: List[str] = field(default_factory=list)
    max_examples: int = 5
    
    def add_issue(self, message: str) -> None:
        """Add an issue to this group, tracking examples up to the max count."""
        self.count += 1
        if len(self.examples) < self.max_examples:
            self.examples.append(message)


class LogManager:
    """
    Enhanced logging manager that provides both console output and a structured summary.
    """
    
    def __init__(self, 
                app_name: str, 
                log_dir: Optional[Path] = None,
                console_level: int = logging.INFO,
                file_level: int = logging.DEBUG):
        """
        Initialize the logging manager.
        
        Args:
            app_name: Name of the application (used for log file names)
            log_dir: Directory to store log files (defaults to ./logs)
            console_level: Logging level for console output
            file_level: Logging level for file output
        """
        self.app_name = app_name
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamp for log file names
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        
        # Set up main logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)  # Capture everything, let handlers filter
        
        # Clear any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler for detailed logs
        detail_log_path = self.log_dir / f"{app_name}_{timestamp}.log"
        file_handler = logging.FileHandler(detail_log_path)
        file_handler.setLevel(file_level)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Store paths for summary files
        self.summary_path = self.log_dir / f"{app_name}_{timestamp}_summary.txt"
        
        # Issue tracking
        self.issue_groups: Dict[str, IssueGroup] = {}
        self.success_count = 0
        self.warning_count = 0
        self.error_count = 0
        self.processed_items: Set[str] = set()
        
        # Register issue groups
        self._register_issue_groups()
        
        self.logger.info(f"Log files will be written to: {self.log_dir}")
    
    def _register_issue_groups(self) -> None:
        """Register known issue groups for classification."""
        self.issue_groups = {
            "id_not_processed": IssueGroup(
                name="Library ID Could Not Be Processed",
                description="Libraries whose IDs could not be modified due to structural issues"
            ),
            "dependency_not_found": IssueGroup(
                name="Dependency Not Found",
                description="Libraries that depend on other libraries that weren't found in the bundle"
            ),
            "reference_update_failed": IssueGroup(
                name="Reference Update Failed",
                description="Failed to update a dependency reference in a library"
            ),
            "permissions_error": IssueGroup(
                name="Permission Errors",
                description="Files that could not be accessed due to permission issues"
            ),
            "code_signing_error": IssueGroup(
                name="Code Signing Errors",
                description="Files that failed during code signing"
            ),
            "unknown_error": IssueGroup(
                name="Unknown Errors",
                description="Other unclassified errors"
            )
        }
    
    def register_success(self, item_id: str) -> None:
        """Register a successful operation."""
        self.success_count += 1
        self.processed_items.add(item_id)
    
    def register_warning(self, group_id: str, item_id: str, message: str) -> None:
        """
        Register a warning with a specific issue group.
        
        Args:
            group_id: ID of the issue group
            item_id: ID of the processed item
            message: Warning message
        """
        self.warning_count += 1
        self.processed_items.add(item_id)
        
        if group_id in self.issue_groups:
            self.issue_groups[group_id].add_issue(message)
        else:
            self.issue_groups["unknown_error"].add_issue(message)
    
    def register_error(self, group_id: str, item_id: str, message: str) -> None:
        """
        Register an error with a specific issue group.
        
        Args:
            group_id: ID of the issue group
            item_id: ID of the processed item
            message: Error message
        """
        self.error_count += 1
        self.processed_items.add(item_id)
        
        if group_id in self.issue_groups:
            self.issue_groups[group_id].add_issue(message)
        else:
            self.issue_groups["unknown_error"].add_issue(message)
    
    def write_summary(self) -> None:
        """Write a structured summary of the process to a file."""
        with open(self.summary_path, 'w') as f:
            f.write(f"=== {self.app_name} Build Summary ===\n\n")
            
            # Overall statistics
            f.write("## Overall Statistics\n\n")
            f.write(f"Total items processed: {len(self.processed_items)}\n")
            f.write(f"Successful operations: {self.success_count}\n")
            f.write(f"Warnings: {self.warning_count}\n")
            f.write(f"Errors: {self.error_count}\n\n")
            
            # Issue groups
            f.write("## Issue Summary\n\n")
            
            for group_id, group in self.issue_groups.items():
                if group.count > 0:
                    f.write(f"### {group.name} ({group.count})\n\n")
                    f.write(f"{group.description}\n\n")
                    
                    if group.examples:
                        f.write("Examples:\n")
                        for example in group.examples:
                            f.write(f"- {example}\n")
                        
                        if group.count > len(group.examples):
                            f.write(f"- ... and {group.count - len(group.examples)} more\n")
                    
                    f.write("\n")
            
            f.write(f"\nSummary generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.logger.info(f"Summary written to: {self.summary_path}")
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Get a logger for a specific component.
        
        Args:
            name: Logger name (optional)
            
        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(name)
        return self.logger


# Global log manager instance (initialize this in the main script)
log_manager = None


def initialize(app_name: str, log_dir: Optional[Path] = None) -> LogManager:
    """
    Initialize the global log manager.
    
    Args:
        app_name: Name of the application
        log_dir: Directory for log files
        
    Returns:
        LogManager instance
    """
    global log_manager
    log_manager = LogManager(app_name, log_dir)
    return log_manager


def get_manager() -> Optional[LogManager]:
    """
    Get the global log manager instance.
    
    Returns:
        LogManager instance or None if not initialized
    """
    return log_manager


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger for a specific component.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    if log_manager:
        return log_manager.get_logger(name)
    return logging.getLogger(name)