from argparse import ArgumentParser
from .config import Config
from .backup_manager import BackupManager
from .version import __version__
import os
import sys
import datetime
import copy

argument_parser = ArgumentParser(
    prog="quicksave",
    description="A command line tool for saving snapshots of game saves.",
)
argument_parser.add_argument('-v', '--version', action='store_true', help='show program version')

# Add subparsers for commands
subparsers = argument_parser.add_subparsers(dest='command', help='Commands')

# Register command
register_parser = subparsers.add_parser('register', help='Register a new game save directory')
register_parser.add_argument('game', help='Name of the game')
register_parser.add_argument('-s', '--save-dir', required=True, help='Path to the save directory')
register_parser.add_argument('-b', '--backup-dir', required=True, help='Path to the backup directory')
register_parser.add_argument('-a', '--alias', action='append', help='Alias for the game, can be used multiple times')

# Update command
update_parser = subparsers.add_parser('update', help='Update an existing game configuration')
update_parser.add_argument('game', help='Name or alias of the game to update')
update_parser.add_argument('-s', '--save-dir', help='New path to the save directory')
update_parser.add_argument('-b', '--backup-dir', help='New path to the backup directory')
update_parser.add_argument('-a', '--alias', action='append', help='Aliases to add (can be used multiple times)')
update_parser.add_argument('-r', '--remove-alias', action='append', help='Aliases to remove (can be used multiple times)')

# Deregister command
deregister_parser = subparsers.add_parser('deregister', help='Remove a game from configuration')
deregister_parser.add_argument('game', help='Name of the game to deregister')

# Save command
save_parser = subparsers.add_parser('save', help='Save a snapshot of the registered game save')
save_parser.add_argument('game', help='Name or alias of the game to save')
save_parser.add_argument('-t', '--tag', help='Optional tag to add to the snapshot name')
save_parser.add_argument('-b', '--backup-dir', help='Override the backup directory for this snapshot')

# List command
list_parser = subparsers.add_parser('list', help='List all registered games')
list_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed information including save and backup directories')

# Show command
show_parser = subparsers.add_parser('show', help='List saved snapshots for a game')
show_parser.add_argument('game', help='Name or alias of the game to show snapshots for')
show_parser.add_argument('-b', '--backup-dir', help='Override the backup directory for listing snapshots')

