use anyhow::Result;
use regex::Regex;
use std::collections::HashMap;
use std::fs;

pub struct CollectionFilter {
    config: toml::Value,
}

impl CollectionFilter {
    pub fn new(collection_path: &str) -> Result<Self> {
        let content = fs::read_to_string(collection_path)?;
        let parsed: toml::Value = toml::from_str(&content)?;
        Ok(Self { config: parsed })
    }

    fn collect_platforms(&self) -> HashMap<String, toml::Value> {
        let mut platforms = HashMap::new();
        if let Some(table) = self.config.get("roms").and_then(|v| v.as_table()) {
            for (k, v) in table.iter() { platforms.insert(k.clone(), v.clone()); }
        }
        if let Some(table) = self.config.get("bios").and_then(|v| v.as_table()) {
            for (k, v) in table.iter() { platforms.insert(k.clone(), v.clone()); }
        }
        platforms
    }

    fn get_platform_config(&self, platform: &str) -> Option<&toml::Value> {
        if let Some(t) = self.config.get("roms").and_then(|v| v.get(platform)) { return Some(t); }
        if let Some(t) = self.config.get("bios").and_then(|v| v.get(platform)) { return Some(t); }
        None
    }

    fn global_filters(&self) -> toml::value::Table {
        self.config.get("filters").and_then(|v| v.as_table()).cloned().unwrap_or_default()
    }

    fn get_platform_filters(&self, platform: &str) -> toml::value::Table {
        let mut filters = self.global_filters();
        if let Some(cfg) = self.get_platform_config(platform).and_then(|v| v.as_table()) {
            for key in ["include", "exclude", "deduplicate"].iter() {
                if let Some(val) = cfg.get(*key) { filters.insert(key.to_string(), val.clone()); }
            }
        }
        filters
    }

    fn should_skip_filtering(&self, platform: &str) -> bool {
        self.get_platform_config(platform)
            .and_then(|v| v.get("skip_filtering"))
            .and_then(|b| b.as_bool())
            .unwrap_or(false)
    }

    pub fn filter_files(&self, platform: &str, files: &[String]) -> Vec<String> {
        if self.should_skip_filtering(platform) { return files.to_vec(); }

        let filters = self.get_platform_filters(platform);

        let mut filtered: Vec<String> = Vec::new();
        let mut seen = std::collections::HashSet::new();
        let mut games: HashMap<String, (String, String)> = HashMap::new(); // base -> (filename, version)
        let mut base_to_index: HashMap<String, usize> = HashMap::new();

        for filename in files.iter() {
            if filename.starts_with('#') { filtered.push(filename.clone()); continue; }

            if seen.contains(filename) { continue; }
            seen.insert(filename.clone());

            if !self.should_include(filename, &filters) {
                filtered.push(format!("#{}", filename));
                continue;
            }

            let dedup = filters.get("deduplicate").and_then(|v| v.as_bool()).unwrap_or(true);
            if !dedup {
                filtered.push(filename.clone());
            } else {
                self.deduplicate(filename, &mut filtered, &mut games, &mut base_to_index);
            }
        }

        filtered
    }

    fn should_include(&self, filename: &str, filters: &toml::value::Table) -> bool {
        // Exclude if any match
        let exclude_patterns = filters.get("exclude").and_then(|v| v.as_array()).cloned();
        if let Some(ex) = exclude_patterns {
            for p in ex.iter().filter_map(|x| x.as_str()) { if filename.contains(p) { return false; } }
        }

        // Handle includes (grouped AND logic)
        let include_groups = Self::parse_filter_groups(filters.get("include"));
        if !include_groups.is_empty() {
            return include_groups.iter().all(|group| {
                group.iter().any(|pattern| filename.contains(pattern))
            });
        }

        true
    }

    fn parse_filter_groups(filter_value: Option<&toml::Value>) -> Vec<Vec<String>> {
        let mut groups = Vec::new();

        if let Some(arr) = filter_value.and_then(|v| v.as_array()) {
            for item in arr {
                if let Some(nested_arr) = item.as_array() {
                    // Grouped format: [[patterns]]
                    let group: Vec<String> = nested_arr.iter()
                        .filter_map(|v| v.as_str().map(|s| s.to_string()))
                        .collect();
                    if !group.is_empty() {
                        groups.push(group);
                    }
                } else if let Some(pattern) = item.as_str() {
                    // Simple format: ["pattern"] - treat as single-item group
                    groups.push(vec![pattern.to_string()]);
                }
            }
        }

        groups
    }

    fn deduplicate(&self, filename: &str, filtered: &mut Vec<String>, games: &mut HashMap<String, (String, String)>, base_to_index: &mut HashMap<String, usize>) {
        let base = Self::extract_base_name(filename);
        if let Some((existing_filename, existing_version)) = games.get(&base).cloned() {
            let current_version = Self::extract_version(filename);
            if Self::is_better_version(&current_version, &existing_version) {
                if let Some(&idx) = base_to_index.get(&base) { filtered[idx] = format!("#{}", filtered[idx]); }
                base_to_index.insert(base.clone(), filtered.len());
                games.insert(base.clone(), (filename.to_string(), current_version));
                filtered.push(filename.to_string());
            } else {
                filtered.push(format!("#{}", filename));
            }
        } else {
            games.insert(base.clone(), (filename.to_string(), Self::extract_version(filename)));
            base_to_index.insert(base, filtered.len());
            filtered.push(filename.to_string());
        }
    }

    fn extract_base_name(filename: &str) -> String {
        let re_ext = Regex::new(r"\.[^.]+$").unwrap();
        let mut s = re_ext.replace(filename, "").to_string();
        if let Some(pos) = s.find('(') { s = s[..pos].to_string(); }
        s.split_whitespace().collect::<Vec<&str>>().join(" ").trim().to_string()
    }

    fn extract_version(filename: &str) -> String {
        let re_rev = Regex::new(r"\(Rev (\d+)\)").unwrap();
        if let Some(caps) = re_rev.captures(filename) { return format!("rev{}", &caps[1]); }
        let re_v = Regex::new(r"\(v([\d.]+)\)").unwrap();
        if let Some(caps) = re_v.captures(filename) { return format!("v{}", &caps[1]); }
        String::new()
    }

    fn is_better_version(new_ver: &str, old_ver: &str) -> bool {
        if old_ver.is_empty() { return true; }
        if new_ver.is_empty() { return false; }
        if new_ver.starts_with("rev") && old_ver.starts_with('v') { return true; }
        if new_ver.starts_with('v') && old_ver.starts_with("rev") { return false; }
        if new_ver.starts_with("rev") && old_ver.starts_with("rev") {
            let a = new_ver[3..].parse::<i64>().unwrap_or(0);
            let b = old_ver[3..].parse::<i64>().unwrap_or(0);
            return a > b;
        }
        if new_ver.starts_with('v') && old_ver.starts_with('v') { return new_ver > old_ver; }
        false
    }
}

// Helper free functions
pub fn filter_collection_apply(collection_path: &str, platform_name: &str, files: &[String]) -> Result<Vec<String>> {
    let f = CollectionFilter::new(collection_path)?;
    Ok(f.filter_files(platform_name, files))
}

pub fn get_all_platforms(collection_path: &str) -> Result<Vec<String>> {
    let f = CollectionFilter::new(collection_path)?;
    Ok(f.collect_platforms().keys().cloned().collect())
}
