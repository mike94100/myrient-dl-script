# Multi-Platform ROM Collection

This collection contains ROMs for multiple gaming platforms.

## Metadata

- **Generated**: 2025-12-23 06:06:55 UTC
- **Total Platforms**: 21
- **Total Files**: 17762
- **Total Size**: 8.3 TiB (9.1 TB)

## Included Platforms

| PLATFORM | FILES | SIZE | DIRECTORY |
| --- | --- | --- | --- |
| [3DS](3ds/README.md) | 617 Files | 287 GiB (308 GB) | 3ds |
| [ATARI2600](atari2600/README.md) | 465 Files | 21.1 MiB (22.1 MB) | atari2600 |
| [ATARI5200](atari5200/README.md) | 73 Files | 714 KiB (731 KB) | atari5200 |
| [ATARI7800](atari7800/README.md) | 59 Files | 1.8 MiB (1.9 MB) | atari7800 |
| [C64](c64/README.md) | 195 Files | 2.6 MiB (2.7 MB) | c64 |
| [COLECOVISION](colecovision/README.md) | 137 Files | 1.5 MiB (1.5 MB) | colecovision |
| [DREAMCAST](dreamcast/README.md) | 344 Files | 179 GiB (192 GB) | dreamcast |
| [GB](gb/README.md) | 637 Files | 60.8 MiB (63.7 MB) | gb |
| [GBA](gba/README.md) | 1185 Files | 4.5 GiB (4.9 GB) | gba |
| [GBC](gbc/README.md) | 563 Files | 238 MiB (249 MB) | gbc |
| [GC](gc/README.md) | 659 Files | 507 GiB (544 GB) | gc |
| [GENESIS](genesis/README.md) | 846 Files | 566 MiB (594 MB) | genesis |
| [INTELLIVISION](intellivision/README.md) | 149 Files | 1.2 MiB (1.3 MB) | intellivision |
| [N64](n64/README.md) | 319 Files | 3.6 GiB (3.9 GB) | n64 |
| [NDS](nds/README.md) | 2509 Files | 58.8 GiB (63.2 GB) | nds |
| [NES](nes/README.md) | 858 Files | 80.6 MiB (84.6 MB) | nes |
| [PS2](ps2/README.md) | 2774 Files | 4.2 TiB (4.7 TB) | ps2 |
| [PSP](psp/README.md) | 967 Files | 200 GiB (214 GB) | psp |
| [PSX](psx/README.md) | 1886 Files | 578 GiB (621 GB) | psx |
| [SNES](snes/README.md) | 899 Files | 711 MiB (745 MB) | snes |
| [WII](wii/README.md) | 1621 Files | 2.3 TiB (2.5 TB) | wii |


## Download

### Local Execution
To download all ROMs in this collection locally:

```bash
python myrient_dl.py "1g1r.toml"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "1g1r.toml"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
# Download to default location (~/Downloads/roms)
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/1g1r/1g1r.toml"

# Download to custom directory
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/1g1r/1g1r.toml" --output "~/custom/path"
```

**Windows:**
```batch
REM Download to default location (%USERPROFILE%\Downloads\roms)
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/1g1r/1g1r.toml'; del $t }"

REM Download to custom directory
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/1g1r/1g1r.toml' --output '%USERPROFILE%\Downloads\roms'; del $t }"
```

