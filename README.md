# Myrient ROM Downloader

A Python ROM collection & downloading script for the Myrient site.

## Why

I made this as a proof-of-concept on configuring a ROM collection as "code". This allows users to have a backup of what their ROM collection consisted of, and use a single command to recreate their ROM collection due to data loss. Given the tiny size of the .toml files (which are just text), you can backup your collection configuration very easily with no space constraints, even using GitHub/GitLab/Codeberg for free with remote script access.

## Design Goals

- **Simple Backups** This tool lets users create a backup of their collection as text, which is space-efficient for storage basically anywhere, even for free with easy remote access on GitHub/GitLab/Codeberg. Backing up a large collection of ROMs via cloud providers is costly and may be subject to copyright issues or other restrictions. Locally requires some technical knowledge (which I would recommend people gain) & higher initial cost for storage, redundancy, and backups.
- **Takedown Resiliency** I tried to create the tool to be easy to switch to a new Base URL or URL Path Directory if needed. If a new provider did use different file names, there is not much I can do to account for it. But the text would still serve as a list of games in the worst case scenario. Since the file names are not copyrightable, the .toml files themselves would not pose any legal issue. There is nothing I can do if a full crackdown on all ROM sites occured, which is why users should look into local storage and backups. But this should be a good, free, and easy first step.
- **Easy Downloads** The Myrient site itself is great, but only functions to download single files. There are many tools to download files bulk from Myrient, but typically require installation and some configuration for filtering. This tool is meant to run as a simple command and access the script & configurations remotely. One command to download any collection with no installs.
- **Customization** This tool lets users filter to create a generic configuration then manually update the file list to create fully custom collections. This process is what allows users to backup a specific configuration as text. Most Myrient tools today provide on the fly filtering & downloads, but no way to pre-define specific lists of games.

  Examples:
  - Your entire ROM collection
  - A subset of your ROM collection for specific devices
  - A 1 Game 1 Rom (1G1R) collection
  - Top 25 for each Platform
  - All games in a specific franchise
- **No File Hosting** Since all downloads are from Myrient, users can share & curate any number of collections without needing to host any files themselves. 
- **Authenticity** Since Myrient is used as the source and provides only files with known hashes from known groups, users can be sure all files downloaded are authentic. This also ensures that ROMs from collections created by other users are authentic.

## Features

- **Cross-platform**: Pyhton works on Windows, MacOS, and Linux
- **Wget-based Downloads**: Wget is recommended by Myrient for downloads
- **Filtering**: Scripts to filter & Deduplicate ROM files
- **TOML Configuration**: Scrape & filter Myrient to create user-readable & editable configurations
- **README generation**: Create documentation from configuration files

## Quick Start (One-Command Downloads)

For the easiest experience, use the bootstrap scripts that download everything automatically:

### Linux/Mac
```bash
# Download sample ROMs
curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash

# Download specific collection
curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.sh | bash -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/1g1r/1g1r.toml
```

### Windows
```batch
# Download sample ROMs
curl -s https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/download_roms.bat -o download_roms.bat && download_roms.bat

# Download specific platform
download_roms.bat https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/1g1r/1g1r.toml
```

The bootstrap scripts:
- Download the Python code from this repo
- Install dependencies automatically
- Handle referenced platform .toml files
- Support any TOML source

## Requirements

- **Python 3.11+** (for built-in TOML support)
- **Wget** (installed automatically by bootstrap scripts)
- **Git** (for cloning the repo)
- **curl** (for downloading TOML files)

## AI

This was coded with AI given my fairly limited programming knowledge. Made this more as a proof-of-concept for functionality I haven't seen that should be further developed by those more knowledgable.
