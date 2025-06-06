import unittest
import os
import tempfile
import shutil
import zipfile
from unittest.mock import patch, MagicMock

# Import the BackupManager class
from quicksave.backup_manager import BackupManager


class TestBackupManager(unittest.TestCase):
    """Test the BackupManager class functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_dir, "source")
        self.backup_dir = os.path.join(self.temp_dir, "backups")

        # Create the source directory with some test files
        os.makedirs(self.source_dir)
        with open(os.path.join(self.source_dir, "test_file1.txt"), "w") as f:
            f.write("Test content 1")
        with open(os.path.join(self.source_dir, "test_file2.txt"), "w") as f:
            f.write("Test content 2")

        # Create the backup directory
        os.makedirs(self.backup_dir)

        # Create a BackupManager instance
        self.backup_manager = BackupManager()

    def tearDown(self):
        """Clean up test environment after each test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_is_s3_path(self):
        """Test the is_s3_path method."""
        self.assertTrue(self.backup_manager.is_s3_path("s3://my-bucket/path"))
        self.assertFalse(self.backup_manager.is_s3_path("/local/path"))
        self.assertFalse(self.backup_manager.is_s3_path("http://example.com"))

    def test_parse_s3_path(self):
        """Test the parse_s3_path method."""
        # Test with path containing key
        bucket, key = self.backup_manager.parse_s3_path("s3://my-bucket/my/path")
        self.assertEqual(bucket, "my-bucket")
        self.assertEqual(key, "my/path")

        # Test with bucket-only path
        bucket, key = self.backup_manager.parse_s3_path("s3://my-bucket")
        self.assertEqual(bucket, "my-bucket")
        self.assertEqual(key, "")

    def test_verify_directories_local(self):
        """Test verifying local directories."""
        # Test with valid directories
        success, _ = self.backup_manager.verify_directories(self.source_dir, self.backup_dir)
        self.assertTrue(success)

        # Test with non-existent source directory
        non_existent_dir = os.path.join(self.temp_dir, "non_existent")
        success, error_message = self.backup_manager.verify_directories(non_existent_dir, self.backup_dir)
        self.assertFalse(success)
        self.assertIn("does not exist", error_message)

    @patch('boto3.client')
    def test_verify_directories_s3(self, mock_boto3_client):
        """Test verifying directories with S3 backup directory."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        # Mock successful bucket check
        mock_s3_client.head_bucket.return_value = {}

        # Test verification with S3 backup directory
        success, _ = self.backup_manager.verify_directories(self.source_dir, "s3://my-bucket/backups")
        self.assertTrue(success)

        # Check that the head_bucket method was called with the right arguments
        mock_s3_client.head_bucket.assert_called_with(Bucket="my-bucket")

        # Mock bucket not found
        mock_s3_client.head_bucket.side_effect = Exception("Bucket not found")
        success, error_message = self.backup_manager.verify_directories(self.source_dir, "s3://non-existent-bucket/backups")
        self.assertFalse(success)
        self.assertIn("Error connecting to S3", error_message)

    def test_create_backup_local(self):
        """Test creating a backup to a local directory."""
        # Create a backup
        source_name = os.path.basename(self.source_dir)
        snapshot_name = "test_snapshot"
        backup_path = self.backup_manager.create_backup(self.source_dir, self.backup_dir, snapshot_name)

        # Check that the backup file exists
        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(backup_path.endswith(f"{source_name}_{snapshot_name}.zip"))

        # Check the contents of the backup
        with zipfile.ZipFile(backup_path, "r") as zip_file:
            file_list = zip_file.namelist()
            self.assertIn("test_file1.txt", file_list)
            self.assertIn("test_file2.txt", file_list)

            # Check file contents
            self.assertEqual(zip_file.read("test_file1.txt").decode(), "Test content 1")
            self.assertEqual(zip_file.read("test_file2.txt").decode(), "Test content 2")

    @patch('boto3.client')
    def test_create_backup_s3(self, mock_boto3_client):
        """Test creating a backup to an S3 bucket."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client

        # Create a backup
        source_name = os.path.basename(self.source_dir)
        snapshot_name = "test_snapshot"

        with patch.object(self.backup_manager, '_cleanup_temp_files') as mock_cleanup:
            backup_path = self.backup_manager.create_backup(self.source_dir, "s3://my-bucket/backups", snapshot_name)

            # Check that the backup path is correctly formatted
            self.assertTrue(backup_path.startswith("s3://my-bucket/backups/"))
            self.assertTrue(backup_path.endswith(f"{source_name}_{snapshot_name}.zip"))

            # Check that upload_file was called correctly
            mock_s3_client.upload_file.assert_called()

            # Check that cleanup was called
            mock_cleanup.assert_called()

    def test_list_snapshots_local(self):
        """Test listing snapshots from a local backup directory."""
        # Create a backup to generate a snapshot
        source_name = os.path.basename(self.source_dir)

        # Create snapshot files with proper timestamp format (YYYY-MM-DD_HH-MM-SS)
        timestamp1 = "2023-01-01_12-00-00"
        timestamp2 = "2023-01-02_12-00-00"

        # Manually create backup files to avoid actual backup creation
        backup_file1 = os.path.join(self.backup_dir, f"{source_name}_{timestamp1}.zip")
        backup_file2 = os.path.join(self.backup_dir, f"{source_name}_{timestamp2}_tag.zip")

        # Create empty zip files
        with zipfile.ZipFile(backup_file1, 'w') as _:
            pass
        with zipfile.ZipFile(backup_file2, 'w') as _:
            pass

        # List the snapshots
        snapshots = self.backup_manager.list_snapshots(self.backup_dir, source_name)

        # Check the snapshots
        self.assertEqual(len(snapshots), 2)

        # Check snapshot details (filename, timestamp, tag)
        snapshots_info = [(filename, timestamp, tag) for filename, timestamp, tag in snapshots]

        # Verify snapshot1 (no tag)
        snapshot1_info = next((info for info in snapshots_info if timestamp1 in info[1]), None)
        self.assertIsNotNone(snapshot1_info)
        self.assertEqual(snapshot1_info[1], timestamp1)  # Timestamp
        self.assertIsNone(snapshot1_info[2])     # No tag

        # Verify snapshot2 (with tag)
        snapshot2_info = next((info for info in snapshots_info if timestamp2 in info[1]), None)
        self.assertIsNotNone(snapshot2_info)
        self.assertEqual(snapshot2_info[1], timestamp2)  # Timestamp
        self.assertEqual(snapshot2_info[2], "tag")  # Tag


if __name__ == "__main__":
    unittest.main()
