import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Manages the configuration for the Quicksave application."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "quicksave.yaml"
        self.config = self._load_config()

    def _get_config_dir(self) -> Path:
        """Get the OS-specific configuration directory."""
        if os.name == "nt":  # Windows
            config_dir = Path(os.environ.get("APPDATA")) / "Quicksave"
        elif os.name == "posix":  # macOS / Linux
            # macOS: ~/Library/Application Support/Quicksave
            if os.uname().sysname == "Darwin":
                config_dir = Path.home() / "Library" / "Application Support" / "Quicksave"
            # Linux: ~/.config/quicksave
            else:
                xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
                if xdg_config_home:
                    config_dir = Path(xdg_config_home) / "quicksave"
                else:
                    config_dir = Path.home() / ".config" / "quicksave"
        else:
            # Fallback to home directory
            config_dir = Path.home() / ".quicksave"

        # Ensure the directory exists
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the YAML file."""
        if not self.config_file.exists():
            # Create a default config if none exists
            default_config = {
                "version": "0.1.0",
                "games": {}
            }
            self._save_config(default_config)
            return default_config

        with open(self.config_file, "r") as file:
            try:
                return yaml.safe_load(file) or {}
            except yaml.YAMLError:
                # If the file is corrupted, return an empty config
                return {"version": "0.1.0", "games": {}}

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to the YAML file."""
        with open(self.config_file, "w") as file:
            yaml.dump(config, file)

    def save(self) -> None:
        """Save the current configuration."""
        self._save_config(self.config)

    def get_games(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered games."""
        return self.config.get("games", {})

    def get_game(self, name_or_alias: str) -> Optional[Dict[str, Any]]:
        """Get a game by name or alias."""
        games = self.get_games()

        # Direct name lookup
        if name_or_alias in games:
            return games[name_or_alias]

        # Check aliases
        for name, game_info in games.items():
            aliases = game_info.get("aliases", [])
            if isinstance(aliases, list) and name_or_alias in aliases:
                return game_info

        return None

    def add_game(self, name: str, save_dir: str, backup_dir: str, alias: Optional[str] = None) -> None:
        """Register a new game."""
        if "games" not in self.config:
            self.config["games"] = {}

        self.config["games"][name] = {
            "save_dir": save_dir,
            "backup_dir": backup_dir,
            "aliases": []
        }

        if alias:
            self.config["games"][name]["aliases"] = [alias]

        self.save()

    def add_alias(self, name: str, alias: str) -> bool:
        """Add an alias to an existing game.

        Args:
            name: Name of the game
            alias: Alias to add

        Returns:
            bool: True if successful, False if game not found
        """
        games = self.get_games()
        if name not in games:
            return False

        if "aliases" not in games[name]:
            games[name]["aliases"] = []

        if alias not in games[name]["aliases"]:
            games[name]["aliases"].append(alias)
            self.save()

        return True
