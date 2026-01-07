use anyhow::Result;
use std::path::{Path};
use std::fs;
use std::collections::BTreeMap;
use percent_encoding::percent_decode_str;
use regex::Regex;

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

fn parse_file_size(size_str: &str) -> u64 {
    if size_str.is_empty() || size_str == "-" { return 0; }
    let mut s = size_str.replace(' ', "");
    let mut multiplier: f64 = 1.0;
    let s_up = s.to_uppercase();
    let units = [ ("KI",1024_f64.powi(1)), ("MI",1024_f64.powi(2)), ("GI",1024_f64.powi(3)), ("TI",1024_f64.powi(4)), ("K",1000_f64.powi(1)), ("M",1000_f64.powi(2)), ("G",1000_f64.powi(3)), ("T",1000_f64.powi(4)) ];
    for (u,m) in units.iter() {
        if s_up.ends_with(u) { multiplier = *m; s = s[..s.len()-u.len()].to_string(); break; }
    }
    if s.ends_with('B') { s.pop(); }
    let val = s.parse::<f64>().unwrap_or(0.0);
    (val * multiplier) as u64
}

fn format_file_size(bytes: u64, use_binary: bool) -> String {
    if bytes == 0 { return "0 B".to_string(); }
    let base = if use_binary {1024_f64} else {1000_f64};
    let units = if use_binary { vec!["B","KiB","MiB","GiB","TiB"] } else { vec!["B","KB","MB","GB","TB"] };
    let mut size = bytes as f64;
    let mut idx = 0usize;
    while size >= base && idx < units.len()-1 { size /= base; idx += 1; }
    if idx == 0 { format!("{} {}", size as u64, units[idx]) }
    else if size >= 100.0 { format!("{} {}", size as u64, units[idx]) }
    else if size >= 10.0 { if (size - (size as u64) as f64).abs() < 1e-9 { format!("{} {}", size as u64, units[idx]) } else { format!("{:.1} {}", size, units[idx]) } }
    else { format!("{:.1} {}", size, units[idx]) }
}

fn format_file_size_dual(bytes: u64) -> String {
    if bytes == 0 { return "Unknown".to_string(); }
    let iec = format_file_size(bytes, true);
    let si = format_file_size(bytes, false);
    format!("{} ({})", iec, si)
}

fn extract_sizes_from_html(html: &str, files: &[String]) -> BTreeMap<String,String> {
    let mut map = BTreeMap::new();
    for f in files.iter() {
        let decoded = percent_decode_str(f).decode_utf8_lossy();
        let pat = regex::escape(&decoded);
        let re_s = Regex::new(&format!(r"<a[^>]*>{}</a>\s*</td>\s*<td[^>]*class=\"size\"[^>]*>([^<]+)</td>", pat)).unwrap();
        if let Some(c) = re_s.captures(html) { let s = c.get(1).map(|m| m.as_str().trim().to_string()).unwrap_or_default(); if !s.is_empty() && s != "-" { map.insert(decoded.to_string(), s); } }
    }
    map
}

