# GBA ROM Collection

This collection contains ROMs for the GBA.

## Metadata

- **Generated**: 2025-12-22 20:58:56 UTC
- **Source URL**: [https://myrient.erista.me/files/No-Intro/Nintendo - Game Boy Advance/](https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Game%20Boy%20Advance/)
- **Total Files**: 7
- **Total Size**: 39.7 MiB (41.6 MB)
- **Platform Directory**: gba

## ROM Files
<details>
<summary>The following ROM files are included in this collection:</summary>

| GAME | TAGS | SIZE |
| --- | --- | --- |
| Pokemon - Emerald Version | (USA, Europe) | 6.7 MiB |
| Pokemon - FireRed Version | (USA, Europe) (Rev 1) | 5.1 MiB |
| Pokemon - LeafGreen Version | (USA, Europe) (Rev 1) | 5.1 MiB |
| Pokemon Mystery Dungeon - Red Rescue Team | (USA, Australia) | 10.9 MiB |
| Pokemon Pinball - Ruby &amp; Sapphire | (USA) | 2.5 MiB |
| Pokemon - Ruby Version | (USA, Europe) (Rev 2) | 4.7 MiB |
| Pokemon - Sapphire Version | (USA, Europe) (Rev 2) | 4.7 MiB |

</details>

## Download

### Local Execution
To download all ROMs in this collection locally:

```bash
python myrient_dl.py "gba.toml"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "gba.toml"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/gba/gba.toml"
```

**Windows:**
```batch
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/gba/gba.toml'; del $t }"
```
