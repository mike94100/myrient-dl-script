# ROMs as Code Sample Collection

This is a small sample collection used for testing the download function while maintaing a small file footprint.

## Metadata

- **Generated**: 2026-01-08 05:59:46 UTC
- **ROM Platforms**: 3
- **BIOS Platforms**: 1
- **Total Files**: 19
- **Total Size**: 52.7 MiB (55.2 MB)

## Directory Structure

```
└── bios/
    ├── ps2/ (3 files, 7.8 MiB (8.2 MB))

└── roms/
    ├── gb/ (3 files, 1.2 MiB (1.3 MB))
    ├── gba/ (7 files, 39.7 MiB (41.6 MB))
    ├── gbc/ (6 files, 3.9 MiB (4.1 MB))
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
  - Pokemon Mystery Dungeon - Red Rescue Team (USA, Australia).zip (10.9 MiB)
  - Pokemon Pinball - Ruby & Sapphire (USA).zip (2.5 MiB)
</details>

<details>
<summary>gbc</summary>

  - Pokemon - Crystal Version (USA, Europe) (Rev 1).zip (1005.8 KiB)
  - Pokemon - Gold Version (USA, Europe) (SGB Enhanced) (GB Compatible).zip (730.7 KiB)
  - Pokemon - Silver Version (USA, Europe) (SGB Enhanced) (GB Compatible).zip (730.6 KiB)
  - Pokemon Pinball (USA, Australia) (Rumble Version) (SGB Enhanced) (GB Compatible).zip (307.8 KiB)
  - Pokemon Puzzle Challenge (USA, Australia).zip (662.8 KiB)
  - Pokemon Trading Card Game (Europe) (En,Es,It) (Rev 1) (SGB Enhanced) (GB Compatible).zip (603.8 KiB)
</details>



## BIOS Files

<details>
<summary>ps2</summary>

  - ps2-0230a-20080220-175343.zip (2.6 MiB)
  - ps2-0230e-20080220-175343.zip (2.6 MiB)
  - ps2-0230j-20080220-175343.zip (2.6 MiB)
</details>



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
