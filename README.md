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
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/scripts/myrient_dl.sh) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

**Windows:**
```powershell
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/scripts/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml' }"
```

**Python (Cross-platform):**
```bash
python <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/scripts/myrient_dl.py) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

## Installation & Distribution

### AppImage (Recommended for Linux)
Download the latest AppImage from [Releases](https://github.com/mike94100/myrient-dl-script/releases):

```bash
# Make executable and run
chmod +x MyrientDL.AppImage
./MyrientDL.AppImage gui  # Launch GUI
./MyrientDL.AppImage download collections/sample/sample.toml  # CLI usage
```

### From Source
```bash
# Clone and install
git clone https://github.com/mike94100/myrient-dl-script.git
cd myrient-dl-script
pip install -e .

# Use commands
myrient-dl gui                    # Launch GUI
myrient-dl download collections/sample/sample.toml
myrient-dl generate-all collections/sample/sample.toml
```

### Building AppImage
```bash
# Dependencies are included (appimagetool downloaded automatically)
# Build AppImage
python build_appimage.py
```

See [full documentation](docs/README.md) for detailed installation instructions, configuration, and advanced usage examples.

## Requirements

- **Python 3.8+** (3.11+ recommended for built-in TOML support)
- **Wget** (install on Windows, commonly available on Linux/macOS)

## AI Developed

Built with AI assistance given my limited programming knowledge. Because of this, I would not recommend using this for any more than a test use case. This is meant as a proof-of-concept for code-as-configuration ROM collections that can be easily downloaded to any device by any user.
