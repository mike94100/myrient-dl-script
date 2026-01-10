# Myrient ROM Downloader

A modern, cross-platform ROM collection and downloading system for the Myrient site with decentralized collection hosting.

## Why

This project treats ROM collections as "code" - small, versionable TOML configuration & URL list files that define collections of games. This approach enables:

- **No File Hosting**: All files are downloaded from Myrient (or other source)
- **Authenticity**: Myrient provides verified, hashed ROMs from trusted sources
- **Space-Efficient**: Store collection definitions as text not ROM files
- **Easy Sharing**: Share curated collections without hosting any files
- **Customization**: Pre-define specific game lists, not just on-the-fly filtering
- **Version Control**: Track changes to your collection over time
- **Auto-Documentation**: Generate comprehensive collection READMEs
- **Easy Downloads**: One-command downloads from any hosted collection via Python, Bash, or PowerShell

## Quick Start

Test with the included [sample collection](collections/sample/README.md):

**Linux/macOS:**
```bash
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/bin/myrient_dl.sh) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

**Windows:**
```powershell
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/bin/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml' }"
```

**Python (Cross-platform):**
```bash
python <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/bin/myrient_dl.py) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

## Installation

## Build

### From Source (Rust workspace)
```bash
# Clone and build (builds GUI and crates)
git clone https://github.com/mike94100/myrient-dl-script.git
cd myrient-dl-script
cargo build --workspace
```

See [full documentation](docs/README.md) for detailed build and packaging instructions.

## Requirements

- **Rust** — required to build the GUI and crates
- **Wget** — required by some downloader scripts
- **Python 3.8+** (optional) — required only to run `bin/myrient_dl.py`

## AI Developed

Built with AI assistance given my limited programming knowledge. Because of this, I would not recommend using this for any more than a test use case. This is meant as a proof-of-concept for code-as-configuration ROM collections that can be easily downloaded to any device by any user.
