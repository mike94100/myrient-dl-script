use anyhow::Result;
use std::path::{Path};
use std::fs;
use std::collections::{BTreeMap, HashMap};
use percent_encoding::percent_decode_str;
use regex::Regex;
use byte_unit::{Byte, UnitType};

fn parse_url_file_content(url_file: &Path) -> Result<(Vec<String>, Vec<String>)> {
    let mut included = Vec::new();
    let mut excluded = Vec::new();
    let s = fs::read_to_string(url_file)?;
    for line in s.lines().map(|l| l.trim()).filter(|l| !l.is_empty()) {
        if line.starts_with('#') {
            if line.starts_with("#http") {
                if let Some(seg) = line[1..].rsplit('/').next() { excluded.push(seg.to_string()); }
            }
        } else {
            if line.starts_with("http") { if let Some(seg) = line.rsplit('/').next() { included.push(seg.to_string()); } }
        }
    }
    Ok((included, excluded))
}

fn extract_sizes_from_html(html: &str, files: &[String]) -> BTreeMap<String,String> {
    let mut map = BTreeMap::new();
    for f in files.iter() {
        let decoded = percent_decode_str(f).decode_utf8_lossy();
        let pat = regex::escape(&decoded);
        // Use a raw string with # to allow literal double quotes inside the pattern
        let re_s = Regex::new(&format!(r#"<a[^>]*>{}</a>\s*</td>\s*<td[^>]*class="size"[^>]*>([^<]+)</td>"#, pat)).unwrap();
        if let Some(c) = re_s.captures(html) {
            let s = c.get(1).map(|m| m.as_str().trim().to_string()).unwrap_or_default();
            if !s.is_empty() && s != "-" { map.insert(decoded.to_string(), s); }
        }
    }
    map
}

fn organize_files_by_game(decoded_files: &[String], file_sizes: &BTreeMap<String,String>) -> BTreeMap<String, Vec<serde_json::Value>> {
    let mut groups: BTreeMap<String, Vec<serde_json::Value>> = BTreeMap::new();
    // Removed unused regex and simplify loop
    for df in decoded_files.iter() {
        let name = df.clone();
        let name_no_ext = Regex::new(r"\.[^.]+$").unwrap().replace(&name, "").to_string();
        let game_name = if let Some(pos) = name_no_ext.find('(') { name_no_ext[..pos].trim().to_string() } else { name_no_ext.trim().to_string() };
        let tags_re = Regex::new(r"\([^)]*\)").unwrap();
        let tags = tags_re.find_iter(&name_no_ext).map(|m| m.as_str()).collect::<Vec<_>>().join(" ");
        let size = file_sizes.get(df).cloned().unwrap_or_else(|| "Unknown".to_string());
        let size_bytes = if size == "Unknown" { 0 } else { Byte::parse_str(&size, true).map(|b| b.as_u128() as u64).unwrap_or(0) };
        let entry = serde_json::json!({"filename": df, "decoded_filename": df, "tags": tags, "size": size, "size_bytes": size_bytes});
        groups.entry(game_name).or_default().push(entry);
    }
    groups
}

fn build_platform_data_structure(platform_name: &str, included_files: &[String], excluded_files: &[String], game_groups: &BTreeMap<String, Vec<serde_json::Value>>, total_bytes: u64, source_url: &str) -> serde_json::Value {
    serde_json::json!({
        "platform_name": platform_name,
        "included_files": included_files,
        "excluded_files": excluded_files,
        "game_groups": game_groups,
        "total_files": included_files.len(),
        "total_bytes": total_bytes,
        "source_url": source_url
    })
}

fn extract_collection_metadata(collection_path: &Path) -> Result<(String, String)> {
    let content = fs::read_to_string(collection_path)?;
    let parsed: toml::Value = toml::from_str(&content)?;
    let title = parsed.get("title").and_then(|v| v.as_str()).unwrap_or("ROM Collection").to_string();
    let description = parsed.get("description").and_then(|v| v.as_str()).unwrap_or("A collection of ROM files for various gaming platforms.").to_string();
    Ok((title, description))
}

fn process_platform_data(collection_path: &Path, parsed: &toml::Value) -> Result<(BTreeMap<String, serde_json::Value>, usize, u64)> {
    let mut roms = BTreeMap::new();
    if let Some(t) = parsed.get("roms").and_then(|v| v.as_table()) {
        for (k,v) in t { roms.insert(k.clone(), v.clone()); }
    }

    let mut total_files_all = 0usize;
    let mut total_bytes_all: u64 = 0;
    let mut platform_data: BTreeMap<String, serde_json::Value> = BTreeMap::new();

    for (platform, cfg) in roms.iter() {
        let url_file = crate::toml_utils::get_url_file_path(collection_path.to_str().unwrap(), platform);
        if !url_file.exists() { continue; }
        let (included, excluded) = parse_url_file_content(&url_file)?;
        total_files_all += included.len();
        let source_url = cfg.get("url").and_then(|v| v.as_str()).unwrap_or("");
        let mut file_sizes = BTreeMap::new();
        if !included.is_empty() && !source_url.is_empty() {
            if let Ok(resp) = reqwest::blocking::get(source_url) {
                if let Ok(html) = resp.text() { file_sizes = extract_sizes_from_html(&html, &included); }
            }
        }
        let decoded: Vec<String> = included.iter().map(|f| percent_decode_str(f).decode_utf8_lossy().to_string()).collect();
        let groups = organize_files_by_game(&decoded, &file_sizes);
        let total_bytes = file_sizes.values().map(|s| if s.trim().is_empty() || s.trim() == "-" { 0 } else { Byte::parse_str(s, true).map(|b| b.as_u128() as u64).unwrap_or(0) }).sum::<u64>();
        total_bytes_all += total_bytes;
        let data = build_platform_data_structure(platform, &included, &excluded, &groups, total_bytes, source_url);
        platform_data.insert(platform.clone(), data);
    }

    Ok((platform_data, total_files_all, total_bytes_all))
}

fn build_directory_structure(platform_data: &BTreeMap<String, serde_json::Value>) -> String {
    let mut directory_structure = String::new();
    directory_structure.push_str("```\n└── roms/\n");
    for (pname, pdata) in platform_data.iter() {
        let total_files = pdata.get("total_files").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
        let total_bytes = pdata.get("total_bytes").and_then(|v| v.as_u64()).unwrap_or(0);
        let size_str = if total_bytes == 0 {
            "Unknown".to_string()
        } else {
            let iec = Byte::from_u128(total_bytes as u128).unwrap().get_appropriate_unit(UnitType::Binary).to_string();
            let si = Byte::from_u128(total_bytes as u128).unwrap().get_appropriate_unit(UnitType::Decimal).to_string();
            format!("{} ({})", iec, si)
        };
        directory_structure.push_str(&format!("    ├── {}/ ({} files, {})\n", pname, total_files, size_str));
    }
    directory_structure.push_str("```");
    directory_structure
}

fn build_rom_files_section(platform_data: &BTreeMap<String, serde_json::Value>) -> String {
    let mut rom_files = String::new();
    for (pname, pdata) in platform_data.iter() {
        let game_groups = pdata.get("game_groups").cloned().unwrap_or(serde_json::json!({}));
        if game_groups.as_object().map(|o| o.is_empty()).unwrap_or(true) { continue; }
        rom_files.push_str(&format!("<details>\n<summary>{}</summary>\n\n", pname));
        if let Some(obj) = game_groups.as_object() {
            for (_gname, files) in obj.iter() {
                if let Some(arr) = files.as_array() {
                    for fi in arr.iter() {
                        let filename = fi.get("decoded_filename").and_then(|v| v.as_str()).unwrap_or("");
                        let size = fi.get("size").and_then(|v| v.as_str()).unwrap_or("Unknown");
                        rom_files.push_str(&format!("  - {} ({})\n", filename, size));
                    }
                }
            }
        }
        rom_files.push_str("</details>\n\n");
    }
    rom_files
}

fn build_bios_section(platform_data: &BTreeMap<String, serde_json::Value>) -> (usize, String) {
    let mut bios_platform_count = 0;
    let mut bios_files = String::new();

    for (pname, pdata) in platform_data.iter() {
        let game_groups = pdata.get("game_groups").cloned().unwrap_or(serde_json::json!({}));
        if let Some(obj) = game_groups.as_object() {
            let has_bios = obj.values().any(|files| {
                files.as_array().unwrap_or(&Vec::new()).iter().any(|file| {
                    file.get("filename").and_then(|f| f.as_str()).unwrap_or("").to_lowercase().contains("bios")
                })
            });

            if has_bios {
                bios_platform_count += 1;
                bios_files.push_str(&format!("<details>\n<summary>{}</summary>\n\n", pname));
                for (_gname, files) in obj.iter() {
                    if let Some(arr) = files.as_array() {
                        for fi in arr.iter() {
                            let filename = fi.get("filename").and_then(|v| v.as_str()).unwrap_or("");
                            if filename.to_lowercase().contains("bios") {
                                let size = fi.get("size").and_then(|v| v.as_str()).unwrap_or("Unknown");
                                bios_files.push_str(&format!("  - {} ({})\n", filename, size));
                            }
                        }
                    }
                }
                bios_files.push_str("</details>\n\n");
            }
        }
    }

    (bios_platform_count, bios_files)
}

fn generate_collection_urls(collection_path: &str) -> (String, String) {
    let collection_toml_local = collection_path;
    let collection_toml_remote = collection_toml_local.replace("collections/", "https://raw.githubusercontent.com/mike94100/roms-as-code/main/collections/");
    (collection_toml_local.to_string(), collection_toml_remote)
}

fn prepare_template_data(
    title: String,
    description: String,
    platform_data: &BTreeMap<String, serde_json::Value>,
    total_files_all: usize,
    total_bytes_all: u64,
    bios_platform_count: usize,
    directory_structure: String,
    rom_files: String,
    bios_files: String,
    collection_toml_local: String,
    collection_toml_remote: String,
) -> HashMap<String, String> {
    let mut data = HashMap::new();

    data.insert("TITLE".to_string(), title);
    data.insert("DESCRIPTION".to_string(), description);
    data.insert("GENERATED_DATE".to_string(), chrono::Utc::now().format("%Y-%m-%d %H:%M:%S UTC").to_string());
    data.insert("ROM_PLATFORM_COUNT".to_string(), platform_data.len().to_string());
    data.insert("BIOS_PLATFORM_COUNT".to_string(), bios_platform_count.to_string());
    data.insert("FILES_COUNT".to_string(), total_files_all.to_string());

    let total_size = if total_bytes_all == 0 {
        "Unknown".to_string()
    } else {
        let iec = Byte::from_u128(total_bytes_all as u128).unwrap().get_appropriate_unit(UnitType::Binary).to_string();
        let si = Byte::from_u128(total_bytes_all as u128).unwrap().get_appropriate_unit(UnitType::Decimal).to_string();
        format!("{} ({})", iec, si)
    };
    data.insert("TOTAL_SIZE".to_string(), total_size);

    data.insert("DIRECTORY_STRUCTURE".to_string(), directory_structure);
    data.insert("ROM_FILES".to_string(), rom_files);
    data.insert("BIOS_FILES".to_string(), bios_files);
    data.insert("COLLECTION_TOML_REMOTE".to_string(), collection_toml_remote);
    data.insert("COLLECTION_TOML_LOCAL".to_string(), collection_toml_local);

    data
}

fn render_template(template_data: HashMap<String, String>) -> Result<String> {
    let template_path = Path::new("templates/readme.template.md");
    let mut template = fs::read_to_string(template_path)?;

    for (key, value) in template_data {
        template = template.replace(&format!("{{{{{}}}}}", key), &value);
    }

    Ok(template)
}

pub fn generate_readme(collection_path: &str) -> Result<bool> {
    let collection_path = Path::new(collection_path);

    // Extract collection metadata
    let (title, description) = extract_collection_metadata(collection_path)?;

    // Parse collection TOML for platform processing
    let content = fs::read_to_string(collection_path)?;
    let parsed: toml::Value = toml::from_str(&content)?;

    // Process all platform data
    let (platform_data, total_files_all, total_bytes_all) = process_platform_data(collection_path, &parsed)?;

    // Build content sections
    let directory_structure = build_directory_structure(&platform_data);
    let rom_files = build_rom_files_section(&platform_data);
    let (bios_platform_count, bios_files) = build_bios_section(&platform_data);

    // Generate collection URLs
    let (collection_toml_local, collection_toml_remote) = generate_collection_urls(collection_path.to_str().unwrap());

    // Prepare template data
    let template_data = prepare_template_data(
        title,
        description,
        &platform_data,
        total_files_all,
        total_bytes_all,
        bios_platform_count,
        directory_structure,
        rom_files,
        bios_files,
        collection_toml_local,
        collection_toml_remote,
    );

    // Render template
    let readme_content = render_template(template_data)?;

    // Write README
    let readme_path = collection_path.parent().unwrap().join("README.md");
    fs::write(readme_path, readme_content)?;
    Ok(true)
}
