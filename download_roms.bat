@echo off
REM Myrient ROM Downloader Bootstrap Script for Windows
REM Downloads Python code from main repo and handles TOML resolution

setlocal enabledelayedexpansion

REM Default values
set "DEFAULT_TOML=https://raw.githubusercontent.com/mike94100/myrient-dl-script/main/dl/sample/sample.toml"
set "TOML_SOURCE=%DEFAULT_TOML%"
set "OUTPUT_DIR=%USERPROFILE%\Downloads\roms"

REM Parse command line flags
:parse_args
if "%~1"=="" goto :end_parse
if "%~1"=="-t" (
    set "TOML_SOURCE=%~2"
    shift & shift
    goto :parse_args
)
if "%~1"=="--toml" (
    set "TOML_SOURCE=%~2"
    shift & shift
    goto :parse_args
)
if "%~1"=="-o" (
    set "OUTPUT_DIR=%~2"
    shift & shift
    goto :parse_args
)
if "%~1"=="--output" (
    set "OUTPUT_DIR=%~2"
    shift & shift
    goto :parse_args
)
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help
echo Unknown option: %~1
echo Use --help for usage information
exit /b 1

:show_help
echo Usage: %0 [-t^|--toml TOML_URL] [-o^|--output OUTPUT_DIR]
echo.
echo Download ROMs using Myrient ROM Downloader
echo.
echo Options:
echo   -t, --toml TOML_URL      URL or path to TOML file (default: sample ROMs)
echo   -o, --output OUTPUT_DIR  Output directory (default: %%USERPROFILE%%\Downloads\roms)
echo   -h, --help              Show this help message
echo.
echo Examples:
echo   %0  # Download sample ROMs to default location
echo   %0 --toml https://example.com/custom.toml
echo   %0 --output "C:\My ROMs"
echo   %0 -t https://example.com/custom.toml -o "C:\My ROMs"
exit /b 0

:end_parse

echo Myrient ROM Downloader
echo TOML Source: %TOML_SOURCE%
echo Output Directory: %OUTPUT_DIR%
echo.

REM Create temp directory
for /f "tokens=*" %%i in ('powershell -command "& { $temp = [System.IO.Path]::GetTempPath(); $guid = [guid]::NewGuid().ToString(); $path = Join-Path $temp $guid; New-Item -ItemType Directory -Path $path -Force; Write-Output $path }"') do set "TEMP_DIR=%%i"

REM Cleanup on exit
powershell -command "& { $exitCode = $LASTEXITCODE; Remove-Item -Recurse -Force '%TEMP_DIR%' -ErrorAction SilentlyContinue; exit $exitCode }" 2>nul
if %ERRORLEVEL% neq 0 goto :cleanup

echo Step 1: Downloading Python code from main repo...
cd /d "%TEMP_DIR%"
git clone --depth=1 --quiet https://github.com/mike94100/myrient-dl-script.git repo 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Git clone failed. Make sure Git is installed.
    goto :cleanup
)
cd repo

echo Step 2: Installing dependencies...
python -m pip install --quiet -r requirements.txt 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies
    goto :cleanup
)

echo Step 3: Processing TOML configuration...

REM Function to download file
goto :main

:download_file
    set "url=%~1"
    set "dest=%~2"
    REM Try curl first, then PowerShell
    curl -s -L "%url%" -o "%dest%" 2>nul
    if %ERRORLEVEL% neq 0 (
        powershell -command "& { try { Invoke-WebRequest -Uri '%url%' -OutFile '%dest%' -UseBasicParsing } catch { exit 1 } }"
        if !ERRORLEVEL! neq 0 (
            echo ERROR: Failed to download %url%
            goto :cleanup
        )
    )
    goto :eof

