# Quicksave

Quicksave is a command line tool for saving snapshots of game saves. It helps gamers create and manage backup snapshots of their game save files, with support for both local backups and AWS S3 cloud storage.

## Features

- Register any game's save directory for easy backup
- Create snapshots of game saves with timestamps and optional tags
- Support for both local and S3 cloud storage backups
- Simple command line interface

## Installation

Quicksave requires Python 3.13 or later.

```bash
pip install quicksave-tool
```

## Usage

### Basic Commands

```bash
# Show version
quicksave --version

# Register a new game
quicksave register "Game Name" --save-dir "/path/to/game/saves" --backup-dir "/path/to/backups"

# Create a snapshot
quicksave save "Game Name"

# Create a snapshot with a tag
quicksave save "Game Name" --tag "before_boss_fight"

# List registered games
quicksave list

# List game backups
quicksave show "Game Name"
```

### Command Reference

#### Register a game
```
quicksave register GAME -s SAVE_DIR -b BACKUP_DIR [-a ALIAS]
```

#### Update a game configuration
```
quicksave update GAME [-s SAVE_DIR] [-b BACKUP_DIR] [-a ALIAS] [-r REMOVE_ALIAS]
```

#### Remove a game
```
quicksave deregister GAME
```

#### Create a save snapshot
```
quicksave save GAME [-t TAG] [-b BACKUP_DIR]
```

#### List registered games
```
quicksave list [-v]
```

#### Show game snapshots
```
quicksave show GAME [-b BACKUP_DIR]
```

## Development

### Setup Development Environment

1. Clone the repository
```bash
git clone https://github.com/mathiasstaricka/quicksave.git
cd quicksave
```

2. Set up virtual environment, install, and run
```bash
uv run quicksave
```

### Running Tests

```bash
uv run pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
