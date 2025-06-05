import os
import zipfile
import pathlib
import boto3
import botocore.exceptions
from typing import List, Tuple, Optional

class BackupManager:
    """Manages backup operations for game saves."""

    def __init__(self, config=None):
        """Initialize the backup manager with optional configuration.

        Args:
            config: Configuration settings for backup operations
        """
        self.config = config or {}
        self._s3_client = None

    @property
    def s3_client(self):
        """Lazy-load S3 client when needed."""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3')
        return self._s3_client

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

    def _cleanup_temp_files(self, temp_file_path: str) -> None:
        """Clean up temporary files and directories after a successful upload.

        Args:
            temp_file_path: Path to the temporary file to remove
        """
        # Get the directory containing the temp file
        temp_dir = os.path.dirname(temp_file_path)

        # Delete the temporary file
        try:
            os.remove(temp_file_path)
            print(f"Removed temporary local file: {temp_file_path}")
        except OSError as e:
            print(f"Warning: Could not remove temporary file {temp_file_path}: {e}")
            return

        # Check if the directory is empty, and if so, delete it
        try:
            # List all files in the directory (excluding . and ..)
            remaining_files = [f for f in os.listdir(temp_dir) if not f.startswith('.')]

            if not remaining_files:
                os.rmdir(temp_dir)
                print(f"Removed empty temporary directory: {temp_dir}")
        except OSError as e:
            print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")

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
            # Handle S3 backup
            # Create a temporary backup in the parent directory of source_dir
            source_parent = os.path.dirname(source_dir)
            temp_dir = os.path.join(source_parent, "temp_backups")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_backup_path = os.path.join(temp_dir, backup_filename)

            # Extract S3 bucket and key
            bucket_name, key_prefix = self.parse_s3_path(backup_dir)
            # Add trailing slash to key prefix if not present and not empty
            if key_prefix and not key_prefix.endswith('/'):
                key_prefix += '/'
            s3_key = f"{key_prefix}{backup_filename}"
            s3_path = f"{backup_dir}/{backup_filename}"

            # Create the zip locally
            print(f"Creating backup archive...")
            with zipfile.ZipFile(temp_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, rel_path)

            # Upload to S3
            print(f"Uploading to S3 bucket '{bucket_name}'...")
            try:
                self.s3_client.upload_file(
                    temp_backup_path,
                    bucket_name,
                    s3_key,
                    Callback=UploadProgressPercentage(temp_backup_path)
                )
                print(f"Upload complete!")

                # Clean up temporary files after successful upload
                self._cleanup_temp_files(temp_backup_path)

                return s3_path
            except botocore.exceptions.ClientError as e:
                print(f"Error uploading to S3: {e}")
                # Return local path if upload fails
                print(f"Backup saved locally to: {temp_backup_path}")
                return temp_backup_path
        else:
            # Local backup path
            backup_path = os.path.join(backup_dir, backup_filename)

            # Create a zip file
            print(f"Creating backup archive...")
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

    def _parse_snapshot_filename(self, filename: str, prefix: str) -> Optional[Tuple[str, str, Optional[str]]]:
        """Parse a snapshot filename to extract timestamp and tag information.

        Args:
            filename: Name of the snapshot file
            prefix: Expected filename prefix (usually the game directory name followed by _)

        Returns:
            tuple: (filename, timestamp, tag) if valid, None otherwise
        """
        if not (filename.startswith(prefix) and filename.endswith('.zip')):
            return None

        # Remove prefix and .zip extension
        name_part = filename[len(prefix):-4]

        # Split by underscore to find components
        parts = name_part.split('_')

        if len(parts) >= 2:  # At minimum we need date and time parts
            # Timestamp is the first two parts joined with an underscore
            timestamp = f"{parts[0]}_{parts[1]}"

            # Anything remaining after is the tag (if present)
            tag = None
            if len(parts) > 2:
                tag = "_".join(parts[2:])

            return (filename, timestamp, tag)

        return None

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
            # Handle S3 listing
            bucket_name, key_prefix = self.parse_s3_path(backup_dir)

            # Add trailing slash to key prefix if not present and not empty
            if key_prefix and not key_prefix.endswith('/'):
                key_prefix += '/'

            # Prepare the S3 prefix to search for
            s3_prefix = f"{key_prefix}{source_name}_"

            try:
                # List objects in the bucket with the given prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=s3_prefix
                )

                # Process the response if objects were found
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        # Extract just the filename from the full key
                        filename = os.path.basename(key)

                        # Use the helper to parse the filename
                        parsed = self._parse_snapshot_filename(filename, prefix)
                        if parsed:
                            snapshots.append(parsed)
            except botocore.exceptions.ClientError as e:
                print(f"Error listing S3 objects: {e}")
                return snapshots
        else:
            # Local directory listing
            if not os.path.exists(backup_dir):
                return snapshots

            for file in os.listdir(backup_dir):
                # Use the helper to parse the filename
                parsed = self._parse_snapshot_filename(file, prefix)
                if parsed:
                    snapshots.append(parsed)

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

            # Verify the bucket exists and is accessible
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"S3 bucket '{bucket_name}' is accessible.")
                return True, None
            except botocore.exceptions.ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == '404':
                    return False, f"S3 bucket '{bucket_name}' does not exist."
                elif error_code == '403':
                    return False, f"No permission to access S3 bucket '{bucket_name}'."
                else:
                    return False, f"Error accessing S3 bucket '{bucket_name}': {e}"
            except Exception as e:
                return False, f"Error connecting to S3: {e}"

        # Create local backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir)
            except OSError as e:
                return False, f"Error creating backup directory: {e}"

        return True, None


# Helper class for S3 upload progress
class UploadProgressPercentage:
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._last_percentage = 0

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = int((self._seen_so_far / self._size) * 100)

        # Only print when percentage changes by at least 10%
        if percentage >= self._last_percentage + 10:
            print(f"Upload progress: {percentage}%")
            self._last_percentage = percentage
