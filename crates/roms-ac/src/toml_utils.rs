use std::path::Path;
use std::fs;
use anyhow::Result;

pub fn discover_and_organize_platforms(collection_path: &str) -> Result<(Vec<String>, Vec<String>)> {
    let content = fs::read_to_string(collection_path)?;
    let parsed: toml::Value = toml::from_str(&content)?;
    let mut filter = Vec::new();
    let mut nofilter = Vec::new();

    // Helper to process table entries
    let mut process_table = |table: Option<&toml::value::Table>| {
        if let Some(tbl) = table {
            for (k, v) in tbl.iter() {
                // check skip_filtering flag
                let skip = v.get("skip_filtering").and_then(|s| s.as_bool()).unwrap_or(false);
                if skip {
                    nofilter.push(k.clone());
                } else {
                    filter.push(k.clone());
                }
            }
        }
    };

    process_table(parsed.get("roms").and_then(|v| v.as_table()));
    process_table(parsed.get("bios").and_then(|v| v.as_table()));

    Ok((filter, nofilter))
}

pub fn get_url_file_path(collection_path: &str, platform: &str) -> std::path::PathBuf {
    // Try to use urllist from platform config if present (resolve relative to repo root)
    let p = Path::new(collection_path);
    let content = fs::read_to_string(collection_path).unwrap_or_default();
    if let Ok(parsed) = toml::from_str::<toml::Value>(&content) {
        if let Some(platform_cfg) = parsed.get("roms").and_then(|t| t.get(platform)).or_else(|| parsed.get("bios").and_then(|t| t.get(platform))) {
            if let Some(urllist) = platform_cfg.get("urllist").and_then(|v| v.as_str()) {
                // Resolve relative to repo root by searching for config.toml or .git
                let mut dir = p.parent().unwrap_or(Path::new(".")).to_path_buf();
                for _ in 0..10 {
                    if dir.join("config.toml").exists() || dir.join(".git").exists() {
                        break;
                    }
                    if !dir.pop() { break; }
                }
                let resolved = dir.join(urllist);
                if let Some(parent) = resolved.parent() { let _ = std::fs::create_dir_all(parent); }
                return resolved;
            }
        }
    }

    // Fallback to previous behaviour
    let parent = p.parent().unwrap_or(Path::new("."));
    let base = p.file_name().and_then(|s| s.to_str()).unwrap_or("collection");
    parent.join(format!("{}.{}.txt", base, platform))
}

/// Get the repository base URL from config.toml
/// Used when generating remote download links in README files.
pub fn get_repo_base_url() -> Result<String> {
    get_toml_value("config.toml", "repo_base_url")
}

/// Get the collection directory path from config.toml
/// Searches for the repo root and reads the collection_directory setting from the config file.
pub fn get_collection_directory() -> Result<String> {
    // Find repository root by searching up the directory tree
    let current_dir = std::env::current_dir()?;
    let mut repo_root = current_dir.clone();

    // Search up to 10 levels up
    for _ in 0..10 {
        if repo_root.join("config.toml").exists() {
            // Found repo root with config file
            let config_path = repo_root.join("config.toml");
            return get_toml_value(&config_path.to_string_lossy(), "collection_directory");
        }
        if !repo_root.pop() {
            break;
        }
    }

    // No config.toml found in repository
    Err(anyhow::anyhow!("Could not find config.toml in repository root or parent directories"))
}

pub fn get_toml_value<T>(toml_path: &str, value_path: &str) -> Result<T>
where
    T: serde::de::DeserializeOwned,
{
    let config_content = fs::read_to_string(toml_path)?;
    let config: toml::Value = toml::from_str(&config_content)?;

    // Navigate the path
    let mut current = config;
    for key in value_path.split('.') {
        current = current.get(key).ok_or_else(|| {
            anyhow::anyhow!("Key '{}' not found in path '{}' of TOML file '{}'", key, value_path, toml_path)
        })?.clone();
    }

    serde::Deserialize::deserialize(current).map_err(|e| {
        anyhow::anyhow!("Failed to deserialize value at path '{}' in TOML file '{}': {}", value_path, toml_path, e)
    })
}
