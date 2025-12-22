# Multi-Platform ROM Collection

This collection contains ROMs for multiple gaming platforms.

## Metadata

- **Generated**: 2025-12-22 20:58:56 UTC
- **Total Platforms**: 3
- **Total Files**: 16
- **Total Size**: 44.8 MiB (47.0 MB)

## Included Platforms

| PLATFORM | FILES | SIZE | DIRECTORY |
| --- | --- | --- | --- |
| [GB](gb/README.md) | 3 Files | 1.2 MiB (1.3 MB) | gb |
| [GBC](gbc/README.md) | 6 Files | 3.9 MiB (4.1 MB) | gbc |
| [GBA](gba/README.md) | 7 Files | 39.7 MiB (41.6 MB) | gba |


## Download

### Local Execution
To download all platforms in this collection locally:

```bash
python myrient_dl.py "sample.toml"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "sample.toml"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/sample/sample.toml"
```

**Windows:**
```batch
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/sample/sample.toml'; del $t }"
```
