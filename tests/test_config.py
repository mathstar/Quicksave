import unittest
import os
import tempfile
import shutil
from pathlib import Path

# Import the Config class
from quicksave.config import Config
from quicksave import __version__


class TestConfig(unittest.TestCase):
    """Test the Config class functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for config files
        self.temp_dir = tempfile.mkdtemp()
        # Set environment variables to control config location
        os.environ["XDG_CONFIG_HOME"] = self.temp_dir
        # Override the _get_config_dir method to use our temp directory
        self.original_get_config_dir = Config._get_config_dir
        Config._get_config_dir = lambda self: Path(tempfile.mkdtemp())
        # Create a test instance
        self.config = Config()

    def tearDown(self):
        """Clean up test environment after each test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Restore original method
        Config._get_config_dir = self.original_get_config_dir

    def test_init_creates_default_config(self):
        """Test that initialization creates a default config."""
        self.assertIsInstance(self.config.config, dict)
        self.assertIn("version", self.config.config)
        self.assertIn("games", self.config.config)
        self.assertEqual(self.config.config["version"], __version__)
        self.assertIsInstance(self.config.config["games"], dict)

    def test_add_game(self):
        """Test adding a game to the config."""
        # Add a game
        success, valid_aliases, rejected_aliases = self.config.add_game(
            "TestGame", "/path/to/saves", "/path/to/backups", ["test_alias"]
        )

        # Check return values
        self.assertTrue(success)
        self.assertIn("test_alias", valid_aliases)
        self.assertEqual(len(rejected_aliases), 0)

        # Check that the game was added to the config
        games = self.config.get_games()
        self.assertIn("TestGame", games)
        self.assertEqual(games["TestGame"]["save_dir"], "/path/to/saves")
        self.assertEqual(games["TestGame"]["backup_dir"], "/path/to/backups")
        self.assertEqual(games["TestGame"]["aliases"], ["test_alias"])

    def test_add_game_with_duplicate_name(self):
        """Test adding a game with a name that already exists."""
        # Add a game
        self.config.add_game("TestGame", "/path/to/saves", "/path/to/backups")

        # Try to add a game with the same name
        success, valid_aliases, rejected_aliases = self.config.add_game(
            "TestGame", "/other/path", "/other/backups", ["alias"]
        )

        # Check that the operation failed
        self.assertFalse(success)
        self.assertEqual(len(valid_aliases), 0)
        self.assertIn("alias", rejected_aliases)

    def test_add_game_with_duplicate_alias(self):
        """Test adding a game with an alias that already exists."""
        # Add a game with an alias
        self.config.add_game("Game1", "/path1", "/backup1", ["shared_alias"])

        # Try to add another game with the same alias
        success, valid_aliases, rejected_aliases = self.config.add_game(
            "Game2", "/path2", "/backup2", ["shared_alias", "unique_alias"]
        )

        # Check that the game was added but the duplicate alias was rejected
        self.assertTrue(success)
        self.assertIn("unique_alias", valid_aliases)
        self.assertNotIn("shared_alias", valid_aliases)
        self.assertIn("shared_alias", rejected_aliases)

    def test_get_game_by_name(self):
        """Test getting a game by its name."""
        # Add a game
        self.config.add_game("TestGame", "/path/to/saves", "/path/to/backups", ["alias"])

        # Get the game by name
        game_info = self.config.get_game("TestGame")

        # Check the game info
        self.assertIsNotNone(game_info)
        self.assertEqual(game_info["save_dir"], "/path/to/saves")
        self.assertEqual(game_info["backup_dir"], "/path/to/backups")

    def test_get_game_by_alias(self):
        """Test getting a game by its alias."""
        # Add a game with aliases
        self.config.add_game("TestGame", "/path/to/saves", "/path/to/backups", ["alias1", "alias2"])

        # Get the game by alias
        game_info = self.config.get_game("alias1")

        # Check the game info
        self.assertIsNotNone(game_info)
        self.assertEqual(game_info["save_dir"], "/path/to/saves")
        self.assertEqual(game_info["backup_dir"], "/path/to/backups")

    def test_remove_game(self):
        """Test removing a game from the config."""
        # Add a game
        self.config.add_game("TestGame", "/path/to/saves", "/path/to/backups")

        # Remove the game
        success = self.config.remove_game("TestGame")

        # Check that the operation succeeded
        self.assertTrue(success)

        # Check that the game was removed
        self.assertNotIn("TestGame", self.config.get_games())

    def test_remove_nonexistent_game(self):
        """Test removing a game that doesn't exist."""
        # Try to remove a game that doesn't exist
        success = self.config.remove_game("NonexistentGame")

        # Check that the operation failed
        self.assertFalse(success)

    def test_update_game(self):
        """Test updating a game's configuration."""
        # Add a game
        self.config.add_game("TestGame", "/path/to/saves", "/path/to/backups")

        # Update the game
        game_info = self.config.get_game("TestGame")
        game_info["save_dir"] = "/new/path"
        success, actual_name, valid_aliases, rejected_aliases = self.config.update_game("TestGame", game_info)

        # Check that the operation succeeded
        self.assertTrue(success)
        self.assertEqual(actual_name, "TestGame")

        # Check that the game was updated
        updated_game = self.config.get_game("TestGame")
        self.assertEqual(updated_game["save_dir"], "/new/path")


if __name__ == "__main__":
    unittest.main()
