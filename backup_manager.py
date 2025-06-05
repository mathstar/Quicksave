import os
import zipfile
import pathlib
from typing import List, Tuple, Optional

class BackupManager:
    """Manages backup operations for game saves."""

    def __init__(self, config=None):
        """Initialize the backup manager with optional configuration.

        Args:
            config: Configuration settings for backup operations
        """
        self.config = config or {}

    def create_backup(self, source_dir: str, backup_dir: str, snapshot_name: str) -> str:
        """Create a zip backup of the source directory.

        Args:
            source_dir: Directory to backup
            backup_dir: Directory to store the backup
            snapshot_name: Name for the backup file (without extension)

        Returns:
            str: Path to the created backup file
        """
        source_path = pathlib.Path(source_dir)
        source_name = source_path.name

        # Create the backup filename with source directory name
        backup_filename = f"{source_name}_{snapshot_name}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)

        # Create a zip file
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through all files in the source directory
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Calculate the relative path for the zip file
                    rel_path = os.path.relpath(file_path, source_dir)
                    # Add the file to the zip
                    zipf.write(file_path, rel_path)

        return backup_path

    def list_snapshots(self, backup_dir: str, source_name: str) -> List[Tuple[str, str, Optional[str]]]:
        """List all snapshots for a specific game.

        Args:
            backup_dir: Directory containing backups
            source_name: Name of the save directory (game folder name)

        Returns:
            list: List of snapshot details (tuples of filename, timestamp, tag)
        """
        snapshots = []
        prefix = f"{source_name}_"

        if not os.path.exists(backup_dir):
            return snapshots

        for file in os.listdir(backup_dir):
            if file.startswith(prefix) and file.endswith(".zip"):
                # Remove prefix and .zip extension
                name_part = file[len(prefix):-4]

                # Split by underscore to find components
                parts = name_part.split('_')

                if len(parts) >= 2:  # At minimum we need date and time parts
                    # Timestamp is the first two parts joined with an underscore
                    timestamp = f"{parts[0]}_{parts[1]}"

                    # Anything remaining after is the tag (if present)
                    tag = None
                    if len(parts) > 2:
                        tag = "_".join(parts[2:])

                    snapshots.append((file, timestamp, tag))

        # Sort by timestamp (newest first)
        return sorted(snapshots, key=lambda x: x[1], reverse=True)

    def verify_directories(self, save_dir: str, backup_dir: str) -> Tuple[bool, Optional[str]]:
        """Verify that source directory exists and create backup directory if needed.

        Args:
            save_dir: Path to save directory
            backup_dir: Path to backup directory

        Returns:
            tuple: (success, error_message)
        """
        # Check if source directory exists
        if not os.path.exists(save_dir):
            return False, f"Save directory '{save_dir}' does not exist."

        # Create backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir)
            except OSError as e:
                return False, f"Error creating backup directory: {e}"

        return True, None