:resolve_url
    set "base=%~1"
    set "rel=%~2"

    REM If rel starts with http, it's already absolute
    echo %rel% | findstr /b "http" >nul
    if %ERRORLEVEL% equ 0 (
        set "resolved=%rel%"
        goto :eof
    )

    REM Remove filename from base URL to get directory
    for %%i in ("%base%") do set "base_dir=%%~dpi"
    set "base_dir=%base_dir:~0,-1%"

    REM If rel starts with /, it's absolute from domain
    echo %rel% | findstr /b "/" >nul
    if %ERRORLEVEL% equ 0 (
        REM Extract protocol and domain from base
        for /f "tokens=1,2 delims=://" %%a in ("%base%") do (
            set "proto=%%a"
            for /f "tokens=1 delims=/" %%c in ("%%b") do set "domain=%%c"
        )
        set "resolved=%proto%://%domain%%rel%"
    ) else (
        REM Relative path - combine with base directory
        set "resolved=%base_dir%/%rel%"
    )
    goto :eof

:is_meta_toml
    set "file=%~1"
    findstr "platform_tomls" "%file%" >nul 2>&1
    goto :eof

:main
REM Download and process TOML
set "TOML_FILE=%TEMP_DIR%\toml_source.toml"
call :download_file "%TOML_SOURCE%" "%TOML_FILE%"

call :is_meta_toml "%TOML_FILE%"
if %ERRORLEVEL% equ 0 (
    echo Detected meta TOML - downloading platform TOMLs...

    REM Platform TOMLs will be downloaded directly to temp dir
    set "PLATFORM_DIR=%TEMP_DIR%"

    REM Extract platform_tomls array and download each
    REM This uses PowerShell for better TOML parsing
    for /f "usebackq tokens=*" %%i in (`powershell -command "& { $toml = Get-Content '%TOML_FILE%' -Raw; $matches = [regex]::Matches($toml, 'platform_tomls\s*=\s*\[(.*?)\]', [System.Text.RegularExpressions.RegexOptions]::Singleline); if ($matches.Count -gt 0) { $content = $matches[0].Groups[1].Value; $refs = [regex]::Matches($content, '\"([^\""]*)\"', [System.Text.RegularExpressions.RegexOptions]::Multiline); $refs | ForEach-Object { $_.Groups[1].Value } } }"`) do (
        set "platform_ref=%%i"
        if defined platform_ref (
            call :resolve_url "%TOML_SOURCE%" "!platform_ref!"
            set "resolved_url=!resolved!"

            REM Download to local file (preserve directory structure)
            set "local_file=%PLATFORM_DIR%\!platform_ref!"
            powershell -command "& { $dir = Split-Path '!local_file!'; if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null } }"
            echo Downloading !resolved_url! -^> !local_file!
            call :download_file "!resolved_url!" "!local_file!"

            REM Store local path for meta TOML
            set "local_paths=!local_paths!\"!local_file!\", "
        )
    )

    REM Create new meta TOML with local paths
    set "NEW_META=%TEMP_DIR%\meta_local.toml"
    copy "%TOML_FILE%" "%NEW_META%" >nul

    REM Update meta TOML with local paths
    set "local_paths=platform_tomls = [!local_paths:~0,-2!]"
    REM Use PowerShell for the replacement since batch sed is limited
    powershell -command "& { $content = Get-Content '%NEW_META%' -Raw; $content -replace 'platform_tomls\s*=\s*\[.*?\]', '!local_paths!' | Set-Content '%NEW_META%' }"

    set "FINAL_TOML=%NEW_META%"
) else (
    echo Using platform TOML directly
    set "FINAL_TOML=%TOML_FILE%"
)

echo Step 4: Starting ROM download...
echo Using TOML: %FINAL_TOML%
echo Output: %OUTPUT_DIR%
echo.

REM Run the download
python myrient_dl.py "%FINAL_TOML%" -o "%OUTPUT_DIR%"

if %ERRORLEVEL% equ 0 (
    echo.
    echo Download complete! ROMs saved to: %OUTPUT_DIR%
) else (
    echo.
    echo ERROR: Download failed
    goto :cleanup
)

:cleanup
REM Cleanup temp directory
if exist "%TEMP_DIR%" (
    rmdir /s /q "%TEMP_DIR%" 2>nul
)
goto :eof
