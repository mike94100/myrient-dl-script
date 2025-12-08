#!/usr/bin/awk -f
# ============================================================================
# ROM Filter Template - Customize this for your filtering needs
# ============================================================================
#
# Usage: awk -f template_filter.awk file_list.txt
#        gen-platform-toml-awktest.sh -f template_filter.awk [options] ...
#
# Copy this file and modify the sections below to create custom filters.
#
# Notes:
#   
#
# ============================================================================

BEGIN {
    # Configuration flags
    KEEP_ALL_REVISIONS = 0  # Set to 1 to keep all revisions, 0 to deduplicate

    # Games tracking for deduplication (only used if KEEP_ALL_REVISIONS = 0)
    if (KEEP_ALL_REVISIONS == 0) { delete games }
}

{
    filename = $0

    # Skip already excluded files (start with #)
    if (filename ~ /^#/) { print filename; next }

    # ============================================================================
    # EXCLUDE
    # ============================================================================

    # Exclude game if any of the following apply
    if (filename ~ /EXCLUDE1/ { print "#" filename; next }
    if (filename ~ /EXCLUDE2/ { print "#" filename; next }
    if (filename ~ /EXCLUDE3/ { print "#" filename; next }

    # Exclude game if any of the following apply (Same as above but on one line)
    if (filename ~ /EXCLUDE1/ || filename ~ /EXCLUDE2/ { print "#" filename; next }

    # Exclude game if all of the following apply
    if (filename ~ /EXCLUDE1/ && filename ~ /EXCLUDE2/ { print "#" filename; next }

    # EXAMPLES
    # Exclude Unreleased ROMs - Matches (Beta & (Proto
    if (filename ~ /\(Beta/ || filename ~ /\(Proto/) { print "#" filename; next }

    # ============================================================================
    # INCLUDE
    # ============================================================================

    # Include game if any of the following apply
    if (filename !~ /EXCLUDE1/ { print "#" filename; next }
    if (filename !~ /EXCLUDE2/ { print "#" filename; next }
    if (filename !~ /EXCLUDE3/ { print "#" filename; next }

    # Include game if any of the following apply (Same as above but on one line)
    if (filename !~ /EXCLUDE1/ || filename !~ /EXCLUDE2/ { print "#" filename; next }

    # Include game if all of the following apply
    if (filename !~ /EXCLUDE1/ && filename !~ /EXCLUDE2/ { print "#" filename; next }

    EXAMPLES
    # Include specific regions - Matches (USA & (World)
    if (filename !~ /\(USA/ || filename !~ /\(World\)/) { print "#" filename; next }
    # Include specific game names - Matches Pokemon & Mario
    if (filename !~ /Pokemon/ || filename !~ /Mario/) { print "#" filename; next }

    # ============================================================================
    # DEDUPLICATION - Keep only the best version of each game
    # ============================================================================

    if (KEEP_ALL_REVISIONS == 1) {
        # Skip deduplication - include all files that pass other filters
        print filename
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
                print "#" games[base_name]["filename"]
                games[base_name]["filename"] = filename
                games[base_name]["version"] = current_version
                print filename
            } else {
                # This version is worse or equal - exclude it
                print "#" filename
            }
        } else {
            # First occurrence of this game
            games[base_name]["filename"] = filename
            games[base_name]["version"] = extract_version(filename)
            print filename
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

# ============================================================================
# HOW TO MODIFY THIS TEMPLATE
# ============================================================================
#
# 1. Copy this file: cp templates/template_filter.awk filters/my_filter.awk
# 2. Modify the configuration flags at the top
# 3. Uncomment/modify the filtering patterns in each section
# 4. Test with: awk -f filters/my_filter.awk sample_files.txt
# 5. Use with: gen-platform-toml-awktest.sh -f filters/my_filter.awk [options]
#
# ============================================================================
