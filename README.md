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

Start by testing the included [sample collection](collections/sample/README.md):

**Linux/macOS:**
```bash
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.sh) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

**Windows:**
```powershell
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml' }"
```

**Python (Cross-platform):**
```bash
python <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

### Downloads

**Local:**
```bash
python myrient_dl.py https://example.com/collection.toml
```

**Remote:**
```bash
python <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) https://example.com/my-collection.toml
```

### Creating Collections

1. **Copy and edit collection.template.toml**

2. **Generate Content**
   ```bash
   # Generate URL files by scraping Myrient
   python myrient_generator.py --gen-url collection.toml

   # Generate README documentation
   python myrient_generator.py --gen-readme collection.toml

   # Generate both concurrently
   python myrient_generator.py --gen-url --gen-readme collection.toml
   ```

3. [See provided collections](collections/README.md)

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
