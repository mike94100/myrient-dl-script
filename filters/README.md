# ROM Filters

This directory contains filter files for `gen-platform-toml.sh`.

## Filter Types

### Sed-Based Filters (Simple, Fast)
- Use with: `gen-platform-toml.sh -f filters/filter.sed`
- Good for: Basic pattern matching and region filtering
- See: [template_filter.sed](../templates/template_filter.sed) for examples.

### Awk-Based Filters (Advanced, with Deduplication)
- Use with: `gen-platform-toml-awktest.sh -f filters/filter.awk`
- Good for: Complex logic, version comparison, deduplication
- See: [template_filter.awk](../templates/template_filter.awk) for examples

## Quick Start

```bash
# Use the 1G1R filter (excludes betas/demos, includes USA/World)
gen-platform-toml.sh -f filters/1g1r.awk "/files/No-Intro/Nintendo - Game Boy/" gb.toml
```
