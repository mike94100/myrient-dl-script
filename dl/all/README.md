# Multi-Platform ROM Collection

This collection contains ROMs for multiple gaming platforms.

## Metadata

- **Generated**: 2025-12-23 05:52:36 UTC
- **Total Platforms**: 21
- **Total Files**: 65719
- **Total Size**: 29.6 TiB (32.5 TB)

## Included Platforms

| PLATFORM | FILES | SIZE | DIRECTORY |
| --- | --- | --- | --- |
| [3DS](3ds/README.md) | 2149 Files | 1.1 TiB (1.2 TB) | 3ds |
| [ATARI2600](atari2600/README.md) | 854 Files | 22.6 MiB (23.7 MB) | atari2600 |
| [ATARI5200](atari5200/README.md) | 183 Files | 1.8 MiB (1.9 MB) | atari5200 |
| [ATARI7800](atari7800/README.md) | 126 Files | 3.6 MiB (3.8 MB) | atari7800 |
| [C64](c64/README.md) | 327 Files | 6.7 MiB (7.0 MB) | c64 |
| [COLECOVISION](colecovision/README.md) | 201 Files | 2.2 MiB (2.3 MB) | colecovision |
| [DREAMCAST](dreamcast/README.md) | 1506 Files | 772 GiB (829 GB) | dreamcast |
| [GB](gb/README.md) | 1958 Files | 227 MiB (238 MB) | gb |
| [GBA](gba/README.md) | 3478 Files | 13.3 GiB (14.3 GB) | gba |
| [GBC](gbc/README.md) | 1958 Files | 939 MiB (985 MB) | gbc |
| [GC](gc/README.md) | 2015 Files | 1.5 TiB (1.6 TB) | gc |
| [GENESIS](genesis/README.md) | 2786 Files | 1.9 GiB (2.1 GB) | genesis |
| [INTELLIVISION](intellivision/README.md) | 207 Files | 1.7 MiB (1.8 MB) | intellivision |
| [N64](n64/README.md) | 1147 Files | 14.1 GiB (15.2 GB) | n64 |
| [NDS](nds/README.md) | 7642 Files | 222 GiB (238 GB) | nds |
| [NES](nes/README.md) | 4464 Files | 532 MiB (558 MB) | nes |
| [PS2](ps2/README.md) | 11717 Files | 16.4 TiB (18.1 TB) | ps2 |
| [PSP](psp/README.md) | 4250 Files | 696 GiB (747 GB) | psp |
| [PSX](psx/README.md) | 10886 Files | 3.0 TiB (3.3 TB) | psx |
| [SNES](snes/README.md) | 4087 Files | 3.5 GiB (3.8 GB) | snes |
| [WII](wii/README.md) | 3778 Files | 5.9 TiB (6.5 TB) | wii |


## Download

### Local Execution
To download all ROMs in this collection locally:

```bash
python myrient_dl.py "all.toml"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "all.toml"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
# Download to default location (~/Downloads/roms)
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/all/all.toml"

# Download to custom directory
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/all/all.toml" --output "~/custom/path"
```

**Windows:**
```batch
REM Download to default location (%USERPROFILE%\Downloads\roms)
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/all/all.toml'; del $t }"

REM Download to custom directory
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/all/all.toml' --output '%USERPROFILE%\Downloads\roms'; del $t }"
```

