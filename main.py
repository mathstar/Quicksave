from argparse import ArgumentParser
from config import Config
from backup_manager import BackupManager
import os
import datetime

argument_parser = ArgumentParser(
    prog="quicksave",
    usage="quicksave [-h] [--version]",
    description="A command line tool for saving snapshots of game saves.",
)
argument_parser.add_argument('--version', action='store_true', help='show program version')

# Add subparsers for commands
subparsers = argument_parser.add_subparsers(dest='command', help='Commands')

# Register command
register_parser = subparsers.add_parser('register', help='Register a new game save directory')
register_parser.add_argument('-n', '--name', required=True, help='Name of the game')
register_parser.add_argument('-s', '--save-dir', required=True, help='Path to the save directory')
register_parser.add_argument('-b', '--backup-dir', required=True, help='Path to the backup directory')
register_parser.add_argument('-a', '--alias', action='append', help='Alias for the game, can be used multiple times')

# Save command
save_parser = subparsers.add_parser('save', help='Save a snapshot of the registered game save')
save_parser.add_argument('game', help='Name or alias of the game to save')
save_parser.add_argument('-t', '--tag', help='Optional tag to add to the snapshot name')
save_parser.add_argument('-b', '--backup-dir', help='Override the backup directory for this snapshot')

# List command
list_parser = subparsers.add_parser('list', help='List all registered games')

# Show command
show_parser = subparsers.add_parser('show', help='List saved snapshots for a game')
show_parser.add_argument('game', help='Name or alias of the game to show snapshots for')
show_parser.add_argument('-b', '--backup-dir', help='Override the backup directory for listing snapshots')

def main():
    # Parse command line arguments
    args = argument_parser.parse_args()

    config = Config()
    backup_manager = BackupManager()

    # Handle version flag if present
    if hasattr(args, 'version') and args.version:
        print("quicksave version 0.1.0")
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
            config.add_game(args.name, save_dir, backup_dir, args.alias)
            print(f"Registered game: {args.name}")
            print(f"Save directory: {save_dir}")
            print(f"Backup directory: {backup_dir}")
            if args.alias:
                print(f"Aliases: {', '.join(args.alias)}")

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
