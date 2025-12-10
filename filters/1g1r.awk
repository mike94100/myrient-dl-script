#!/usr/bin/awk -f
# ============================================================================
# 1G1R Awk Filter - Simple ROM filtering with deduplication
# ============================================================================
#
# Usage: awk -f filters/1g1r.awk file_list.txt
#        gen-platform-toml-awktest.sh -f filters/1g1r.awk [options] ...
#
# This filter excludes unwanted ROMs and includes only USA/World releases.
# It also performs intelligent deduplication, keeping the best version of each game.
#
# CONFIGURATION:
#   Set KEEP_ALL_REVISIONS = 1 to keep all game revisions instead of deduplicating
#   Set KEEP_ALL_REVISIONS = 0 to deduplicate (keep only best version)
#
# ============================================================================

BEGIN {
    # Configuration flags
    KEEP_ALL_REVISIONS = 0  # Set to 1 to keep all revisions, 0 to deduplicate

    # Arrays for maintaining ordered output
    count = 0
    delete all_games
    delete base_to_index
    delete seen
}

{
    filename = $0

    # Skip already excluded files (start with #)
    if (filename ~ /^#/) { print filename; next }

    # Exact deduplication - skip duplicate filenames
    if (filename in seen) { next }
    seen[filename] = 1

    # ============================================================================
    # EXCLUDE
    # ============================================================================

    # Exclude development/unreleased content
    if (filename ~ /\(Beta/) { all_games[++count] = "#" filename; next }
    if (filename ~ /\(Demo/) { all_games[++count] = "#" filename; next }
    if (filename ~ /\(Tech Demo/) { all_games[++count] = "#" filename; next }
    if (filename ~ /\(Proto/ || filename ~ /Proto\)/) { all_games[++count] = "#" filename; next }
    if (filename ~ /\(Sample/) { all_games[++count] = "#" filename; next }

    # Exclude unauthorized content
    if (filename ~ /\(Pirate/) { all_games[++count] = "#" filename; next }
    if (filename ~ /\(Unl/) { all_games[++count] = "#" filename; next }
    if (filename ~ /\(Hack/) { all_games[++count] = "#" filename; next }

    # Exclude technical files
    if (filename ~ /\[BIOS\]/) { all_games[++count] = "#" filename; next }
    if (filename ~ /\(Test Program/) { all_games[++count] = "#" filename; next }

    # Exclude specific collections
    #if (filename ~ /Retro Collection/) { all_games[++count] = "#" filename; next }
    #if (filename ~ /Limited Run Games/) { all_games[++count] = "#" filename; next }
    #if (filename ~ /Evercade/) { all_games[++count] = "#" filename; next }
    #if (filename ~ /Disney Classic Games/) { all_games[++count] = "#" filename; next }

    # Exclude if not English
    if (filename ~ /\(Ja\)/) { all_games[++count] = "#" filename; next }

    # Exclude if not USA, World, or English
    if (filename !~ /\(USA/ && filename !~ /\(World\)/ && filename !~ /\(En/) { all_games[++count] = "#" filename; next }

    # ============================================================================
    # DEDUPLICATION - Keep only the best version of each game
    # ============================================================================

    if (KEEP_ALL_REVISIONS == 1) {
        # Skip deduplication - include all files that pass other filters
        all_games[++count] = filename
    } else {
        # Extract base game name (everything before first parenthesis)
        base_name = extract_base_name(filename)

        # Check if we already have this game
        if (base_name in games) {
            # Compare versions with existing entry
            existing_version = games[base_name]["version"]
            current_version = extract_version(filename)

            if (is_better_version(current_version, existing_version)) {
                # This version is better - exclude the old one and keep this
                all_games[base_to_index[base_name]] = "#" all_games[base_to_index[base_name]]
                games[base_name]["filename"] = filename
                games[base_name]["version"] = current_version
                base_to_index[base_name] = ++count
                all_games[count] = filename
            } else {
                # This version is worse or equal - exclude it
                all_games[++count] = "#" filename
            }
        } else {
            # First occurrence of this game
            games[base_name]["filename"] = filename
            games[base_name]["version"] = extract_version(filename)
            base_to_index[base_name] = ++count
            all_games[count] = filename
        }
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function extract_base_name(filename) {
    # Remove file extension
    sub(/\.[^.]+$/, "", filename)

    # Extract everything before the first parenthesis
    if (match(filename, /\(/)) {
        filename = substr(filename, 1, RSTART-1)
    }

    # Clean up extra spaces
    gsub(/ +/, " ", filename)
    sub(/^ +/, "", filename)
    sub(/ +$/, "", filename)

    return filename
}

function extract_version(filename) {
    # Extract version info for comparison
    if (filename ~ /\(Rev [0-9]+\)/) {
        match(filename, /\(Rev ([0-9]+)\)/, arr)
        return "rev" arr[1]
    }
    if (filename ~ /\(v([0-9.]+)\)/) {
        match(filename, /\(v([0-9.]+)\)/, arr)
        return "v" arr[1]
    }
    # No version = lowest priority
    return ""
}

function is_better_version(new_ver, old_ver) {
    # Empty version is worse than any version
    if (old_ver == "") return 1
    if (new_ver == "") return 0

    # Rev versions are better than v versions
    if (new_ver ~ /^rev/ && old_ver ~ /^v/) return 1
    if (new_ver ~ /^v/ && old_ver ~ /^rev/) return 0

    # Compare same type versions
    if (new_ver ~ /^rev/ && old_ver ~ /^rev/) {
        new_num = substr(new_ver, 4)
        old_num = substr(old_ver, 4)
        return new_num > old_num
    }
    if (new_ver ~ /^v/ && old_ver ~ /^v/) {
        # Simple string comparison for versions
        return new_ver > old_ver
    }

    return 0
}

END {
    for (i = 1; i <= count; i++) {
        print all_games[i]
    }
}

# ============================================================================
# HOW TO MODIFY THIS FILTER
# ============================================================================
#
# To exclude more content:
#   Add new lines: if (filename ~ /\(pattern/) { print "#" filename; next }
#
# To change regions:
#   Modify has_usa/has_world checks, or add has_europe = (filename ~ /\(Europe\)/)
#
# To exclude specific games or franchises:
#   Uncomment and modify lines in the GAME NAME FILTERING section
#
# The deduplication automatically keeps the best version of each game based on:
#   - Rev versions (Rev 1 > Rev 0)
#   - V versions (v1.1 > v1.0)
#   - Any version > no version
#
# Examples:
#   if (filename ~ /\(japan/) { print "#" filename; next }  # Exclude Japan
#   if (filename ~ /Mario/) { print "#" filename; next }    # Exclude Mario games
#
# ============================================================================
