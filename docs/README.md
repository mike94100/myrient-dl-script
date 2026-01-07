# Myrient Downloader Documentation

## Overview

Myrient Downloader is a tool for downloading ROM and BIOS files from Myrient collections. It supports batch downloads with progress tracking and resume functionality.

## Requirements

- **Rust toolchain** (stable) — required to build the GUI and crates
- **Wget** (optional) — required by some downloader scripts
- **Python 3.8+** only if you plan to run the optional `bin/myrient_dl.py` downloader script

## Build

### From Source

```bash
# Clone and build the workspace
git clone https://github.com/mike94100/myrient-dl-script.git
cd myrient-dl-script
cargo build --workspace
```

Run the GUI or individual crates with `cargo run -p <crate-name>` or see the packaging instructions below.

### Option 2: Use Standalone Scripts

The standalone scripts are available in the `bin/` directory:

**Python:**
```python
python bin/myrient_dl.py download collections/sample/sample.toml
```

**Bash:**
```bash
bash bin/myrient_dl.sh collections/sample/sample.toml
```

**PowerShell:**
```powershell
.\bin\myrient_dl.ps1 -CollectionUrl collections/sample/sample.toml
```

## Run

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

### Standalone Scripts

The standalone scripts are available in the `bin/` directory:

```bash
# Bash script
./bin/myrient_dl.sh collections/sample/sample.toml

# Python script
python bin/myrient_dl.py collections/sample/sample.toml
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
   # Build and run the Rust generator crate to generate URL files and README
   cargo run -p myrient-gen -- generate-urls collection.toml
   cargo run -p myrient-gen -- generate-readme collection.toml

   # Generate both URLs and README
   cargo run -p myrient-gen -- generate-all collection.toml
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

### Build & Test (Rust)

```bash
# Build the workspace
cargo build --workspace

# Run unit tests for workspace
cargo test --workspace
```

### Code Quality

```bash
# Format Rust code
cargo fmt --all

# Lint with clippy
cargo clippy --workspace --all-targets -- -D warnings
```

## Architecture

- `src-tauri/` - Tauri GUI (Rust)
- `crates/` - Rust helper crates and CLI tools
- `collections/` - TOML configuration files
- `urls/` - URL lists for downloads
- `bin/` - Legacy executable scripts (Python/Bash/PowerShell)
- `docs/` - Documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run code quality checks
6. Submit a pull request

## License

GNU General Public License v3.0 - see LICENSE file for details.
