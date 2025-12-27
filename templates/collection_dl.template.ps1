# PowerShell ROM/BIOS Download Script
# Generated script for downloading files

# Global variables
$OutputDir = ""
$SelectedPlatforms = @()

# Platform configuration arrays
{PLATFORM_ARRAYS}

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
}}

# Interactive menu for platform and directory selection
function Show-Menu {{
    Clear-Host
    Write-Host "=== ROM/BIOS Download Script ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Current settings:"
    Write-Host "  Platforms: $(if ($SelectedPlatforms.Count -eq 0) {{ "None selected" }} else {{ $SelectedPlatforms -join ", " }})"
    Write-Host "  Output directory: $(if ([string]::IsNullOrEmpty($OutputDir)) {{ "Not set" }} else {{ $OutputDir }})"
    Write-Host ""
    Write-Host "Available platforms:"
    for ($i = 0; $i -lt $PlatformNames.Count; $i++) {{
        $platform = $PlatformNames[$i]
        $marker = if ($SelectedPlatforms -contains $platform) {{ "[✓]" }} else {{ "[ ]" }}
        Write-Host "  $marker $(($i+1))) $platform"
    }}
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  1) Select platforms"
    Write-Host "  2) Set output directory"
    Write-Host "  3) Continue with download"
    Write-Host "  4) Cancel"
    Write-Host ""
    $choice = Read-Host "Choose option (1-4)"
    switch ($choice) {{
        "1" {{ Select-Platforms }}
        "2" {{ Set-OutputDir }}
        "3" {{
            if ($SelectedPlatforms.Count -eq 0 -or [string]::IsNullOrEmpty($OutputDir)) {{
                Write-Host "Error: Please select platforms and set output directory first." -ForegroundColor Red
                Read-Host "Press Enter to continue"
                Show-Menu
                return
            }}
            Confirm-Download
            return
        }}
        "4" {{
            Write-Host "Download cancelled."
            exit 0
        }}
        default {{
            Write-Host "Invalid option. Please try again." -ForegroundColor Red
            Read-Host "Press Enter to continue"
            Show-Menu
        }}
    }}
}}

function Select-Platforms {{
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
    Show-Menu
}}

function Set-OutputDir {{
    Write-Host ""
    $currentDir = if ([string]::IsNullOrEmpty($OutputDir)) {{ "Not set" }} else {{ $OutputDir }}
    Write-Host "Current output directory: $currentDir"
    $newDir = Read-Host "Enter new output directory (press Enter for ~/Downloads)"
    if (-not [string]::IsNullOrEmpty($newDir)) {{
        $script:OutputDir = $newDir
    }} elseif ([string]::IsNullOrEmpty($OutputDir)) {{
        $script:OutputDir = "$HOME/Downloads"
    }}
    Show-Menu
}}

function Confirm-Download {{
    Write-Host ""
    Write-Host "Ready to download:"
    Write-Host "  Platforms: $($SelectedPlatforms -join ", ")"
    Write-Host "  Output directory: $OutputDir"
    Write-Host ""
    $confirm = Read-Host "Start download? (y/N)"
    if ($confirm -match "^[Yy]$") {{
        # Continue with download
    }} else {{
        Write-Host "Download cancelled."
        Show-Menu
        return
    }}
}}

# Initialize with defaults
$SelectedPlatforms = {DEFAULT_PLATFORMS}
$OutputDir = "$HOME/Downloads"

# Show initial menu
Show-Menu

Write-LogInfo "Starting {TOML_STEM} download to $OutputDir"

# Create output directory if it doesn't exist
if (!(Test-Path $OutputDir)) {{
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}}

Set-Location $OutputDir

# Function to process a single platform by index
function Process-Platform {{
    param([int]$Index)
    $platformName = $PlatformNames[$Index]
    $platformDir = $PlatformDirs[$Index]
    $platformUrl = $PlatformUrls[$Index]
    $shouldExtract = $PlatformExtracts[$Index]

    Write-LogInfo "Processing platform: $platformName"

    # Create platform directory
    if (!(Test-Path $platformDir)) {{
        New-Item -ItemType Directory -Path $platformDir | Out-Null
    }}

    # Download URL list and filter comments
    try {{
        $urlListContent = Invoke-WebRequest -Uri $platformUrl -UseBasicParsing | Select-Object -ExpandProperty Content
        $urls = $urlListContent -split "`n" | Where-Object {{ $_ -and -not $_.StartsWith("#") }} | ForEach-Object {{ $_.Trim() }}
    }} catch {{
        Write-LogError "Failed to download URL list for $platformName`: $_"
        return
    }}

    if ($urls.Count -eq 0) {{
        Write-LogWarn "No URLs found for $platformName"
        return
    }}

    # Download all files
    Write-LogInfo "Downloading files for $platformName"
    foreach ($url in $urls) {{
        if (-not [string]::IsNullOrEmpty($url)) {{
            $filename = [System.IO.Path]::GetFileName($url)
            Write-LogInfo "Downloading $filename"
            try {{
                Invoke-WebRequest -Uri $url -OutFile (Join-Path $platformDir $filename) -UseBasicParsing
            }} catch {{
                Write-LogError "Failed to download $filename`: $_"
            }}
        }}
    }}

    # Extract if needed
    if ($shouldExtract) {{
        Write-LogInfo "Extracting files for $platformName"
        Set-Location $platformDir
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

    Write-LogInfo "Completed $platformName"
}}

# Process selected platforms
for ($i = 0; $i -lt $PlatformNames.Count; $i++) {{
    $platformName = $PlatformNames[$i]
    if ($SelectedPlatforms -contains $platformName) {{
        Process-Platform $i
    }}
}}

Write-LogInfo "Download completed successfully"
exit 0
