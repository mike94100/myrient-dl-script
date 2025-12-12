# myrient-dl-script
Scripts allowing users to generate ROM configuration files and download ROMs.

## Why
- No-installation batch downloads from Myrient. 
- Create ROM collections without hosting the ROM files youself.
- Access & share configuration files for free on GitHub, GitLab, etc.
- "Backup" your ROM library as code.

## Platform Configuration
`gen-platform-toml.sh` generates a platform-specific .toml file that will store the URL for the platform, directory to save ROMs into, and the file names for the ROMs themselves. This can be used with a .sed or .awk filter configuration file to generate a platform configuration excluding games matching a defined criteria.

## README Documentation
`gen-readme.sh` generates a README.md, usable on GitHub, with basic information about the collection is provided. This includes which games will be downloaded, total files size, etc.

## Download
`myrient-dl.sh` downloads the ROMs as defined in the platform configuration files using [WGET](https://www.man7.org/linux/man-pages/man1/wget.1.html).

## To-Do
- Support a single line 'curl' command for downloading ROMs
- Batch generate Platform Configuration TOML files using pre-defined values for URL Path and file path
- Batch generate multiple READMEs (already supports a single Meta-Configuration TOML that links to Platform TOML)
- Improved logging

## AI
I used AI when making this. I have some coding/scripting knowledge but typically on a much smaller scale. More so wanted this out there as a proof of concept that I hadn't seen before.