# Myrient Downloader Documentation

## Overview

Myrient Downloader is a tool for downloading ROM and BIOS files from Myrient collections. It supports batch downloads with progress tracking and resume functionality.

## Requirements

- **Python 3.8+** (3.11+ recommended for built-in TOML support)
- **Wget** (install on Windows, commonly available on Linux/macOS)

## Installation

### Option 1: Install as Python Package (Recommended)

```bash
# Clone the repository
git clone https://github.com/mike94100/myrient-dl-script.git
cd myrient-dl-script

# Install in development mode
pip install -e .
```

Then use:
```bash
myrient-dl collections/sample/sample.toml
```

### Option 2: Use Legacy Scripts

The standalone scripts are available in the `scripts/` directory:

**Python:**
```bash
python scripts/myrient_dl.py download collections/sample/sample.toml
```

**Bash:**
```bash
bash scripts/myrient_dl.sh collections/sample/sample.toml
```

**PowerShell:**
```powershell
.\scripts\myrient_dl.ps1 -CollectionUrl collections/sample/sample.toml
```

### Using pip (once published)

```bash
pip install myrient-dl
```

## Usage

### Command Line

```bash
# Download from a collection
myrient-dl collections/1g1r/1g1r.toml

# Download to specific directory
myrient-dl collections/sample/sample.toml -o ~/roms

# Non-interactive mode
myrient-dl collections/all/all.toml --non-interactive

# Verbose logging
myrient-dl collections/1g1r/1g1r.toml --verbose
```

### Legacy Scripts

The legacy bash and Python scripts are still available in the `scripts/` directory:

```bash
# Bash script
./scripts/myrient_dl.sh collections/sample/sample.toml

# Python script
python scripts/myrient_dl.py collections/sample/sample.toml
```

### Advanced Usage

**Dry Runs:**
```bash
# Preview downloads
myrient-dl download collections/sample/sample.toml --non-interactive --dry-run

# Preview content generation
myrient-dl generate-all collections/sample/sample.toml --dry-run
```

### Creating Collections

1. **Copy and edit collection.template.toml**

2. **Generate Content**
   ```bash
   # Install the package first
   pip install -e .

   # Generate URL files by scraping Myrient
   myrient-dl generate-urls collection.toml

   # Generate README documentation
   myrient-dl generate-readme collection.toml

   # Generate both URLs and README
   myrient-dl generate-all collection.toml
   ```

3. [See provided collections](../collections/README.md)

## Configuration

Collections are defined using TOML configuration files. See the `collections/` directory for examples.

### Collection Structure

```toml
[roms.nes]
directory = "nes"
urllist = "urls/nes.txt"
extract = false

[roms.snes]
directory = "snes"
urllist = "urls/snes.txt"
extract = true

[bios.ps1]
directory = "ps1"
urllist = "urls/ps1.txt"
```

## Development

### Setup Development Environment

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black src/ scripts/

# Sort imports
isort src/ scripts/

# Type checking
mypy src/

# Linting
flake8 src/
```

## Architecture

- `src/myrient_dl/` - Main package
  - `cli.py` - Command-line interface
  - `core.py` - Core download functionality
  - `config.py` - Configuration handling
  - `utils/` - Utility modules
- `collections/` - TOML configuration files
- `urls/` - URL lists for downloads
- `scripts/` - Legacy executable scripts
- `tests/` - Unit tests
- `docs/` - Documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run code quality checks
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
