# ROM Filters

This directory contains filter files for `gen-platform-toml.sh` and `gen-platform-toml-awktest.sh`.

## Filter Types

### Sed-Based Filters (Simple, Fast)
- Use with: `gen-platform-toml.sh -f filters/1g1r.sed`
- Good for: Basic pattern matching and region filtering
- See: `templates/template_filter.sed` for examples

### Awk-Based Filters (Advanced, with Deduplication)
- Use with: `gen-platform-toml-awktest.sh -f filters/1g1r.awk`
- Good for: Complex logic, version comparison, deduplication
- See: `filters/README.awk` for comprehensive documentation

## Quick Start

```bash
# Use the 1G1R filter (excludes betas/demos, includes USA/World)
gen-platform-toml.sh -f filters/1g1r.sed "/files/No-Intro/Nintendo - Game Boy/" gb.toml

# Test a filter on sample data
echo -e "Game (USA).zip\nGame (Beta).zip" | sed -E -f filters/1g1r.sed
```

## Creating Custom Filters

1. **Copy the template**: `cp templates/template_filter.sed filters/my_filter.sed`
2. **Edit the patterns** to match your desired criteria

## Filter Types

- **`1g1r.sed`**: One Game, One ROM - excludes unofficial content, includes USA/World regions
- **`exclude_unofficial.sed`**: Excludes betas, demos, pirates, etc.
- **`include_USA.sed`**: Includes only USA or World games

## Syntax Reference

```bash
# Exclude pattern
/^#/b; /PATTERN/s/^/#/

# Include pattern (OR logic)
/^#/b; /PATTERN1/b; /PATTERN2/b; s/^/#/

# Include pattern (AND logic - multiple groups)
/^#/b; /PATTERN1/b; s/^/#/
/^#/b; /PATTERN2/b; s/^/#/
```

See **[template_filter.sed](../templates/template_filter.sed)** for comprehensive examples and best practices.