def main():
    # Handle no arguments case - print usage and exit
    if len(sys.argv) == 1:
        argument_parser.print_help()
        return

    # Parse command line arguments
    args = argument_parser.parse_args()

    config = Config()
    backup_manager = BackupManager()

    # Handle version flag if present
    if hasattr(args, 'version') and args.version:
        print(f"quicksave version {__version__}")
        return

    # Handle commands
    if hasattr(args, 'command') and args.command:
        if args.command == 'register':
            # Validate directories
            save_dir = os.path.abspath(args.save_dir)

            # Handle backup_dir - preserve S3 URL format if present
            if args.backup_dir.startswith('s3://'):
                backup_dir = args.backup_dir
            else:
                backup_dir = os.path.abspath(args.backup_dir)

            # Verify directories
            success, error_message = backup_manager.verify_directories(save_dir, backup_dir)
            if not success:
                print(error_message)
                return

            # Register the game
            success, valid_aliases, rejected_aliases = config.add_game(args.game, save_dir, backup_dir, args.alias)

            if not success:
                print(f"Error: Game name '{args.game}' is already in use as a game name or alias.")
                return

            print(f"Registered game: {args.game}")
            print(f"Save directory: {save_dir}")
            print(f"Backup directory: {backup_dir}")
            if valid_aliases:
                print(f"Aliases: {', '.join(valid_aliases)}")
            if rejected_aliases:
                print(f"Warning: The following aliases were rejected because they're already in use: {', '.join(rejected_aliases)}")

        elif args.command == 'update':
            # Get game info
            original_game_info = config.get_game(args.game)
            if not original_game_info:
                print(f"Error: Game '{args.game}' not found.")
                return

            # Create a deep copy to avoid modifying the original object
            game_info = copy.deepcopy(original_game_info)

            # Update save directory if provided
            if args.save_dir:
                save_dir = os.path.abspath(args.save_dir)
                game_info["save_dir"] = save_dir

            # Update backup directory if provided
            if args.backup_dir:
                if args.backup_dir.startswith('s3://'):
                    backup_dir = args.backup_dir
                else:
                    backup_dir = os.path.abspath(args.backup_dir)
                game_info["backup_dir"] = backup_dir

            # Update aliases if provided
            if args.alias or args.remove_alias:
                success, actual_name, valid_aliases, rejected_aliases = config.update_game(args.game, game_info, args.alias, args.remove_alias)
            else:
                # No new aliases to add or remove
                success, actual_name, valid_aliases, rejected_aliases = config.update_game(args.game, game_info)

            if success:
                print(f"Updated game: {actual_name}")
                if args.save_dir:
                    print(f"New save directory: {save_dir}")
                if args.backup_dir:
                    print(f"New backup directory: {backup_dir}")
                if valid_aliases:
                    print(f"Added aliases: {', '.join(valid_aliases)}")
                if rejected_aliases:
                    print(f"Warning: The following aliases were rejected because they're already in use: {', '.join(rejected_aliases)}")
                if args.remove_alias:
                    print(f"Removed aliases: {', '.join(args.remove_alias)}")
            else:
                print(f"Error: Failed to update game '{args.game}'.")

        elif args.command == 'deregister':
            # Remove game configuration
            success = config.remove_game(args.game)
            if success:
                print(f"Deregistered game: {args.game}")
            else:
                print(f"Error: Game '{args.game}' not found.")

        elif args.command == 'save':
            # Get game info
            game_info = config.get_game(args.game)
            if not game_info:
                print(f"Error: Game '{args.game}' not found.")
                return

            # Extract directories from game info
            save_dir = game_info.get("save_dir")
            backup_dir = args.backup_dir if args.backup_dir else game_info.get("backup_dir")

            # Make sure save directory exists
            if not os.path.exists(save_dir):
                print(f"Error: Save directory '{save_dir}' doesn't exist.")
                return

            # Create timestamp for snapshot
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if args.tag:
                snapshot_name = f"{timestamp}_{args.tag}"
            else:
                snapshot_name = timestamp

            try:
                # Create the backup
                backup_path = backup_manager.create_backup(save_dir, backup_dir, snapshot_name)
                print(f"Saving snapshot for game: {args.game}")
                if args.tag:
                    print(f"Using tag: {args.tag}")
                print(f"Snapshot saved to: {backup_path}")
            except Exception as e:
                print(f"Error creating backup: {e}")
                return

        elif args.command == 'list':
            games = config.get_games()
            if not games:
                print("No games registered.")
                return

            print("Registered games:")
            for name, game_info in games.items():
                aliases = game_info.get("aliases", [])
                if aliases:
                    alias_str = ", ".join(aliases)
                    print(f"- {name} (aliases: {alias_str})")
                else:
                    print(f"- {name}")
                if args.verbose:
                    save_dir = game_info.get("save_dir", "N/A")
                    backup_dir = game_info.get("backup_dir", "N/A")
                    print(f"  Save directory: {save_dir}")
                    print(f"  Backup directory: {backup_dir}")

        elif args.command == 'show':
            # Get game info
            game_info = config.get_game(args.game)
            if not game_info:
                print(f"Error: Game '{args.game}' not found.")
                return

            # Extract directories from game info
            save_dir = game_info.get("save_dir")
            backup_dir = args.backup_dir if args.backup_dir else game_info.get("backup_dir")
            source_name = os.path.basename(save_dir)

            # Get list of snapshots
            snapshots = backup_manager.list_snapshots(backup_dir, source_name)

            if not snapshots:
                print(f"No snapshots found for game: {args.game}")
                return

            print(f"Snapshots for game: {args.game}")
            for snapshot in snapshots:
                filename, timestamp, tag = snapshot
                if tag:
                    print(f"- {timestamp} (tag: {tag})")
                else:
                    print(f"- {timestamp}")

if __name__ == "__main__":
    main()
