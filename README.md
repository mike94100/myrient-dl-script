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

### Download from Any Collection

**Linux/macOS:**
```bash
# Download sample collection
./myrient_dl.sh collections/sample/sample.toml

# Download from any hosted collection
./myrient_dl.sh https://example.com/my-collection.toml
```

**Windows:**
```powershell
# Download sample collection
.\myrient_dl.ps1 collections\sample\sample.toml

# Download from any hosted collection
.\myrient_dl.ps1 https://example.com/my-collection.toml
```

**Python (Cross-platform):**
```bash
# Download sample collection
python myrient_dl.py collections/sample/sample.toml

# Download to custom directory
python myrient_dl.py collections/sample/sample.toml --output ~/my-roms

# Download specific platforms
python myrient_dl.py collections/sample/sample.toml --platforms gb gba
```

## Run without Downloading

Run the scripts directly from the repository without downloading them first. The scripts will fetch and parse the TOML collection from the provided URL and allow interactive platform selection and output directory configuration.

**Linux/macOS:**
```bash
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.sh) https://example.com/my-collection.toml
```

**Python (Cross-platform):**
```bash
python3 <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) https://example.com/my-collection.toml
```

**Windows PowerShell:**
```powershell
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl 'https://example.com/my-collection.toml' }"
```

## Usage Guide

### Creating Collections

1. **Edit TOML Configuration**
   ```bash
   # Copy template to create new collection
   cp templates/collection.template.toml collections/my-collection.toml
   ```

2. **Generate Content**
   ```bash
   # Generate URL files by scraping Myrient
   python myrient_generator.py --gen-url collections/my-collection.toml

   # Generate README documentation
   python myrient_generator.py --gen-readme collections/my-collection.toml

   # Generate both concurrently
   python myrient_generator.py --gen-url --gen-readme collections/my-collection.toml
   ```

### Collection Examples

- **`collections/sample/`**: Small sample with Game Boy, GBA, GBC, and PS2 BIOS
- **`collections/1g1r/`**: 1 Game 1 ROM collection
- **`collections/all/`**: Complete collection

### Advanced Usage

**Interactive Downloads:**
```bash
# Interactive menu to select platforms
./myrient_dl.sh collections/sample/sample.toml

# Non-interactive with all platforms
./myrient_dl.sh collections/sample/sample.toml --non-interactive
```

**Dry Runs:**
```bash
# See what would be downloaded
python myrient_dl.py collections/sample/sample.toml --dry-run

# See what would be generated
python myrient_generator.py --gen-url --gen-readme --dry-run collections/sample/sample.toml
```

**Remote Collections:**
```bash
# Download from any URL
./myrient_dl.sh https://raw.githubusercontent.com/user/repo/main/my-collection.toml

# Generate from remote TOML
python myrient_generator.py --gen-url https://example.com/collection.toml
```

## Requirements

- **Python 3.11+** (for built-in TOML support)
- **Wget** (auto-installed on Windows, commonly available on Linux/macOS)

## Development

Built with AI assistance given limited programming knowledge. This is a proof-of-concept for decentralized, code-as-configuration ROM collections that should be further developed by those with more expertise.
