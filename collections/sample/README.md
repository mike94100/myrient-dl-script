# SAMPLE ROM Collection

This collection contains ROMs for multiple gaming platforms.

## Metadata

- **Generated**: 2025-12-31 03:48:43 UTC
- **ROM Platforms**: 3
- **BIOS Platforms**: 1
- **Total Files**: 14
- **Total Size**: 37.7 MiB (39.5 MB)

## Directory Structure

```
├── bios/
│   └── ps2/ (3 files, 7.8 MiB)
└── roms/
    ├── gb/ (3 files, 1.2 MiB)
    ├── gba/ (5 files, 26.3 MiB)
    └── gbc/ (3 files, 2.4 MiB)
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

<details>
<summary>ps2</summary>

  - ps2-0230a-20080220-175343.zip (2.6 MiB)
  - ps2-0230e-20080220-175343.zip (2.6 MiB)
  - ps2-0230j-20080220-175343.zip (2.6 MiB)
</details>



## Download

### Local Usage

If you have the myrient-dl-script repository cloned locally:

**Linux/macOS:**
```bash
./myrient_dl.sh collections/sample/sample.toml
```

**Windows:**
```powershell
.\myrient_dl.ps1 collections/sample/sample.toml
```

**Python (Cross-platform):**
```bash
python myrient_dl.py collections/sample/sample.toml
```

### Remote Usage

Run the scripts directly from the repository without downloading them first. The scripts will fetch and parse the collection TOML from the URL and allow interactive platform selection.

**Linux/macOS:**
```bash
bash <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.sh) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

**Python (Cross-platform):**
```bash
python3 <(curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.py) https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml
```

**Windows PowerShell:**
```powershell
powershell -Command "& { $script = Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/myrient_dl.ps1' -UseBasicParsing; $sb = [scriptblock]::Create($script.Content); & $sb -CollectionUrl 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/collections/sample/sample.toml' }"
```
