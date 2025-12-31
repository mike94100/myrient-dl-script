# Myrient Download Script
# Downloads files from any TOML collection configuration

param(
    [Parameter(Mandatory=$true)]
    [string]$CollectionUrl,

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "$env:USERPROFILE/Downloads",

    [switch]$NonInteractive
)

# Global variables
$SelectedPlatforms = @()

# Logging functions
function Write-LogInfo {{
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] INFO: $Message" -ForegroundColor Green
}}

function Write-LogWarn {{
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] WARN: $Message" -ForegroundColor Yellow
}}

function Write-LogError {{
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ERROR: $Message" -ForegroundColor Red
    exit 1
}}

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -lt 5) {{
    Write-LogWarn "PowerShell version $($psVersion) detected. Some features may not work correctly."
}}

# Fetch and parse TOML from URL or local file
function Get-TomlContent {{
    param([string]$Url)

    try {{
        if ($Url -match '^https?://') {{
            # Remote URL
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing
            return $response.Content
        }} else {{
            # Local file
            if (Test-Path $Url) {{
                return Get-Content $Url -Raw
            } else {{
                Write-LogError "Local file not found: $Url"
            }}
        }}
    }} catch {{
        Write-LogError "Failed to fetch TOML from $Url: $_"
    }}
}}

# Simple TOML to PowerShell object converter
function ConvertFrom-Toml {{
    param([string]$TomlContent)

    $result = @{{}}

    # Split into lines and process
    $lines = $TomlContent -split "`n"
    $currentSection = $null
    $currentSubSection = $null

    foreach ($line in $lines) {{
        $line = $line.Trim()

        # Skip comments and empty lines
        if ($line -match '^#' -or $line -eq '') {{
            continue
        }}

        # Section headers
        if ($line -match '^\[([^\]]+)\]$') {{
            $sectionName = $matches[1]
            if ($sectionName -like '*.*') {{
                # Sub-section like [roms.gb]
                $parts = $sectionName -split '\.'
                $parentSection = $parts[0]
                $subSection = $parts[1]

                if (-not $result.ContainsKey($parentSection)) {{
                    $result[$parentSection] = @{{}}
                }}
                $result[$parentSection][$subSection] = @{{}}
                $currentSection = $parentSection
                $currentSubSection = $subSection
            }} else {{
                # Main section like [roms]
                $result[$sectionName] = @{{}}
                $currentSection = $sectionName
                $currentSubSection = $null
            }}
            continue
        }}

        # Key-value pairs
        if ($line -match '^\s*([^=]+)\s*=\s*(.+)\s*$') {{
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()

            # Remove quotes if present
            if ($value -match '^"(.*)"$') {{
                $value = $matches[1]
            }}

            # Convert boolean strings
            if ($value -eq 'true') {{ $value = $true }}
            elseif ($value -eq 'false') {{ $value = $false }}

            # Add to appropriate section
            if ($currentSubSection) {{
                $result[$currentSection][$currentSubSection][$key] = $value
            }} elseif ($currentSection) {{
                $result[$currentSection][$key] = $value
            }}
        }}
    }}

    return $result
}}

# Get unselected platforms
function Get-UnselectedPlatforms {{
    param([hashtable]$Platforms)

    $platformNames = @($Platforms.Keys)
    $unselected = @()
    foreach ($platform in $platformNames) {{
        if ($SelectedPlatforms -notcontains $platform) {{
            $unselected += $platform
        }}
    }}
    return ($unselected -join ", ")
}}

# Extract platforms from parsed TOML
function Get-PlatformsFromToml {{
    param([hashtable]$TomlData)

    $platforms = @{{}}

    # Process roms and bios sections
    foreach ($section in @('roms', 'bios')) {{
        if ($TomlData.ContainsKey($section)) {{
            foreach ($platformKey in $TomlData[$section].Keys) {{
                $platformData = $TomlData[$section][$platformKey]
                if ($platformData -is [hashtable]) {{
                    $platforms[$platformKey] = $platformData
                }}
            }}
        }}
    }}

    return $platforms
}}

# Resolve relative URL
function Resolve-RelativeUrl {{
    param([string]$TomlUrl, [string]$RelativePath)

    if ($TomlUrl -match '^https?://') {{
        # Remote URL: remove filename from TOML URL
        $baseUrl = $TomlUrl -replace '/[^/]*$', ''
        $resolved = "$baseUrl/$RelativePath"
        return $resolved
    }} else {{
        # Local file: resolve relative to script directory
        $scriptDir = Split-Path -Parent $PSCommandPath
        $tomlPath = Join-Path $scriptDir $TomlUrl
        $tomlDir = Split-Path -Parent $tomlPath
        $resolved = Join-Path $tomlDir $RelativePath
        return $resolved
    }}
}}

# Show interactive menu
function Show-Menu {{
    param([hashtable]$Platforms)

    $platformNames = @($Platforms.Keys)

    while ($true) {{
        Clear-Host
        Write-Host "=== Myrient Download Script ===" -ForegroundColor Cyan
        Write-Host "Collection: $CollectionUrl"
        Write-Host "Output directory: $OutputDir"
        Write-Host "Selected platforms: $(if ($SelectedPlatforms.Count -eq 0) {{ "None selected" }} else {{ $SelectedPlatforms -join ", " }})"
        Write-Host "Unselected platforms: $(if ($platformNames.Count -eq $SelectedPlatforms.Count) {{ "None" }} else {{ Get-UnselectedPlatforms $Platforms }})"
        Write-Host ""

        Write-Host "Options:"
        Write-Host "  1) Toggle platform selection"
        Write-Host "  2) Set output directory"
        Write-Host "  3) Dry run (preview download)"
        Write-Host "  4) Start download"
        Write-Host "  5) Cancel"
        Write-Host ""

        $choice = Read-Host "Choose option (1-5)"

        switch ($choice) {{
            "1" {{
                Select-Platforms $platformNames
            }}
            "2" {{
                Set-OutputDir
            }}
            "3" {{
                if ($SelectedPlatforms.Count -eq 0) {{
                    Write-Host "Error: Please select at least one platform first." -ForegroundColor Red
                    Read-Host "Press Enter to continue"
                    continue
                }}
                Invoke-DryRun $Platforms
            }}
            "4" {{
                if ($SelectedPlatforms.Count -eq 0) {{
                    Write-Host "Error: Please select at least one platform first." -ForegroundColor Red
                    Read-Host "Press Enter to continue"
                    continue
                }}
                return
            }}
            "5" {{
                Write-Host "Download cancelled."
                exit 0
            }}
            default {{
                Write-Host "Invalid option. Please try again." -ForegroundColor Red
                Read-Host "Press Enter to continue"
            }}
        }}
    }}
}}

# Platform selection
function Select-Platforms {{
    param([array]$PlatformNames)

    Write-Host ""
    Write-Host "Available platforms:"
    for ($i = 0; $i -lt $PlatformNames.Count; $i += 3) {{
        $rowPlatforms = $PlatformNames[$i..([math]::Min($i + 2, $PlatformNames.Count - 1))]
        $rowLines = @()
        for ($j = 0; $j -lt $rowPlatforms.Count; $j++) {{
            $platform = $rowPlatforms[$j]
            $marker = if ($SelectedPlatforms -contains $platform) {{ "[✓]" }} else {{ "[ ]" }}
            $line = "  {0} {1,2}) {2}" -f $marker, ($i + $j + 1), $platform
            $rowLines += $line
        }}
        Write-Host ($rowLines -join "    ")
    }}
    Write-Host ""

    $input = Read-Host "Enter platform numbers to toggle (space-separated) or 'all'/'none'"

    switch ($input) {{
        "all" {{
            $script:SelectedPlatforms = $PlatformNames.Clone()
        }}
        "none" {{
            $script:SelectedPlatforms = @()
        }}
        default {{
            $numbers = $input -split "\s+"
            foreach ($num in $numbers) {{
                if ($num -match "^\d+$" -and [int]$num -ge 1 -and [int]$num -le $PlatformNames.Count) {{
                    $platform = $PlatformNames[[int]$num - 1]
                    if ($SelectedPlatforms -contains $platform) {{
                        $script:SelectedPlatforms = $SelectedPlatforms | Where-Object {{ $_ -ne $platform }}
                    }} else {{
                        $script:SelectedPlatforms += $platform
                    }}
                }}
            }}
        }}
    }}
}}

# Set output directory
function Set-OutputDir {{
    Write-Host ""
    Write-Host "Current output directory: $OutputDir"
    $newDir = Read-Host "Enter new output directory (press Enter for ~/Downloads)"
    if (-not [string]::IsNullOrEmpty($newDir)) {{
        $script:OutputDir = $newDir
    }} elseif ([string]::IsNullOrEmpty($OutputDir)) {{
        $script:OutputDir = "$env:USERPROFILE/Downloads"
    }}
}}

# Dry run - show what will be downloaded
function Invoke-DryRun {{
    param([hashtable]$Platforms)

    Write-Host ""
    Write-Host "=== DRY RUN - Preview Download ===" -ForegroundColor Cyan
    Write-Host "Output directory: $OutputDir"
    Write-Host "Selected platforms: $($SelectedPlatforms -join ", ")"
    Write-Host ""

    Write-Host "Directories that will be created:"

    foreach ($platformName in $SelectedPlatforms) {{
        $platformData = $Platforms[$platformName]
        $platformDir = $platformData['directory']
        $fullPlatformDir = Join-Path $OutputDir $platformDir

        # Try to fetch URL list to show count
        try {{
            $urllistPath = $platformData['urllist']
            $urllistUrl = Resolve-RelativeUrl $CollectionUrl $urllistPath

            if ($urllistUrl -match '^https?://') {{
                $urlListContent = Invoke-WebRequest -Uri $urllistUrl -UseBasicParsing
                $urls = $urlListContent.Content -split "`n" | Where-Object {{ $_ -and -not $_.StartsWith("#") }}
            }} else {{
                if (Test-Path $urllistUrl) {{
                    $urlListContent = Get-Content $urllistUrl
                    $urls = $urlListContent | Where-Object {{ $_ -and -not $_.StartsWith("#") }}
                }} else {{
                    $urls = @()
                }}
            }}

            Write-Host "  $fullPlatformDir ($($urls.Count) files)"
        }} catch {{
            Write-Host "  $fullPlatformDir (Could not fetch URL list)"
        }}
    }}

    Write-Host ""
    Read-Host "Press Enter to return to menu"
}}

# Download files for a platform
function Invoke-PlatformDownload {{
    param(
        [string]$PlatformName,
        [hashtable]$PlatformData
    )

    $platformDir = $PlatformData['directory']
    $shouldExtract = $PlatformData['extract'] -eq $true

    # Create platform directory
    $fullPlatformDir = Join-Path $OutputDir $platformDir
    if (!(Test-Path $fullPlatformDir)) {{
        New-Item -ItemType Directory -Path $fullPlatformDir | Out-Null
    }}

    # Resolve and fetch URL list
    $urllistPath = $PlatformData['urllist']
    $urllistUrl = Resolve-RelativeUrl $CollectionUrl $urllistPath

    try {{
        if ($urllistUrl -match '^https?://') {{
            $urlListContent = Invoke-WebRequest -Uri $urllistUrl -UseBasicParsing
            $urls = $urlListContent.Content -split "`n" | Where-Object {{ $_ -and -not $_.StartsWith("#") }}
        }} else {{
            $urlListContent = Get-Content $urllistUrl
            $urls = $urlListContent | Where-Object {{ $_ -and -not $_.StartsWith("#") }}
        }}

        if ($urls.Count -eq 0) {{
            Write-LogWarn "No URLs found for $PlatformName"
            return
        }}

        # Download all files
        Write-LogInfo "Downloading files for $PlatformName"
        foreach ($url in $urls) {{
            if (-not [string]::IsNullOrEmpty($url)) {{
                $filename = [System.IO.Path]::GetFileName($url)
                Write-LogInfo "Downloading $filename"
                try {{
                    Invoke-WebRequest -Uri $url -OutFile (Join-Path $fullPlatformDir $filename) -UseBasicParsing
                }} catch {{
                    Write-LogError "Failed to download $filename`: $_"
                }}
            }}
        }}

        # Extract if needed
        if ($shouldExtract) {{
            Write-LogInfo "Extracting files for $PlatformName"
            Set-Location $fullPlatformDir
            $zipFiles = Get-ChildItem *.zip
            foreach ($zipFile in $zipFiles) {{
                Write-LogInfo "Extracting $zipFile"
                try {{
                    Expand-Archive -Path $zipFile.FullName -DestinationPath . -Force
                    Remove-Item $zipFile.FullName
                }} catch {{
                    Write-LogError "Failed to extract $zipFile`: $_"
                }}
            }}
            Set-Location ..
        }}

    }} catch {{
        Write-LogError "Failed to fetch URL list for $PlatformName`: $_"
    }}
}}

# Main script
try {{
    # Fetch and parse TOML
    $tomlContent = Get-TomlContent $CollectionUrl
    $tomlData = ConvertFrom-Toml $tomlContent
    $platforms = Get-PlatformsFromToml $tomlData

    if ($platforms.Count -eq 0) {{
        Write-LogError "No platforms found in collection"
    }}

    # Initialize selected platforms
    if ($NonInteractive) {{
        $SelectedPlatforms = @($platforms.Keys)
    }} else {{
        $SelectedPlatforms = @($platforms.Keys)
        Show-Menu $platforms
    }}

    # Create output directory
    if (!(Test-Path $OutputDir)) {{
        New-Item -ItemType Directory -Path $OutputDir | Out-Null
    }}

    Set-Location $OutputDir

    # Download selected platforms
    Write-LogInfo "Starting download to $OutputDir"

    foreach ($platformName in $platforms.Keys) {{
        if ($SelectedPlatforms -contains $platformName) {{
            Invoke-PlatformDownload $platformName $platforms[$platformName]
        }}
    }}

    Write-LogInfo "Download completed successfully"

}} catch {{
    Write-LogError "Script failed: $_"
}}
