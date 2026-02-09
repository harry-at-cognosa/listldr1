"""
SQM Logger Module

Custom logging for the SQM template loader with dual output (file + console).
Log format: SQMLoad|{YYMMDD}_{HHMMSS}|{message}
File naming: SQM_{slug}_v{version}_{YYMMDD}_{HHMMSS}_log.txt
"""

import os
import sys
from datetime import datetime
from pathlib import Path


class SQMLogger:
    """Logger with dual output (file + console) and custom format."""

    def __init__(
        self,
        log_dir: str,
        slug: str,
        version: str,
        silent: bool = False
    ):
        self.silent = silent
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Generate log filename with timestamp
        now = datetime.now()
        timestamp = now.strftime("%y%m%d_%H%M%S")
        version_str = version.replace(".", "")
        filename = f"SQM_{slug}_v{version_str}_{timestamp}_log.txt"
        self.log_path = self.log_dir / filename

        # Open log file
        self.log_file = open(self.log_path, "w", encoding="utf-8")
        self.start_time = now

    def _format_message(self, message: str) -> str:
        """Format message with SQMLoad prefix and timestamp."""
        now = datetime.now()
        timestamp = now.strftime("%y%m%d_%H%M%S")
        return f"SQMLoad|{timestamp}|{message}"

    def log(self, message: str) -> None:
        """Write a formatted log message to file (and console unless silent)."""
        formatted = self._format_message(message)
        self.log_file.write(formatted + "\n")
        self.log_file.flush()

        if not self.silent:
            print(formatted)

    def progress(self, char: str) -> None:
        """Write a progress character without newline."""
        sys.stdout.write(char)
        sys.stdout.flush()

    def newline(self) -> None:
        """Write a newline to console (for after progress indicators)."""
        print()

    def close(self) -> None:
        """Close the log file."""
        if self.log_file:
            self.log_file.close()

    @property
    def elapsed_seconds(self) -> float:
        """Return seconds elapsed since logger was created."""
        return (datetime.now() - self.start_time).total_seconds()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
