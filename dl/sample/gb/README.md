# GB ROM Collection

This collection contains ROMs for the GB.

## Metadata

- **Generated**: 2025-12-22 20:58:52 UTC
- **Source URL**: [https://myrient.erista.me/files/No-Intro/Nintendo - Game Boy/](https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Game%20Boy/)
- **Total Files**: 3
- **Total Size**: 1.2 MiB (1.3 MB)
- **Platform Directory**: gb

## ROM Files
<details>
<summary>The following ROM files are included in this collection:</summary>

| GAME | TAGS | SIZE |
| --- | --- | --- |
| Pokemon - Blue Version | (USA, Europe) (SGB Enhanced) | 369.5 KiB |
| Pokemon - Red Version | (USA, Europe) (SGB Enhanced) | 369.8 KiB |
| Pokemon - Yellow Version - Special Pikachu Edition | (USA, Europe) (CGB+SGB Enhanced) | 497.5 KiB |

</details>

## Download

### Local Execution
To download all ROMs in this collection locally:

```bash
python myrient_dl.py "gb.toml"
```

Or download to a custom directory:

```bash
python myrient_dl.py -o /path/to/directory "gb.toml"
```

### Remote Execution (One-Command)
Download directly without installing anything:

**Linux/Mac:**
```bash
wget -q -O - https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s -- --toml "https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/gb/gb.toml"
```

**Windows:**
```batch
powershell -c "& { $s=iwr 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat'; $t=New-TemporaryFile; $t=$t.FullName+'.bat'; [IO.File]::WriteAllText($t,$s); & $t --toml 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/gb/gb.toml'; del $t }"
```
