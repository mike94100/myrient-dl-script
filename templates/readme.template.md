# {{TITLE}}

{{DESCRIPTION}}

## Metadata

- **Generated**: {{GENERATED_DATE}}
- **ROM Platforms**: {{ROM_PLATFORM_COUNT}}
- **BIOS Platforms**: {{BIOS_PLATFORM_COUNT}}
- **Total Files**: {{FILES_COUNT}}
- **Total Size**: {{TOTAL_SIZE}}

## Directory Structure

{{DIRECTORY_STRUCTURE}}

## ROM Files

{{ROM_FILES}}

## BIOS Files

{{BIOS_FILES}}

## Download

### Remote Usage (Recommended)

This is the recommended way for most users to download the collection. These scripts provide a single command to download files without any installation required. The scripts are interactive to customize your download.

**Linux/macOS:**
```bash
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.sh) {{COLLECTION_TOML_REMOTE}}
```

**Python (Cross-platform):**
```bash
python3 <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) {{COLLECTION_TOML_REMOTE}}
```

**Windows PowerShell:**
```powershell
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl '{{COLLECTION_TOML_REMOTE}}' }"
```

### Local (Developers)

This is recommended for developers to modify and test the collection prior to publishing. This requires the repo to be cloned locally.

**Linux/macOS:**
```bash
./myrient_dl.sh {{COLLECTION_TOML_LOCAL}}
```

**Windows:**
```powershell
.\myrient_dl.ps1 {{COLLECTION_TOML_LOCAL}}
```

**Python:**
```bash
python myrient_dl.py {{COLLECTION_TOML_LOCAL}}
```
