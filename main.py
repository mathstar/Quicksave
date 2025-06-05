from argparse import ArgumentParser

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
register_parser.add_argument('-a', '--alias', help='Optional alias for the game')

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

    # Handle version flag if present
    if hasattr(args, 'version') and args.version:
        print("quicksave version 0.1.0")

    # Handle commands
    if hasattr(args, 'command') and args.command:
        if args.command == 'register':
            print(f"Registering game: {args.name}")
            print(f"Save directory: {args.save_dir}")
            print(f"Backup directory: {args.backup_dir}")
            if args.alias:
                print(f"Alias: {args.alias}")
        elif args.command == 'save':
            print(f"Saving snapshot for game: {args.game}")
            if hasattr(args, 'tag') and args.tag:
                print(f"Using tag: {args.tag}")
        elif args.command == 'list':
            print("Registered games:")
            # This would be populated from actual storage in a real implementation
            print("- Skyrim (alias: sky)")
            print("- Fallout 4 (alias: fo4)")
            print("- Stardew Valley (alias: stardew)")
        elif args.command == 'show':
            print(f"Snapshots for game: {args.game}")
            # This would be populated from actual storage in a real implementation
            print("- 2025-06-01_12-30-45")
            print("- 2025-06-02_08-15-22_boss-fight")
            print("- 2025-06-04_19-45-10_before-final-quest")

if __name__ == "__main__":
    main()
