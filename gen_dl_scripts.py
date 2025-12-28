#!/usr/bin/env python3
"""
Download Script Generator
Generates bash and PowerShell scripts for downloading ROMs/BIOS from TOML configurations
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any
from utils.toml_utils import parse_toml_file as parse_toml, parse_platforms_from_config

def load_config() -> Dict[str, Any]:
    """Load base configuration from config.toml"""
    config_path = Path('config.toml')
    if config_path.exists():
        return parse_toml(str(config_path))
    return {}

def read_url_file(url_file_path: Path) -> List[str]:
    """Read URLs from a URL list file"""
    if not url_file_path.exists():
        raise FileNotFoundError(f"URL file not found: {url_file_path}")

    with open(url_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    return urls

def generate_bash_script(platforms: Dict[str, Dict[str, Any]], output_dir: Path, repo_base_url: str, base_path: Path = None, toml_stem: str = None) -> str:
    """Generate bash download script using template"""

    # Read template
    template_path = Path(__file__).parent / 'templates' / 'collection_dl.template.sh'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Prepare platform data with descriptive names
    platform_list = []
    for platform_name, platform_config in platforms.items():
        platform_type = platform_config['type']
        descriptive_name = f"{platform_type}.{platform_name}"
        platform_list.append(descriptive_name)

    platforms_bash_array = '(' + ' '.join(f'"{p}"' for p in platform_list) + ')'

    # Create separate arrays for each configuration type
    platform_names = []
    platform_dirs = []
    platform_urls = []
    platform_extracts = []

    for platform_name, platform_config in platforms.items():
        platform_type = platform_config['type']
        urllist_path = platform_config['urllist']
        github_url = f"{repo_base_url}/{urllist_path}"
        directory = platform_config['directory']
        extract = '1' if platform_config.get('extract', False) else '0'

        descriptive_name = f"{platform_type}.{platform_name}"
        platform_names.append(descriptive_name)
        platform_dirs.append(directory)
        platform_urls.append(github_url)
        platform_extracts.append(extract)

    # Create platform arrays section
    def bash_array_multiline(items, array_name):
        lines = [f'{array_name}=(']
        for item in items:
            lines.append(f'    "{item}"')
        lines.append(')')
        return '\n'.join(lines)

    platform_arrays = '\n'.join([
        bash_array_multiline(platform_names, 'PLATFORM_NAMES'),
        '',
        bash_array_multiline(platform_dirs, 'PLATFORM_DIRS'),
        '',
        bash_array_multiline(platform_urls, 'PLATFORM_URLS'),
        '',
        bash_array_multiline(platform_extracts, 'PLATFORM_EXTRACTS'),
    ])

    # Replace placeholders in template
    script = template.replace('{PLATFORM_ARRAYS}', platform_arrays)
    script = script.replace('{DEFAULT_PLATFORMS}', platforms_bash_array)
    script = script.replace('{TOML_STEM}', toml_stem or 'collection')

    return script

def generate_powershell_script(platforms: Dict[str, Dict[str, Any]], output_dir: Path, repo_base_url: str, base_path: Path = None, toml_stem: str = None) -> str:
    """Generate PowerShell download script using template"""

    # Read template
    template_path = Path(__file__).parent / 'templates' / 'collection_dl.template.ps1'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Prepare platform data with descriptive names
    platform_list = []
    for platform_name, platform_config in platforms.items():
        platform_type = platform_config['type']
        descriptive_name = f"{platform_type}.{platform_name}"
        platform_list.append(descriptive_name)

    platforms_ps_array = '@(' + ', '.join(f'"{p}"' for p in platform_list) + ')'

    # Create separate arrays for each configuration type
    platform_names = []
    platform_dirs = []
    platform_urls = []
    platform_extracts = []

    for platform_name, platform_config in platforms.items():
        platform_type = platform_config['type']
        urllist_path = platform_config['urllist']
        github_url = f"{repo_base_url}/{urllist_path}"
        directory = platform_config['directory']
        extract = '$true' if platform_config.get('extract', False) else '$false'

        descriptive_name = f"{platform_type}.{platform_name}"
        platform_names.append(descriptive_name)
        platform_dirs.append(directory)
        platform_urls.append(github_url)
        platform_extracts.append(extract)

    # Create PowerShell arrays with each item on separate lines
    def powershell_array_multiline(items, array_name):
        lines = [f'${array_name} = @(']
        for item in items:
            lines.append(f'    "{item}"')
        lines.append(')')
        return '\n'.join(lines)

    platform_arrays = '\n'.join([
        powershell_array_multiline(platform_names, 'PlatformNames'),
        '',
        powershell_array_multiline(platform_dirs, 'PlatformDirs'),
        '',
        powershell_array_multiline(platform_urls, 'PlatformUrls'),
        '',
        powershell_array_multiline(platform_extracts, 'PlatformExtracts'),
    ])

    # Replace placeholders in template
    script = template.replace('{PLATFORM_ARRAYS}', platform_arrays)
    script = script.replace('{DEFAULT_PLATFORMS}', platforms_ps_array)
    script = script.replace('{TOML_STEM}', toml_stem or 'collection')

    return script

def generate_python_script(platforms: Dict[str, Dict[str, Any]], output_dir: Path, repo_base_url: str, base_path: Path = None, toml_stem: str = None) -> str:
    """Generate Python download script using template"""

    # Read template
    template_path = Path(__file__).parent / 'templates' / 'collection_dl.template.py'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Create separate lists for each configuration type
    platform_names = []
    platform_dirs = []
    platform_urls = []
    platform_extracts = []

    for platform_name, platform_config in platforms.items():
        platform_type = platform_config['type']
        urllist_path = platform_config['urllist']
        github_url = f"{repo_base_url}/{urllist_path}"
        directory = platform_config['directory']
        extract = platform_config.get('extract', False)

        descriptive_name = f"{platform_type}.{platform_name}"
        platform_names.append(descriptive_name)
        platform_dirs.append(directory)
        platform_urls.append(github_url)
        platform_extracts.append(extract)

    # Create Python lists with each item on separate lines
    def python_list_multiline(items, list_name):
        lines = [f'{list_name} = [']
        for item in items:
            if isinstance(item, str):
                lines.append(f'    "{item}",')
            elif isinstance(item, bool):
                lines.append(f'    {str(item).lower()},')
            else:
                lines.append(f'    {item},')
        lines.append(']')
        return '\n'.join(lines)

    platform_arrays = '\n'.join([
        python_list_multiline(platform_names, 'PLATFORM_NAMES'),
        '',
        python_list_multiline(platform_dirs, 'PLATFORM_DIRS'),
        '',
        python_list_multiline(platform_urls, 'PLATFORM_URLS'),
        '',
        python_list_multiline(platform_extracts, 'PLATFORM_EXTRACTS'),
    ])

    # Replace placeholders in template
    script = template.replace('{PLATFORM_ARRAYS}', platform_arrays)
    script = script.replace('{TOML_STEM}', toml_stem or 'collection')

    return script

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate download scripts from TOML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gen_dl_scripts.py collections/sample/sample.toml
  python gen_dl_scripts.py collections/sample/sample.toml -o /custom/output/dir
        """
    )

    parser.add_argument(
        'toml_file',
        help='Path to TOML configuration file'
    )

    parser.add_argument(
        '-o', '--output',
        help='Base output directory for downloads (default: ~/Downloads)'
    )

    parser.add_argument(
        '--base-path',
        help='Base path for resolving relative URLs in TOML (default: TOML file directory)'
    )

    args = parser.parse_args()

    # Validate TOML file
    toml_path = Path(args.toml_file)
    if not toml_path.exists():
        print(f"Error: TOML file not found: {toml_path}", file=sys.stderr)
        sys.exit(1)

    # Parse TOML
    try:
        toml_config = parse_toml(str(toml_path))
    except Exception as e:
        print(f"Error parsing TOML file: {e}", file=sys.stderr)
        sys.exit(1)

    # Get platforms
    platforms = parse_platforms_from_config(toml_config)
    if not platforms:
        print("Error: No platforms found in TOML file", file=sys.stderr)
        sys.exit(1)

    # Load config to get repo_base_url
    config = load_config()
    repo_base_url = config.get('general', {}).get('repo_base_url', 'https://raw.githubusercontent.com/mike94100/myrient-dl-script/main')

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path.home() / "Downloads"

    # Determine base path for URL resolution (project root)
    if args.base_path:
        base_path = Path(args.base_path)
    else:
        base_path = Path.cwd()  # Project root

    # Generate scripts
    toml_dir = toml_path.parent
    toml_stem = toml_path.stem  # Get filename without extension

    # Generate bash script
    bash_script = generate_bash_script(platforms, output_dir, repo_base_url, base_path, toml_stem)
    bash_path = toml_dir / f'{toml_stem}_dl.sh'
    with open(bash_path, 'w', encoding='utf-8') as f:
        f.write(bash_script)

    # Make bash script executable
    bash_path.chmod(0o755)

    # Generate PowerShell script
    powershell_script = generate_powershell_script(platforms, output_dir, repo_base_url, base_path, toml_stem)
    ps1_path = toml_dir / f'{toml_stem}_dl.ps1'
    with open(ps1_path, 'w', encoding='utf-8') as f:
        f.write(powershell_script)

    # Generate Python script
    python_script = generate_python_script(platforms, output_dir, repo_base_url, base_path, toml_stem)
    py_path = toml_dir / f'{toml_stem}_dl.py'
    with open(py_path, 'w', encoding='utf-8') as f:
        f.write(python_script)

    # Make Python script executable
    py_path.chmod(0o755)

    print(f"Generated scripts:")
    print(f"  Bash: {bash_path}")
    print(f"  PowerShell: {ps1_path}")
    print(f"  Python: {py_path}")
    print(f"Output directory: {output_dir}")
    print(f"Platforms: {', '.join(platforms.keys())}")

if __name__ == "__main__":
    main()
