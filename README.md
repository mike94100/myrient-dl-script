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

## Usage Guide

### Test with Sample Collection

Start by testing the included sample collection:

**Linux/macOS:**
```bash
./myrient_dl.sh collections/sample/sample.toml
```

**Windows:**
```powershell
.\myrient_dl.ps1 collections\sample\sample.toml
```

**Python (Cross-platform):**
```python
python myrient_dl.py collections/sample/sample.toml
```

### Run Scripts without Downloading

Execute scripts directly from the repository without cloning. The scripts will fetch and parse TOML collections from any URL:

**Linux/macOS:**
```bash
# Run bash script from GitHub
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.sh) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml

# Run Python script from GitHub
python3 <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

**Windows PowerShell:**
```powershell
# Run PowerShell script from GitHub
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml' }"
```

### Download from Any Remote Collection

**Local Scripts (after cloning):**
```bash
# Download from any hosted collection
./myrient_dl.sh https://example.com/my-collection.toml

# Download with custom output directory
python myrient_dl.py https://example.com/my-collection.toml --output ~/my-games
```

**Remote Scripts (run from GitHub):**
```bash
# Download any collection using bash script
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.sh) https://example.com/my-collection.toml

# Download any collection using Python script
python3 <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) https://example.com/my-collection.toml
```

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

**Dry Runs:**
```bash
# Preview what would be downloaded
python myrient_dl.py collections/sample/sample.toml --dry-run

# Preview what would be generated
python myrient_generator.py --gen-url --gen-readme --dry-run collections/sample/sample.toml
```

## Requirements

- **Python 3.11+** (for built-in TOML support)
- **Wget** (install on Windows, commonly available on Linux/macOS)

## AI Developed

Built with AI assistance given my limited programming knowledge. Because of this, I would not recommend using this for any more than a test use case. This is meant as a proof-of-concept for code-as-configuration ROM collections that can be easily downloaded to any device by any user.
