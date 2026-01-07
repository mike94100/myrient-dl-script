use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::Result;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct CollectionToml {
    #[serde(default)]
    roms: BTreeMap<String, toml::Value>,
    #[serde(default)]
    bios: BTreeMap<String, toml::Value>,
}

pub fn discover_and_organize_platforms<P: AsRef<Path>>(collection_path: P) -> Result<(Vec<String>, Vec<String>)> {
    let content = fs::read_to_string(&collection_path)?;
    let parsed: toml::Value = toml::from_str(&content)?;

    let mut filter_platforms = Vec::new();
    let mut nofilter_platforms = Vec::new();

    if let Some(roms) = parsed.get("roms").and_then(|v| v.as_table()) {
        for (k, _v) in roms.iter() {
            filter_platforms.push(k.clone());
        }
    }
    if let Some(bios) = parsed.get("bios").and_then(|v| v.as_table()) {
        for (k, _v) in bios.iter() {
            filter_platforms.push(k.clone());
        }
    }

    // For now, treat all platforms as filter platforms and leave nofilter empty
    Ok((filter_platforms, nofilter_platforms))
}

pub fn get_url_file_path<P: AsRef<Path>>(collection_path: P, platform_name: &str) -> PathBuf {
    let coll = collection_path.as_ref();
    let parent = coll.parent().unwrap_or_else(|| Path::new("."));
    parent.join(format!("{}.{}.txt", coll.file_name().and_then(|s| s.to_str()).unwrap_or("collection"), platform_name))
}
