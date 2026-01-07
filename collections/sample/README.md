# ROMs as Code Sample Collection

This is a small sample collection used for testing the download function while maintaing a small file footprint.

## Metadata

- **Generated**: 2026-01-07 06:43:56 UTC
- **ROM Platforms**: 3
- **BIOS Platforms**: 0
- **Total Files**: 11
- **Total Size**: 29.917095184326172 MiB (31.370348 MB)

## Directory Structure

```
└── roms/
    ├── gb/ (3 files, 1.2078132629394531 MiB (1.266484 MB))
    ├── gba/ (5 files, 26.300003051757813 MiB (27.577552 MB))
    ├── gbc/ (3 files, 2.4092788696289063 MiB (2.526312 MB))
```

## ROM Files

<details>
<summary>gb</summary>

  - Pokemon - Blue Version (USA, Europe) (SGB Enhanced).zip (369.5 KiB)
  - Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip (369.8 KiB)
  - Pokemon - Yellow Version - Special Pikachu Edition (USA, Europe) (CGB+SGB Enhanced).zip (497.5 KiB)
</details>

<details>
<summary>gba</summary>

  - Pokemon - Emerald Version (USA, Europe).zip (6.7 MiB)
  - Pokemon - FireRed Version (USA, Europe) (Rev 1).zip (5.1 MiB)
  - Pokemon - LeafGreen Version (USA, Europe) (Rev 1).zip (5.1 MiB)
  - Pokemon - Ruby Version (USA, Europe) (Rev 2).zip (4.7 MiB)
  - Pokemon - Sapphire Version (USA, Europe) (Rev 2).zip (4.7 MiB)
</details>

<details>
<summary>gbc</summary>

  - Pokemon - Crystal Version (USA, Europe) (Rev 1).zip (1005.8 KiB)
  - Pokemon - Gold Version (USA, Europe) (SGB Enhanced) (GB Compatible).zip (730.7 KiB)
  - Pokemon - Silver Version (USA, Europe) (SGB Enhanced) (GB Compatible).zip (730.6 KiB)
</details>



## BIOS Files



## Download

### Remote Usage (Recommended)

This is the recommended way for most users to download the collection. These scripts provide a single command to download files without any installation required. The scripts are interactive to customize your download.

**Linux/macOS:**
```bash
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.sh) https://raw.githubusercontent.com/mike94100/roms-as-code/main/collections/sample/sample.toml
```

**Python (Cross-platform):**
```bash
python3 <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) https://raw.githubusercontent.com/mike94100/roms-as-code/main/collections/sample/sample.toml
```

**Windows PowerShell:**
```powershell
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl 'https://raw.githubusercontent.com/mike94100/roms-as-code/main/collections/sample/sample.toml' }"
```

### Local (Developers)

This is recommended for developers to modify and test the collection prior to publishing. This requires the repo to be cloned locally.

**Linux/macOS:**
```bash
./myrient_dl.sh collections/sample/sample.toml
```

**Windows:**
```powershell
.\myrient_dl.ps1 collections/sample/sample.toml
```

**Python:**
```bash
python myrient_dl.py collections/sample/sample.toml
```
