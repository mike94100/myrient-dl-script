# ============================================================================
# SED FILTER TEMPLATE
# ============================================================================
#
# This template demonstrates best practices for creating sed-based filters
# to exclude unwanted ROMs and include only desired ones.
#
# USAGE: gen-platform-toml.sh -f template_filter.sed [path] [output]
#
# Notes:
#   - EXTENDED REGEX: () for regex grouping, escaped \( and \) for literals
#   - ORDER MATTERS: Each command processes one line at a time, in order.
#   - BE SPECIFIC: More specific patterns trigger fewer false positves.
#   - DOCUMENT FILTERS: Add comments explaining each section
#   - REGION/LANGUAGE: USA & En are always first in tags.
#       Only need (En for both (En,Ja) and (En).
#       Need both (Ja & ,Ja for both (En,Ja) and (Ja).
#   - DUPLICATE SKIPS: /^#/b "branches to the end" or skips the rest of the
#       command if the string starts with # to avoid duplicate # for excludes.
#
# ============================================================================
# EXCLUDE (Comment out matching files)
# ============================================================================
# Use: /^#/b; /PATTERN\/s/^/#/
#
# Logic: If line already excluded (^#), skip. If matches exclude pattern,
# exclude by prefixing with #.
#
# ============================================================================
# INCLUDE (Comment out non-matching files)
# ============================================================================
# Use: /^#/b; /PATTERN1/b; /PATTERN2/b; s/^/#/
#
# Logic: If line already excluded (^#), skip. If matches ANY include pattern,
# branch (skip exclusion). Otherwise, exclude by commenting out.
#
# Multiple patterns = OR logic (matches any one)
# Multiple groups = AND logic (must match all groups)
#
# ============================================================================
# COMMON PATTERNS REFERENCE
# ============================================================================
#
# Regions: USA, World, Japan, Europe
# Languages: (En), (Fr), (De), (Es), (It), (Ja), (Zh)
# Release: (Beta), (Proto), (Demo), (Sample)
# Unofficial: (Pirate), (Unl), (Hack), (Aftermarket)
# Non-Games: [BIOS], (Kiosk)
# Collections:

# ============================================================================
# EXAMPLE 1: Non-Official/Non-Game Filter
# ============================================================================

# Exclude development/unreleased content
/^#/b; /(\(Beta)/s/^/#/
/^#/b; /(\(Proto)/s/^/#/
/^#/b; /(\(Demo)/s/^/#/
/^#/b; /(\(Sample)/s/^/#/

# Exclude unauthorized/pirated content
/^#/b; /(\(Pirate)/s/^/#/
/^#/b; /(\(Unl)/s/^/#/
/^#/b; /(\(Hack)/s/^/#/

# Exclude system/technical files
/^#/b; /(\[BIOS\])/s/^/#/
/^#/b; /(\(Test Program\))/s/^/#/

# ============================================================================
# EXAMPLE 2: Region Filters
# ============================================================================

# USA only
 /^#/b; /(\(USA)/b; s/^/#/

# Europe only
 /^#/b; /(\(Europe)/b; s/^/#/

# USA or World
 /^#/b; /(\(USA)/b; /(\(World\))/b; s/^/#/

# ============================================================================
# EXAMPLE 3: Language Filters
# ============================================================================

# Include English games
 /^#/b; /\(En\)/b; s/^/#/

# Exclude Japanese games
 /^#/b; /(\(Japan\))/s/^/#/
# Re-include Japan games with English tags
 /(\(Japan\))/b; /\(En\)/b; s/^/#/

# ============================================================================
# EXAMPLE 4: Game Filters
# ============================================================================

# Exclude specific games by name
 /^#/b; /Bad Game/s/^/#/
 /^#/b; /Another Bad Game/s/^/#/

# Include only specific franchises
 /^#/b; /Mario/b; /Zelda/b; /Pokemon/b; s/^/#/

# ============================================================================
# EXAMPLE 5: Tag Filters
# ============================================================================

# Exclude certain collections/editions
 /^#/b; /\(Retro-Bit\)/s/^/#/
 /^#/b; /\(Limited Run Games\)/s/^/#/
 /^#/b; /\(Evercade\)/s/^/#/

# Exclude enhanced/remastered versions (keep originals)
 /^#/b; /\(Castlevania Anniversary Collection\)/s/^/#/
 /^#/b; /\(Collection of Mana\)/s/^/#/

# ============================================================================
# EXAMPLE 6: Other Filters
# ============================================================================

# Exclude games with multiple regions in filename
 /\(USA, Europe\)/s/^/#/

# Include only original releases (exclude ports/remakes)
 /^#/b; /Genesis/s/^/#/; /SNES/s/^/#/; s/^/#/
