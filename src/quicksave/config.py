import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .version import __version__


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
                "version": __version__,
                "games": {}
            }
            self._save_config(default_config)
            return default_config

        with open(self.config_file, "r") as file:
            try:
                return yaml.safe_load(file) or {}
            except yaml.YAMLError:
                # If the file is corrupted, return an empty config
                return {"version": __version__, "games": {}}

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

    def add_game(self, name: str, save_dir: str, backup_dir: str, aliases: Optional[list] = None) -> tuple[bool, list, list]:
        """Register a new game.

        Args:
            name: Name of the game
            save_dir: Path to the save directory
            backup_dir: Path to the backup directory
            aliases: Optional list of aliases for the game

        Returns:
            tuple: (success, valid_aliases, rejected_aliases)
        """
        # Check if name is already in use
        if name in self.get_games():
            return False, [], aliases or []

        # Check if name is already an alias for another game
        if self.is_alias_in_use(name):
            return False, [], aliases or []

        # Validate aliases
        valid_aliases = []
        rejected_aliases = []

        if aliases and isinstance(aliases, list):
            for alias in aliases:
                if self.is_alias_in_use(alias):
                    rejected_aliases.append(alias)
                else:
                    valid_aliases.append(alias)

        # Create the game in config
        if "games" not in self.config:
            self.config["games"] = {}

        self.config["games"][name] = {
            "save_dir": save_dir,
            "backup_dir": backup_dir,
            "aliases": valid_aliases
        }

        self.save()

        return True, valid_aliases, rejected_aliases

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

    def update_game(self, name_or_alias: str, game_info: dict, new_aliases: Optional[list] = None,
                    remove_aliases: Optional[list] = None) -> tuple[bool, str, list, list]:
        """Update an existing game's configuration.

        Args:
            name_or_alias: Name or alias of the game to update
            game_info: Updated game information dictionary
            new_aliases: Optional list of new aliases to add
            remove_aliases: Optional list of aliases to remove

        Returns:
            tuple: (success, game_name, valid_aliases, rejected_aliases)
        """
        if "games" not in self.config:
            self.config["games"] = {}

        # Find the actual game name
        actual_name = None

        # Direct name lookup
        if name_or_alias in self.config["games"]:
            actual_name = name_or_alias
        else:
            # Check aliases
            for name, existing_game_info in self.config["games"].items():
                aliases = existing_game_info.get("aliases", [])
                if isinstance(aliases, list) and name_or_alias in aliases:
                    actual_name = name
                    break

        if not actual_name:
            return False, "", [], []

        # Get current aliases
        current_aliases = set(game_info.get("aliases", []))

        # Remove aliases if requested
        if remove_aliases:
            for alias in remove_aliases:
                if alias in current_aliases:
                    current_aliases.remove(alias)

        valid_aliases = []
        rejected_aliases = []

        # Handle new aliases if provided
        if new_aliases:
            for alias in new_aliases:
                if self.is_alias_in_use(alias, actual_name):
                    rejected_aliases.append(alias)
                else:
                    valid_aliases.append(alias)
                    current_aliases.add(alias)

        # Update the aliases in the game info
        game_info["aliases"] = list(current_aliases)

        # Update the game configuration
        self.config["games"][actual_name] = game_info
        self.save()

        return True, actual_name, valid_aliases, rejected_aliases

    def remove_game(self, name_or_alias: str) -> bool:
        """Remove a game from configuration by name or alias.

        Args:
            name_or_alias: Name or alias of the game to remove

        Returns:
            bool: True if the game was found and removed, False otherwise
        """
        games = self.get_games()

        # Direct name lookup
        if name_or_alias in games:
            del self.config["games"][name_or_alias]
            self.save()
            return True

        # Check aliases
        for name, game_info in list(games.items()):
            aliases = game_info.get("aliases", [])
            if isinstance(aliases, list) and name_or_alias in aliases:
                del self.config["games"][name]
                self.save()
                return True

        return False

    def is_alias_in_use(self, alias: str, exclude_game: Optional[str] = None) -> bool:
        """Check if an alias is already in use by another game.

        Args:
            alias: The alias to check
            exclude_game: Optional game name to exclude from the check

        Returns:
            bool: True if the alias is in use by another game, False otherwise
        """
        games = self.get_games()

        # Check if the alias is actually a game name
        if alias in games and alias != exclude_game:
            return True

        # Check all games for the alias
        for name, game_info in games.items():
            if name == exclude_game:
                continue

            aliases = game_info.get("aliases", [])
            if alias in aliases:
                return True

        return False

    def validate_aliases(self, aliases: list, exclude_game: Optional[str] = None) -> list:
        """Validate a list of aliases and return only the unique ones.

        Args:
            aliases: List of aliases to validate
            exclude_game: Optional game name to exclude from the uniqueness check

        Returns:
            list: List of valid aliases (those not in use by other games)
        """
        if not aliases:
            return []

        valid_aliases = []
        for alias in aliases:
            if not self.is_alias_in_use(alias, exclude_game):
                valid_aliases.append(alias)

        return valid_aliases
