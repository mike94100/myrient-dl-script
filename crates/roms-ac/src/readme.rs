use anyhow::Result;
use std::path::{Path};
use std::fs;
use std::collections::{BTreeMap, HashMap};
use percent_encoding::percent_decode_str;
use regex::Regex;
use byte_unit::{Byte, UnitType};

fn parse_url_file_content(url_file: &Path) -> Result<(Vec<String>, Vec<String>, Vec<String>)> {
    let mut included = Vec::new();
    let mut excluded = Vec::new();
    let mut full_urls = Vec::new();
    let s = fs::read_to_string(url_file)?;
    for line in s.lines().map(|l| l.trim()).filter(|l| !l.is_empty()) {
        if line.starts_with('#') {
            if line.starts_with("#http") {
                if let Some(seg) = line[1..].rsplit('/').next() { excluded.push(seg.to_string()); }
            }
        } else {
            if line.starts_with("http") {
                full_urls.push(line.to_string());
                if let Some(seg) = line.rsplit('/').next() { included.push(seg.to_string()); }
            }
        }
    }
    Ok((included, excluded, full_urls))
}

fn extract_sizes_from_html(html: &str, urls: &[String]) -> BTreeMap<String, String> {
    let document = scraper::Html::parse_document(html);
    let row_selector = scraper::Selector::parse("tr").unwrap();
    let link_selector = scraper::Selector::parse("td.link a").unwrap();
    let size_selector = scraper::Selector::parse("td.size").unwrap();

    let mut sizes = BTreeMap::new();

    for row in document.select(&row_selector) {
        if let Some(link_elem) = row.select(&link_selector).next() {
            if let Some(href) = link_elem.value().attr("href") {
                // href contains URL-encoded filename
                if let Some(size_elem) = row.select(&size_selector).next() {
                    let size_text = size_elem.text().collect::<String>().trim().to_string();
                    if !size_text.is_empty() && size_text != "-" {
                        // Match href against our URLs list, splitting last / to get filename only
                        for url in urls {
                            if let Some(url_filename) = url.split('/').last() {
                                if href == url_filename {
                                    // Decode the filename for storage key
                                    let decoded_filename = percent_decode_str(url_filename).decode_utf8_lossy().to_string();
                                    sizes.insert(decoded_filename, size_text.clone());
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    sizes
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

fn build_platform_data_structure(platform_name: &str, included_files: &[String], excluded_files: &[String], game_groups: &BTreeMap<String, Vec<serde_json::Value>>, total_bytes: u64, source_url: &str, directory: &str) -> serde_json::Value {
    serde_json::json!({
        "platform_name": platform_name,
        "directory": directory,
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

fn process_file_section(collection_path: &Path, parsed: &toml::Value, section: &str, progress_callback: Option<&dyn Fn(&str)>) -> Result<BTreeMap<String, serde_json::Value>> {
    let mut platforms = BTreeMap::new();
    if let Some(t) = parsed.get(section).and_then(|v| v.as_table()) {
        for (k,v) in t { platforms.insert(k.clone(), v.clone()); }
    }

    let mut platform_data: BTreeMap<String, serde_json::Value> = BTreeMap::new();

    for (platform, cfg) in platforms.iter() {
        let url_file = crate::toml_utils::get_url_file_path(collection_path.to_str().unwrap(), platform);
        if !url_file.exists() { continue; }
        let (included, excluded, full_urls) = parse_url_file_content(&url_file)?;
        let source_url = cfg.get("url").and_then(|v| v.as_str()).unwrap_or("");
        let directory = cfg.get("directory").and_then(|v| v.as_str()).unwrap_or(platform);
        let mut file_sizes = BTreeMap::new();
        if !included.is_empty() && !source_url.is_empty() {
            // Report progress: starting HTTP request for platform
            if let Some(cb) = progress_callback {
                cb(&format!("Fetching sizes for {} platform...", platform));
            }

            if let Ok(resp) = reqwest::blocking::get(source_url) {
                if let Ok(html) = resp.text() { file_sizes = extract_sizes_from_html(&html, &full_urls); }
            }

            // Report progress: completed HTTP request for platform
            if let Some(cb) = progress_callback {
                cb(&format!("✓ Fetched sizes for {} platform", platform));
            }
        }
        let decoded: Vec<String> = included.iter().map(|f| percent_decode_str(f).decode_utf8_lossy().to_string()).collect();
        let groups = organize_files_by_game(&decoded, &file_sizes);
        let total_bytes = file_sizes.values().map(|s| if s.trim().is_empty() || s.trim() == "-" { 0 } else { Byte::parse_str(s, true).map(|b| b.as_u128() as u64).unwrap_or(0) }).sum::<u64>();
        let data = build_platform_data_structure(platform, &included, &excluded, &groups, total_bytes, source_url, directory);
        platform_data.insert(platform.clone(), data);
    }

    Ok(platform_data)
}

fn count_platforms(parsed: &toml::Value, section: &str) -> usize {
    parsed.get(section)
        .and_then(|v| v.as_table())
        .map(|t| t.len())
        .unwrap_or(0)
}

fn process_platform_data(collection_path: &Path, parsed: &toml::Value, progress_callback: Option<&dyn Fn(&str)>) -> Result<(BTreeMap<String, serde_json::Value>, BTreeMap<String, serde_json::Value>, usize, usize, usize, u64)> {
    let rom_platform_data = process_file_section(collection_path, parsed, "roms", progress_callback)?;
    let bios_platform_data = process_file_section(collection_path, parsed, "bios", progress_callback)?;

    let rom_platform_count = count_platforms(parsed, "roms");
    let bios_platform_count = count_platforms(parsed, "bios");

    let total_files_all = rom_platform_data.values().map(|p| p.get("total_files").and_then(|v| v.as_u64()).unwrap_or(0) as usize).sum::<usize>()
                        + bios_platform_data.values().map(|p| p.get("total_files").and_then(|v| v.as_u64()).unwrap_or(0) as usize).sum::<usize>();
    let total_bytes_all = rom_platform_data.values().map(|p| p.get("total_bytes").and_then(|v| v.as_u64()).unwrap_or(0)).sum::<u64>()
                        + bios_platform_data.values().map(|p| p.get("total_bytes").and_then(|v| v.as_u64()).unwrap_or(0)).sum::<u64>();

    Ok((rom_platform_data, bios_platform_data, rom_platform_count, bios_platform_count, total_files_all, total_bytes_all))
}

fn build_directory_structure(rom_platform_data: &BTreeMap<String, serde_json::Value>, bios_platform_data: &BTreeMap<String, serde_json::Value>) -> String {
    let mut paths: BTreeMap<String, (u64, u64)> = BTreeMap::new();

    // Collect all platform directories
    for (_, pdata) in rom_platform_data.iter() {
        let directory = pdata.get("directory").and_then(|d| d.as_str()).unwrap_or("roms");
        let files = pdata.get("total_files").and_then(|v| v.as_u64()).unwrap_or(0);
        let bytes = pdata.get("total_bytes").and_then(|v| v.as_u64()).unwrap_or(0);
        paths.insert(directory.to_string(), (files, bytes));
    }

    for (_, pdata) in bios_platform_data.iter() {
        let directory = pdata.get("directory").and_then(|d| d.as_str()).unwrap_or("bios");
        let files = pdata.get("total_files").and_then(|v| v.as_u64()).unwrap_or(0);
        let bytes = pdata.get("total_bytes").and_then(|v| v.as_u64()).unwrap_or(0);
        paths.insert(directory.to_string(), (files, bytes));
    }

    build_tree_from_paths(&paths)
}

fn build_tree_from_paths(paths: &BTreeMap<String, (u64, u64)>) -> String {
    let mut output = String::from("```\n");

    // Group by root directory
    let mut roots: BTreeMap<String, Vec<(String, u64, u64)>> = BTreeMap::new();

    for (path, (files, bytes)) in paths {
        let parts: Vec<&str> = path.split('/').collect();
        let root = parts[0].to_string();
        roots.entry(root).or_default().push((path.clone(), *files, *bytes));
    }

    // Build tree for each root
    for (i, (root, platforms)) in roots.iter().enumerate() {
        if i > 0 { output.push('\n'); }
        output.push_str(&format!("└── {}/\n", root));
        output.push_str(&build_subtree(&platforms, 1));
    }

    output.push_str("```");
    output
}

fn build_subtree(platforms: &[(String, u64, u64)], depth: usize) -> String {
    let mut output = String::new();
    let indent = "    ".repeat(depth);

    for (path, files, bytes) in platforms {
        let parts: Vec<&str> = path.split('/').collect();
        if parts.len() > depth {
            // This platform has deeper nesting
            let current_part = parts[depth];
            let remaining_parts: Vec<&str> = parts[depth..].to_vec();

            // Check if this is a nested directory
            if remaining_parts.len() > 1 {
                output.push_str(&format!("{}├── {}/\n", indent, current_part));
                // Recursively build subtree for this branch
                let subtree_platforms: Vec<(String, u64, u64)> = platforms.iter()
                    .filter(|(p, _, _)| p.starts_with(&parts[..depth+1].join("/")))
                    .cloned()
                    .collect();
                if !subtree_platforms.is_empty() {
                    output.push_str(&build_subtree(&subtree_platforms, depth + 1));
                }
            } else {
                // This is a platform directory
                let size_str = format_size(*bytes);
                output.push_str(&format!("{}├── {}/ ({} files, {})\n", indent, current_part, files, size_str));
            }
        } else {
            // This is a platform at current depth
            let path_str = path.as_str();
            let platform_name = parts.last().unwrap_or(&path_str);
            let size_str = format_size(*bytes);
            output.push_str(&format!("{}├── {}/ ({} files, {})\n", indent, platform_name, files, size_str));
        }
    }

    output
}

fn format_size(bytes: u64) -> String {
    if bytes == 0 {
        "Unknown".to_string()
    } else {
        let iec_unit = Byte::from_u128(bytes as u128).unwrap().get_appropriate_unit(UnitType::Binary);
        let si_unit = Byte::from_u128(bytes as u128).unwrap().get_appropriate_unit(UnitType::Decimal);
        format!("{:.1} ({:.1})", iec_unit, si_unit)
    }
}

fn build_files_section(platform_data: &BTreeMap<String, serde_json::Value>, empty_message: &str) -> String {
    let mut files_content = String::new();

    for (pname, pdata) in platform_data.iter() {
        let game_groups = pdata.get("game_groups").cloned().unwrap_or(serde_json::json!({}));
        if game_groups.as_object().map(|o| o.is_empty()).unwrap_or(true) { continue; }
        files_content.push_str(&format!("<details>\n<summary>{}</summary>\n\n", pname));
        if let Some(obj) = game_groups.as_object() {
            for (_gname, files) in obj.iter() {
                if let Some(arr) = files.as_array() {
                    for fi in arr.iter() {
                        let filename = fi.get("decoded_filename").and_then(|v| v.as_str()).unwrap_or("");
                        let size_str = if let Some(size) = fi.get("size").and_then(|v| v.as_str()) {
                            if size == "Unknown" {
                                "Unknown".to_string()
                            } else {
                                // Apply truncation formatting to individual file sizes
                                if let Ok(bytes) = Byte::parse_str(size, true) {
                                    format!("{:.1}", bytes.get_appropriate_unit(UnitType::Binary))
                                } else {
                                    size.to_string()
                                }
                            }
                        } else {
                            "Unknown".to_string()
                        };
                        files_content.push_str(&format!("  - {} ({})\n", filename, size_str));
                    }
                }
            }
        }
        files_content.push_str("</details>\n\n");
    }

    // If no files found, provide a message
    if files_content.trim().is_empty() {
        format!("{}\n", empty_message)
    } else {
        files_content
    }
}



fn generate_collection_urls(collection_path: &str) -> Result<(String, String)> {
    let collection_toml_local = collection_path;
    let repo_base_url = crate::toml_utils::get_repo_base_url()?;
    let collection_toml_remote = format!("{}/{}", repo_base_url, collection_toml_local);
    Ok((collection_toml_local.to_string(), collection_toml_remote))
}

fn prepare_template_data(
    title: String,
    description: String,
    rom_platform_count: usize,
    bios_platform_count: usize,
    total_files_all: usize,
    total_bytes_all: u64,
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
    data.insert("ROM_PLATFORM_COUNT".to_string(), rom_platform_count.to_string());
    data.insert("BIOS_PLATFORM_COUNT".to_string(), bios_platform_count.to_string());
    data.insert("FILES_COUNT".to_string(), total_files_all.to_string());

    let total_size = format_size(total_bytes_all);
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

pub fn generate_readme(collection_path: &str, progress_callback: Option<&dyn Fn(&str)>) -> Result<bool> {
    let collection_path = Path::new(collection_path);

    // Extract collection metadata
    let (title, description) = extract_collection_metadata(collection_path)?;

    // Parse collection TOML for platform processing
    let content = fs::read_to_string(collection_path)?;
    let parsed: toml::Value = toml::from_str(&content)?;

    // Process all platform data
    let (rom_platform_data, bios_platform_data, rom_platform_count, bios_platform_count, total_files_all, total_bytes_all) = process_platform_data(collection_path, &parsed, progress_callback)?;

    // Build content sections
    let directory_structure = build_directory_structure(&rom_platform_data, &bios_platform_data);
    let rom_files = build_files_section(&rom_platform_data, "No ROM files configured in this collection.");
    let bios_files = build_files_section(&bios_platform_data, "No BIOS files configured in this collection.");

    // Generate collection URLs
    let (collection_toml_local, collection_toml_remote) = generate_collection_urls(collection_path.to_str().unwrap())?;

    // Prepare template data
    let template_data = prepare_template_data(
        title,
        description,
        rom_platform_count,
        bios_platform_count,
        total_files_all,
        total_bytes_all,
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
