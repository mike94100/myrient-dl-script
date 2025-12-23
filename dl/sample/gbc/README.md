# GBC ROM Collection

This collection contains ROMs for the GBC.

## Metadata

- **Generated**: 2025-12-22 20:58:54 UTC
- **Source URL**: [https://myrient.erista.me/files/No-Intro/Nintendo - Game Boy Color/](https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Game%20Boy%20Color/)
- **Total Files**: 6
- **Total Size**: 3.9 MiB (4.1 MB)
- **Platform Directory**: gbc

## ROM Files
<details>
<summary>The following ROM files are included in this collection:</summary>

| GAME | TAGS | SIZE |
| --- | --- | --- |
| Pokemon - Crystal Version | (USA, Europe) (Rev 1) | 1005.8 KiB |
| Pokemon - Gold Version | (USA, Europe) (SGB Enhanced) (GB Compatible) | 730.7 KiB |
| Pokemon Pinball | (USA, Australia) (Rumble Version) (SGB Enhanced) (GB Compatible) | 307.8 KiB |
| Pokemon Puzzle Challenge | (USA, Australia) | 662.8 KiB |
| Pokemon - Silver Version | (USA, Europe) (SGB Enhanced) (GB Compatible) | 730.6 KiB |
| Pokemon Trading Card Game | (Europe) (En,Es,It) (Rev 1) (SGB Enhanced) (GB Compatible) | 603.8 KiB |

</details>

## Download

### Local Execution
To download all ROMs in this collection locally:

```bash
python myrient_dl.py "gbc.toml"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "gbc.toml"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/gbc/gbc.toml"
```

**Windows:**
```batch
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/gbc/gbc.toml'; del $t }"
```
