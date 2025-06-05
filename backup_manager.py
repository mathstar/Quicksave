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

    def is_s3_path(self, path: str) -> bool:
        """Check if a path is an S3 URL.

        Args:
            path: Path to check

        Returns:
            bool: True if path is an S3 URL
        """
        return path.startswith('s3://')

    def parse_s3_path(self, s3_path: str) -> Tuple[str, str]:
        """Parse an S3 path into bucket and key.

        Args:
            s3_path: S3 path in the format s3://bucket-name/key/path

        Returns:
            tuple: (bucket_name, key_prefix)
        """
        # Remove the s3:// prefix
        path_without_scheme = s3_path[5:]

        # Split into bucket and key
        parts = path_without_scheme.split('/', 1)
        bucket_name = parts[0]
        key_prefix = parts[1] if len(parts) > 1 else ""

        return bucket_name, key_prefix

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

        if self.is_s3_path(backup_dir):
            # Handle S3 backup (placeholder for now)
            print("Note: S3 backup support is not yet fully implemented")
            # Create a temporary backup in the parent directory of source_dir
            source_parent = os.path.dirname(source_dir)
            temp_dir = os.path.join(source_parent, "temp_backups")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            backup_path = os.path.join(temp_dir, backup_filename)
            s3_path = f"{backup_dir}/{backup_filename}"

            # Create the zip locally
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, rel_path)

            print(f"Would upload {backup_path} to {s3_path}")
            return s3_path
        else:
            # Local backup path
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

        if self.is_s3_path(backup_dir):
            # Placeholder for S3 snapshot listing
            print("Note: S3 snapshot listing is not yet fully implemented")
            return snapshots

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

        # Handle S3 backup directory
        if self.is_s3_path(backup_dir):
            bucket_name, key_prefix = self.parse_s3_path(backup_dir)
            if not bucket_name:
                return False, "Invalid S3 URL format. Expected: s3://bucket-name/optional/path"

            # For now, we just validate the format and accept it
            # In a full implementation, you'd verify bucket existence and permissions
            print(f"Note: S3 backup location '{bucket_name}/{key_prefix}' will be used (validation skipped)")
            return True, None

        # Create local backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir)
            except OSError as e:
                return False, f"Error creating backup directory: {e}"

        return True, None
