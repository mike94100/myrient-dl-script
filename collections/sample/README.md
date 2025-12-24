# SAMPLE.TOML ROM Collection

This collection contains ROMs for multiple gaming platforms with intelligent filtering.

## Metadata

- **Generated**: 2025-12-24 07:07:43 UTC
- **Total Platforms**: 3
- **Total Files**: 11
- **Total Size**: 29.9 MiB (31.4 MB)

## Directory Structure

```
roms/
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



## Download

### Generate URLs and Download All Platforms
```bash
# Generate URL files for all platforms
python gen_urls.py scrape collections/sample.toml/collection.toml

# Download all ROMs to default directory
python myrient_dl.py --urls collections/sample.toml/urls/
```

### Individual Platform Download
```bash
# Generate and download specific platform
python gen_urls.py scrape collections/sample.toml/collection.toml
python myrient_dl.py --urls collections/sample.toml/urls/gb.txt --output ~/roms/gb
```

### Remote One-Command Download
**Linux/Mac:**
```bash
# Download all platforms to ~/Downloads/roms
python gen_urls.py scrape collections/sample.toml/collection.toml && \
python myrient_dl.py --urls collections/sample.toml/urls/ --output ~/Downloads/roms
```
