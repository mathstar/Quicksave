from argparse import ArgumentParser
from config import Config
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

# List command
list_parser = subparsers.add_parser('list', help='List all registered games')

# Show command
show_parser = subparsers.add_parser('show', help='List saved snapshots for a game')
show_parser.add_argument('game', help='Name or alias of the game to show snapshots for')

def main():
    # Parse command line arguments
    args = argument_parser.parse_args()

    # Create config manager
    config = Config()

    # Handle version flag if present
    if hasattr(args, 'version') and args.version:
        print("quicksave version 0.1.0")
        return

    # Handle commands
    if hasattr(args, 'command') and args.command:
        if args.command == 'register':
            # Validate directories
            save_dir = os.path.abspath(args.save_dir)
            backup_dir = os.path.abspath(args.backup_dir)

            if not os.path.exists(save_dir):
                print(f"Error: Save directory '{save_dir}' does not exist.")
                return

            # Create backup directory if it doesn't exist
            if not os.path.exists(backup_dir):
                try:
                    os.makedirs(backup_dir)
                except OSError as e:
                    print(f"Error creating backup directory: {e}")
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

            # Create timestamp for snapshot
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if args.tag:
                snapshot_name = f"{timestamp}_{args.tag}"
            else:
                snapshot_name = timestamp

            # Here you would implement the actual backup functionality
            print(f"Saving snapshot for game: {args.game}")
            if args.tag:
                print(f"Using tag: {args.tag}")

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

            # Here you would implement functionality to list snapshots
            print(f"Snapshots for game: {args.game}")
            # This would be populated from actual storage in a real implementation
            print("- 2025-06-01_12-30-45")
            print("- 2025-06-02_08-15-22_boss-fight")
            print("- 2025-06-04_19-45-10_before-final-quest")

if __name__ == "__main__":
    main()