fn organize_files_by_game(decoded_files: &[String], file_sizes: &BTreeMap<String,String>) -> BTreeMap<String, Vec<serde_json::Value>> {
    let mut groups: BTreeMap<String, Vec<serde_json::Value>> = BTreeMap::new();
    let re_paren = Regex::new(r"\s*\(|\).*?").unwrap();
    for df in decoded_files.iter() {
        let name = df.clone();
        let name_no_ext = Regex::new(r"\.[^.]+$").unwrap().replace(&name, "").to_string();
        let game_name = if let Some(pos) = name_no_ext.find('(') { name_no_ext[..pos].trim().to_string() } else { name_no_ext.trim().to_string() };
        let tags_re = Regex::new(r"\([^)]*\)").unwrap();
        let tags = tags_re.find_iter(&name_no_ext).map(|m| m.as_str()).collect::<Vec<_>>().join(" ");
        let size = file_sizes.get(df).cloned().unwrap_or_else(|| "Unknown".to_string());
        let size_bytes = if size == "Unknown" { 0 } else { parse_file_size(&size) };
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

pub fn generate_readme(collection_path: &str) -> Result<bool> {
    let p = Path::new(collection_path);
    let content = fs::read_to_string(collection_path)?;
    let parsed: toml::Value = toml::from_str(&content)?;
    let mut roms = BTreeMap::new();
    if let Some(t) = parsed.get("roms").and_then(|v| v.as_table()) { for (k,v) in t { roms.insert(k.clone(), v.clone()); } }
    let mut total_files_all = 0usize;
    let mut platform_data: BTreeMap<String, serde_json::Value> = BTreeMap::new();
    for (platform, cfg) in roms.iter() {
        let url_file = crate::toml_utils::get_url_file_path(collection_path, platform);
        if !url_file.exists() { continue; }
        let (included, excluded) = parse_url_file_content(&url_file)?;
        total_files_all += included.len();
        let source_url = cfg.get("url").and_then(|v| v.as_str()).unwrap_or("");
        let mut file_sizes = BTreeMap::new();
        if !included.is_empty() && !source_url.is_empty() {
            if let Ok(resp) = reqwest::blocking::get(source_url) { if let Ok(html) = resp.text() { file_sizes = extract_sizes_from_html(&html, &included); } }
        }
        let decoded: Vec<String> = included.iter().map(|f| percent_decode_str(f).decode_utf8_lossy().to_string()).collect();
        let groups = organize_files_by_game(&decoded, &file_sizes);
        let total_bytes = file_sizes.values().map(|s| parse_file_size(s)).sum();
        let data = build_platform_data_structure(platform, &included, &excluded, &groups, total_bytes, source_url);
        platform_data.insert(platform.clone(), data);
    }
    let mut out = String::new();
    out.push_str(&format!("# {} ROM Collection\n\n", p.file_name().unwrap().to_string_lossy()));
    out.push_str("This collection contains ROMs for multiple gaming platforms.\n\n");
    out.push_str("## Metadata\n\n");
    out.push_str(&format!("- **Generated**: {}\n", chrono::Utc::now().format("%Y-%m-%d %H:%M:%S UTC")));
    out.push_str(&format!("- **ROM Platforms**: {}\n", platform_data.len()));
    out.push_str(&format!("- **Total Files**: {}\n\n", total_files_all));
    out.push_str("## Directory Structure\n\n");
    out.push_str("```");
    out.push_str("\n└── roms/\n");
    for (pname, pdata) in platform_data.iter() {
        let total_files = pdata.get("total_files").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
        let total_bytes = pdata.get("total_bytes").and_then(|v| v.as_u64()).unwrap_or(0);
        out.push_str(&format!("    ├── {}/ ({} files, {})\n", pname, total_files, format_file_size_dual(total_bytes)));
    }
    out.push_str("```\n\n");
    out.push_str("## ROM Files\n\n");
    for (pname, pdata) in platform_data.iter() {
        let game_groups = pdata.get("game_groups").cloned().unwrap_or(serde_json::json!({}));
        if game_groups.as_object().map(|o| o.is_empty()).unwrap_or(true) { continue; }
        out.push_str(&format!("<details>\n<summary>{}</summary>\n\n", pname));
        if let Some(obj) = game_groups.as_object() {
            for (_gname, files) in obj.iter() {
                if let Some(arr) = files.as_array() {
                    for fi in arr.iter() {
                        let filename = fi.get("decoded_filename").and_then(|v| v.as_str()).unwrap_or("");
                        let size = fi.get("size").and_then(|v| v.as_str()).unwrap_or("Unknown");
                        out.push_str(&format!("  - {} ({})\n", filename, size));
                    }
                }
            }
        }
        out.push_str("</details>\n\n");
    }
    let readme_path = Path::new(collection_path).parent().unwrap().join("README.md");
    fs::write(readme_path, out)?;
    Ok(true)
}
